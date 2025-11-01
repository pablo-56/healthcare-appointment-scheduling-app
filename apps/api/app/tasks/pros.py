# apps/api/app/tasks/pros.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from sqlalchemy import text, bindparam
import sqlalchemy as sa

from ..celery_app import celery_app
from ..db import SessionLocal

@celery_app.task(name="pros.reminder_scheduler", acks_late=True)
def reminder_scheduler(days_back: int = 2):
    """
    Dev-friendly: find recent appointments and create a PHQ-9 reminder task
    if patient has no PHQ-9 in the last 7 days and no open reminder yet.
    """
    db = SessionLocal()
    created = 0
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days_back)
        appts = db.execute(
            text("""
                SELECT a.id, a.patient_id
                  FROM appointments a
                 WHERE a.start_at >= :since
            """),
            {"since": since},
        ).mappings().all()

        for a in appts:
            pid = a["patient_id"]
            if not pid:
                continue

            recent = db.execute(
                text("""
                    SELECT 1 FROM patient_surveys
                     WHERE patient_id=:pid AND instrument='phq9'
                       AND created_at >= NOW() - interval '7 days'
                     LIMIT 1
                """),
                {"pid": pid},
            ).first()
            if recent:
                continue

            open_reminder = db.execute(
                text("""
                    SELECT 1 FROM tasks
                     WHERE type='pro_reminder' AND status='open'
                       AND (payload_json->>'patient_id')::int = :pid
                     LIMIT 1
                """),
                {"pid": pid},
            ).first()
            if open_reminder:
                continue

            db.execute(
                text("""
                    INSERT INTO tasks(type, status, payload_json, created_at)
                    VALUES('pro_reminder', 'open', :payload::json, NOW())
                """).bindparams(bindparam("payload", type_=sa.JSON())),
                {"payload": {"patient_id": pid, "instrument": "phq9", "message": "Please complete PHQ-9 in your portal."}},
            )
            created += 1

        db.commit()
        return {"created": created}
    finally:
        db.close()

@celery_app.task(name="pros.escalation_dispatcher", acks_late=True)
def escalation_dispatcher():
    """
    For any survey with high score lacking corresponding escalation task, create one.
    """
    db = SessionLocal()
    made = 0
    try:
        rows = db.execute(
            text("""
                SELECT s.id, s.patient_id, s.instrument, s.score
                  FROM patient_surveys s
                 WHERE s.created_at >= NOW() - interval '2 days'
            """)
        ).mappings().all()

        for r in rows:
            if r["instrument"] == "phq9" and int(r["score"]) < 10:
                continue

            exists = db.execute(
                text("""
                    SELECT 1 FROM tasks
                     WHERE type='care_escalation'
                       AND (payload_json->>'survey_id')::int = :sid
                     LIMIT 1
                """),
                {"sid": r["id"]},
            ).first()
            if exists:
                continue

            db.execute(
                text("""
                    INSERT INTO tasks(type, status, payload_json, created_at)
                    VALUES('care_escalation','open', :payload::json, NOW())
                """).bindparams(bindparam("payload", type_=sa.JSON())),
                {"payload": {"survey_id": r["id"], "patient_id": r["patient_id"], "instrument": r["instrument"], "score": r["score"]}},
            )
            made += 1

        db.commit()
        return {"created": made}
    finally:
        db.close()
