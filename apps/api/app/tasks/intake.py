# apps/api/app/tasks/intake.py
 # <- import the Celery app object defined in tasks/__init__.py
from sqlalchemy import text, bindparam
import sqlalchemy as sa
from ..db import SessionLocal
from ..storage import put_pdf_and_sha
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
import io, json, httpx
from ..settings import settings
from app.celery_app import celery_app

def _pdf_from_answers(answers: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Patient Intake")
    y -= 30
    c.setFont("Helvetica", 10)
    for k, v in answers.items():
        c.drawString(50, y, f"{k}: {json.dumps(v)[:100]}")
        y -= 14
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)
    c.showPage()
    c.save()
    return buf.getvalue()
@celery_app.task(name="intake.render_intake_pdf")
def render_intake_pdf(appointment_id: int, answers: dict):
    """
    - render a PDF from answers
    - upload to S3/MinIO
    - insert into documents(patient_id, kind, url, meta, created_at)
    - mirror to EHR mock as FHIR DocumentReference
    """
    db = SessionLocal()
    try:
        pdf = _pdf_from_answers(answers)
        key = f"intake/appointment-{appointment_id}.pdf"
        url, sha = put_pdf_and_sha(key, pdf)

        # resolve patient_id (nullable)
        row = db.execute(
            text("SELECT patient_id FROM appointments WHERE id=:id"),
            {"id": appointment_id},
        ).first()
        patient_id = row.patient_id if row else None

        meta = {
            "title": f"Intake {appointment_id}",
            "sha256": sha,
            "appointment_id": appointment_id,
            "answers_preview": {k: (str(v)[:80]) for k, v in list(answers.items())[:12]},
        }

        db.execute(
            text("INSERT INTO documents (patient_id, kind, url, meta, created_at) "
                 "VALUES (:pid, 'Intake', :url, :meta, NOW())")
            .bindparams(bindparam("meta", type_=sa.JSON())),
            {"pid": patient_id, "url": url, "meta": meta},
        )
        db.commit()

        # Mirror to EHR mock
        dr = {
            "resourceType": "DocumentReference",
            "status": "current",
            "type": {"text": "Intake"},
            "content": [
                {
                    "attachment": {
                        "url": url,
                        "title": meta["title"],
                        "contentType": "application/pdf",
                    }
                }
            ],
        }
        try:
            with httpx.Client(timeout=5) as client:
                client.post(f"{settings.ehr_base}/fhir/DocumentReference", json=dr)
        except Exception:
            pass

    finally:
        db.close()
