# apps/api/app/routers/signature.py
import hmac, hashlib, os
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy import text, bindparam
import sqlalchemy as sa
from ..db import SessionLocal
from ..storage import put_pdf_and_sha
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
import io, json

router = APIRouter()

WEBHOOK_SECRET = os.getenv("SIGNATURE_WEBHOOK_SECRET", "dev-secret")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

class SignatureRequest(BaseModel):
    appointment_id: int
    signer_name: str
    email: str

@router.post("/v1/signature/requests")
def create_signature_request(req: SignatureRequest, db=Depends(get_db)):
    # In real life call an e-sign provider; here we return a mock request id + URL.
    rid = f"sig-{req.appointment_id}"
    # Audit request creation
    db.execute(
        text("INSERT INTO audit_logs (actor, action, target, details, created_at) "
             "VALUES (:a, 'SIGNATURE_REQUESTED', :t, :d, NOW())")
        .bindparams(bindparam("d", type_=sa.JSON())),
        {"a": req.email, "t": rid, "d": {"appointment_id": req.appointment_id, "signer": req.signer_name}},
    )
    db.commit()
    return {"request_id": rid, "redirect_url": f"/consent/{rid}"}

def _make_consent_pdf(appointment_id: int, signer_name: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    w, h = LETTER
    y = h - 50
    c.setFont("Helvetica-Bold", 14); c.drawString(50, y, "Consent to Treat"); y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Appointment #{appointment_id}"); y -= 16
    c.drawString(50, y, f"Signed by: {signer_name}"); y -= 16
    c.drawString(50, y, "I consent to the proposed care plan."); y -= 16
    c.showPage(); c.save(); return buf.getvalue()

@router.post("/v1/signature/webhook")
async def signature_webhook(
    request: Request,
    x_signature: str = Header(None, alias="X-Signature"),
    db=Depends(get_db),
):
    raw = await request.body()
    expected = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not x_signature or not hmac.compare_digest(x_signature, expected):
        raise HTTPException(401, "invalid signature")

    payload = await request.json()
    rid = payload.get("request_id")
    appointment_id = int(payload.get("appointment_id"))
    signer_name = payload.get("signer_name", "Unknown")
    signer_ip = payload.get("signer_ip", "127.0.0.1")

    # Generate a PDF for the signed consent and upload
    pdf = _make_consent_pdf(appointment_id, signer_name)
    key = f"consent/{rid}.pdf"
    url, sha = put_pdf_and_sha(key, pdf)

    # Resolve patient_id (nullable is allowed)
    row = db.execute(text("SELECT patient_id FROM appointments WHERE id=:id"), {"id": appointment_id}).first()
    patient_id = row.patient_id if row else None

    # Insert into consents
    db.execute(
        text("INSERT INTO consents (patient_id, pdf_url, sha256, signer_name, signer_ip, signed_at, created_at) "
             "VALUES (:pid, :url, :sha, :name, :ip, NOW(), NOW())"),
        {"pid": patient_id, "url": url, "sha": sha, "name": signer_name, "ip": signer_ip},
    )

    # Insert a 'Consent' document (meta stores sha/title/request_id)
    meta = {"title": "Consent (SIGNED)", "sha256": sha, "request_id": rid, "appointment_id": appointment_id}
    db.execute(
        text("INSERT INTO documents (patient_id, kind, url, meta, created_at) "
             "VALUES (:pid, 'Consent', :url, :meta, NOW())")
        .bindparams(bindparam("meta", type_=sa.JSON())),
        {"pid": patient_id, "url": url, "meta": meta},
    )

    # Audit
    db.execute(
        text("INSERT INTO audit_logs (actor, action, target, details, created_at) "
             "VALUES (:a, 'CONSENT_SIGNED', :t, :d, NOW())")
        .bindparams(bindparam("d", type_=sa.JSON())),
        {"a": signer_name, "t": rid, "d": {"appointment_id": appointment_id, "pdf": url}},
    )

    db.commit()
    return {"ok": True}
