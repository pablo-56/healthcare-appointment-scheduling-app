import os
import json
import httpx
from typing import Dict, Any
from sqlalchemy.orm import Session
from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import EligibilityResponse, Task

logger = get_task_logger(__name__)

BILLING_ADAPTER_URL = os.getenv("BILLING_ADAPTER_URL", "http://billing-adapter:9200")

def _db() -> Session:
    return SessionLocal()

def _create_followup_task(db: Session, appointment_id: int, payload: Dict[str, Any]):
    t = Task(type="eligibility_followup", status="OPEN", payload_json=payload)
    setattr(t, "appointment_id", appointment_id) if hasattr(t, "appointment_id") else None
    db.add(t)

@celery_app.task(
    name="eligibility.check_270",
    bind=True,
    autoretry_for=(httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def check_270(self, appointment_id: int, patient_email: str, reason: str, insurance_number: str | None):
    """
    Build a tiny 270 payload, call the mock adapter, persist 271-like result,
    and raise a follow-up task on mismatch.
    """
    payload = {
        "appointment_id": appointment_id,
        "patient_email": patient_email,
        "reason": reason,
        "insurance_number": insurance_number,
        "plan_hint": None,
    }

    logger.info("eligibility.check_270 payload=%s", payload)

    with httpx.Client(base_url=BILLING_ADAPTER_URL, timeout=10) as client:
        r = client.post("/eligibility", json=payload)
        r.raise_for_status()
        data = r.json()

    db = _db()
    try:
        er = EligibilityResponse(
            appointment_id=appointment_id,
            eligible=bool(data.get("eligible")),
            plan=str(data.get("plan") or "PPO-BASIC"),
            copay_cents=int(data.get("copay_cents") or 0),
            raw_json=data.get("raw_json") or {},
        )
        db.add(er)

        # Mismatch rule: no insurance OR not eligible -> follow-up
        if not insurance_number or not er.eligible:
            _create_followup_task(
                db,
                appointment_id,
                {
                    "appointment_id": appointment_id,
                    "reason": reason,
                    "patient_email": patient_email,
                    "issue": "missing_insurance" if not insurance_number else "ineligible",
                    "adapter_result": data,
                },
            )

        db.commit()
        logger.info("eligibility saved for appt=%s plan=%s copay=%s", appointment_id, er.plan, er.copay_cents)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
