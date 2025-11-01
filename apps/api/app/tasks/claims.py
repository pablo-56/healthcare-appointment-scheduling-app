# apps/api/app/tasks/claims.py
from __future__ import annotations

import json, logging, datetime as dt, httpx
from typing import Dict, Any, Optional

from sqlalchemy import text
from app.db import SessionLocal
from app.celery_app import celery_app
from app.settings import settings

log = logging.getLogger(__name__)

CREATE_CLAIMS_SQL = """
CREATE TABLE IF NOT EXISTS claims (
  id SERIAL PRIMARY KEY,
  encounter_id TEXT NOT NULL,
  appointment_id INT NULL,
  patient_id INT NULL,
  status TEXT NOT NULL DEFAULT 'NEW',
  payer_ref TEXT NULL,
  total_cents INT NULL,
  payload_json JSON NOT NULL DEFAULT '{}'::json,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

def _ensure(db):
    db.execute(text(CREATE_CLAIMS_SQL))
    db.commit()

# ---- tiny assembler used by workflows (encounter -> JSON "837") --------------
@celery_app.task(name="claims.assemble")
def assemble(encounter_id: str, appointment_id: Optional[int] = None, patient_id: Optional[int] = None) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        _ensure(db)

        if patient_id is None and appointment_id is not None:
            row = db.execute(
                text("SELECT patient_id FROM appointments WHERE id=:id"),
                {"id": appointment_id},
            ).first()
            if row and row[0] is not None:
                patient_id = int(row[0])

        payload = {
            "encounter_id": encounter_id,
            "svc": [{"cpt": "99213", "units": 1, "charge_cents": 12500}],
            "diag": ["J06.9"],
            "facility": "MAIN_CLINIC",
        }
        total_cents = sum(int(s.get("charge_cents", 0)) for s in payload.get("svc", []))

        db.execute(
            text(
                """
                INSERT INTO claims(encounter_id, appointment_id, patient_id, status, total_cents, payload_json)
                VALUES (:enc, :appt, :pid, 'NEW', :tot, :payload::json)
                ON CONFLICT DO NOTHING
                """
            ).bindparams(bindparam("payload", type_=sa.JSON())),
            {"enc": encounter_id, "appt": appointment_id, "pid": patient_id, "tot": total_cents, "payload": payload},
        )
        db.execute(
            text(
                """
                UPDATE claims
                   SET payload_json=:payload::json, total_cents=:tot, status='NEW', updated_at=NOW()
                 WHERE encounter_id=:enc
                """
            ).bindparams(bindparam("payload", type_=sa.JSON())),
            {"payload": payload, "tot": total_cents, "enc": encounter_id},
        )
        db.commit()

        row = db.execute(
            text("SELECT id, status FROM claims WHERE encounter_id=:enc ORDER BY id DESC LIMIT 1"),
            {"enc": encounter_id},
        ).mappings().first()
        return {"id": row["id"], "status": row["status"]}
    finally:
        db.close()

# ---- submit to billing-adapter ------------------------------------------------
@celery_app.task(name="claims.submit")
def submit(claim_id: int) -> Dict[str, Any]:
    """
    POSTs the stored JSON payload to the billing-adapter mock.
    Sets status=SUBMITTED or REJECTED and saves payer_ref if returned.
    """
    db = SessionLocal()
    try:
        _ensure(db)
        row = db.execute(text("SELECT id, payload_json FROM claims WHERE id=:id"), {"id": claim_id}).mappings().first()
        if not row:
            return {"error": "not_found", "id": claim_id}

        payload = row["payload_json"]
        adapter = getattr(settings, "billing_base", None) or "http://billing-adapter:9400"

        try:
            with httpx.Client(timeout=8) as c:
                r = c.post(f"{adapter}/claims", json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log.warning("Billing adapter failed, marking REJECTED id=%s err=%s", claim_id, e)
            db.execute(
                text("UPDATE claims SET status='REJECTED', updated_at=NOW() WHERE id=:id"),
                {"id": claim_id},
            )
            db.commit()
            return {"id": claim_id, "status": "REJECTED", "error": "adapter_unavailable"}

        payer_ref = data.get("clearinghouse_id") or data.get("id") or None
        status = "SUBMITTED" if (data.get("status") in {"ACCEPTED", "QUEUED", "OK"}) else "REJECTED"

        db.execute(
            text("UPDATE claims SET status=:st, payer_ref=:pr, updated_at=NOW() WHERE id=:id"),
            {"st": status, "pr": payer_ref, "id": claim_id},
        )
        db.commit()
        return {"id": claim_id, "status": status, "payer_ref": payer_ref}
    finally:
        db.close()

# ---- ingest a (mock) 835 remit ----------------------------------------------
@celery_app.task(name="remits.ingest_835")
def ingest_835(remit: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update claim based on remit.
    If paid_cents > 0 -> PAID else -> DENIED and create a 'claim_correction' task.
    """
    db = SessionLocal()
    try:
        _ensure(db)
        cid = int(remit["claim_id"])
        paid = int(remit.get("paid_cents") or 0)
        denial = remit.get("denial_code")

        if paid > 0:
            db.execute(
                text("UPDATE claims SET status='PAID', updated_at=NOW() WHERE id=:id"),
                {"id": cid},
            )
            db.commit()
            return {"id": cid, "status": "PAID", "paid_cents": paid}

        # DENIED path -> create work task so biller can fix/correct
        db.execute(
            text("UPDATE claims SET status='DENIED', updated_at=NOW() WHERE id=:id"),
            {"id": cid},
        )
        db.execute(
            text(
                """
                INSERT INTO tasks(type, status, payload_json, created_at)
                VALUES('claim_correction', 'OPEN',
                       jsonb_build_object('claim_id', :id, 'denial_code', :code)::json, NOW())
                """
            ),
            {"id": cid, "code": denial or "CO-97"},
        )
        db.commit()
        return {"id": cid, "status": "DENIED", "denial_code": denial or "CO-97"}
    finally:
        db.close()
