# apps/api/app/routers/billing_eligibility.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Path
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import sqlalchemy as sa
import httpx, os
from datetime import datetime

from ..db import get_db

router = APIRouter(prefix="/v1/billing", tags=["billing"])

ADAPTER_BASE = os.getenv("BILLING_ADAPTER_BASE", "http://billing-adapter:9200")

def _require_ops_or_payment(pou: Optional[str]):
    if not pou or pou.upper() not in {"OPERATIONS", "PAYMENT"}:
        raise HTTPException(status_code=403, detail="Missing/invalid X-Purpose-Of-Use")

def _fetch_patient_email(db: Session, pid: int) -> Optional[str]:
    # Keep this conservative: only ask for fields we know exist widely.
    row = db.execute(text("SELECT email FROM patients WHERE id=:id"), {"id": pid}).first()
    return row[0] if row and row[0] else None

def _latest_appt_for_patient(db: Session, pid: int) -> Optional[Dict[str, Any]]:
    r = db.execute(
        text("""
          SELECT id, reason
          FROM appointments
          WHERE patient_id = :pid
          ORDER BY COALESCE(start_at, NOW()) DESC
          LIMIT 1
        """),
        {"pid": pid},
    ).mappings().first()
    return dict(r) if r else None

def _insurance_from_intake(db: Session, appt_id: Optional[int]) -> Optional[str]:
    if not appt_id:
        return None
    r = db.execute(
        text("""
          SELECT answers_json->>'insurance_number' AS ins
          FROM intake_forms
          WHERE appointment_id = :aid
          ORDER BY id DESC
          LIMIT 1
        """),
        {"aid": appt_id},
    ).first()
    return (r[0] if r else None) or None

@router.get("/eligibility/{patient_id}")
def run_eligibility(
    patient_id: int = Path(...),
    appointment_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    x_purpose_of_use: Optional[str] = Header(None, alias="X-Purpose-Of-Use"),
):
    """
    Run payer eligibility for a patient (optionally for a specific appointment).

    - Resolves context (appointment reason, patient email)
    - Pulls insurance_number from latest intake for that appointment if available
    - Calls billing-adapter /eligibility
    - Persists a row in eligibility_responses (if table exists)
    - Returns a compact 'result' with mismatch flag (eligible==False OR plan mismatch)
    """
    _require_ops_or_payment(x_purpose_of_use)

    # Resolve appointment if not provided (latest is OK for front-desk)
    appt = None
    if appointment_id:
        appt = db.execute(
            text("SELECT id, reason FROM appointments WHERE id=:id"),
            {"id": appointment_id},
        ).mappings().first()
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found")
    else:
        appt = _latest_appt_for_patient(db, patient_id)

    appt_id = int(appt["id"]) if appt else 0
    reason = (appt["reason"] if appt else "") or ""

    # Gather minimal identity for adapter (safe to omit if unknown)
    email = _fetch_patient_email(db, patient_id)
    insurance_number = _insurance_from_intake(db, appt_id)

    # (Optional) recorded plan if you keep it somewhere; using latest prior response here
    rec = db.execute(
        text("""
          SELECT plan
          FROM eligibility_responses
          WHERE appointment_id = :aid
          ORDER BY id DESC
          LIMIT 1
        """),
        {"aid": appt_id},
    ).first()
    recorded_plan = rec[0] if rec else None

    # Call billing-adapter; fall back to simulated answer if unavailable
    payload = {
        "appointment_id": appt_id,
        "patient_email": email,
        "insurance_number": insurance_number,
        "reason": reason,
    }
    eligible, plan, copay, raw = False, "UNKNOWN", 0, {}
    try:
        with httpx.Client(timeout=8) as client:
            r = client.post(f"{ADAPTER_BASE}/eligibility", json=payload)
            data = r.json()
            eligible = bool(data.get("eligible"))
            plan = data.get("plan") or plan
            copay = int(data.get("copay_cents") or 0)
            raw = data.get("raw_json") or data
    except Exception as _e:
        # Keep a negative but informative outcome
        raw = {"simulated": True, "error": str(_e)}

    # Persist outcome (idempotent enough for repeated checks)
    db.execute(
        text("""
          CREATE TABLE IF NOT EXISTS eligibility_responses (
            id SERIAL PRIMARY KEY,
            appointment_id INT NOT NULL,
            eligible BOOLEAN NOT NULL,
            plan TEXT NULL,
            copay_cents INT NULL,
            raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
          )
        """)
    )
    db.execute(
        text("""
          INSERT INTO eligibility_responses (appointment_id, eligible, plan, copay_cents, raw_json)
          VALUES (:aid, :ok, :plan, :copay, :raw)
        """).bindparams(bindparam("raw", type_=sa.JSON())),
        {"aid": appt_id, "ok": eligible, "plan": plan, "copay": copay, "raw": raw},
    )
    db.commit()

    # Mismatch rule: not eligible OR plan differs from last recorded plan
    mismatch = (not eligible) or (recorded_plan is not None and recorded_plan != plan)

    return {
        "result": {
            "patient_id": patient_id,
            "appointment_id": appt_id or None,
            "eligible": eligible,
            "plan": plan,
            "copay_cents": copay,
            "recorded_plan": recorded_plan,
            "mismatch": mismatch,
            "raw": raw,
            "adapter_base": ADAPTER_BASE,
        }
    }
