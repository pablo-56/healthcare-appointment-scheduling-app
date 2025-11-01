# apps/api/app/tasks/documents.py
# Phase 7 optional task: background discharge render (same logic as the API).

from __future__ import annotations
from sqlalchemy import text
import base64, datetime as dt, secrets
from app.celery_app import celery_app
from app.db import SessionLocal

@celery_app.task(name="documents.render", acks_late=True)
def render_discharge_task(appointment_id: int, encounter_id: str | None = None, language: str = "en") -> dict:
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT id, reason, start_at, fhir_appointment_id FROM appointments WHERE id=:aid"),
            {"aid": appointment_id},
        ).mappings().first()
        if not row:
            return {"status": "skip", "reason": "appointment_not_found"}

        enc = encounter_id or f"enc-{row['id']}"
        token = secrets.token_urlsafe(16)

        html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Discharge</title></head>
        <body style="font-family:system-ui,Segoe UI,Arial,sans-serif">
          <h1>Discharge Summary</h1>
          <p>Encounter: {enc}</p>
          <ul>
            <li>Appointment #{row['id']}</li>
            <li>Start: {row['start_at']}</li>
            <li>Reason: {row.get('reason') or '-'}</li>
          </ul>
          <p>Use your follow-up link or call the clinic to book.</p>
        </body></html>"""

        data_url = "data:text/html;base64," + base64.b64encode(html.encode("utf-8")).decode("ascii")

        db.execute(
            text(
                """
                INSERT INTO documents(kind, url, meta)
                VALUES (
                  'Discharge',
                  :url,
                  (jsonb_build_object(
                    'appointment_id', :aid,
                    'encounter_id', :enc,
                    'token', :tok,
                    'expires_at', NOW() + interval '7 days',
                    'language', :lang,
                    'status', 'READY'
                  ))::json
                )
                """
            ),
            {"url": data_url, "aid": row["id"], "enc": enc, "tok": token, "lang": language},
        )
        db.commit()
        return {"status": "ok", "appointment_id": int(row["id"]), "encounter_id": enc}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
