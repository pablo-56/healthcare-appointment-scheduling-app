# app/routers/appointments.py
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from ..db import get_db
from app.utils.audit import audit_safe
from app.celery_app import celery_app

log = logging.getLogger(__name__)

class AppointmentCreate(BaseModel):
    patient_email: EmailStr
    reason: str
    start: str
    end: str
    slot_id: str
    source_channel: str | None = "web"
    insurance_number: str | None = None  # Phase 3 input

router = APIRouter(prefix="/v1/appointments", tags=["appointments"])

@router.post("")
def create_appointment(
    body: AppointmentCreate,
    db: Session = Depends(get_db),
    x_purpose_of_use: str | None = Header(default=None, convert_underscores=False),
):
    # Create a mock EHR ID tied to the selected slot
    fhir_id = f"ehr-appt-{body.slot_id}"

    # Persist appointment
    row = db.execute(
        text(
            """
            INSERT INTO appointments (
                patient_id, start_at, end_at, reason, status, fhir_appointment_id, source_channel, created_at
            ) VALUES (
                NULL, :start_at, :end_at, :reason, 'BOOKED', :fhir_id, :src, NOW()
            ) RETURNING id
            """
        ),
        {
            "start_at": body.start,
            "end_at": body.end,
            "reason": body.reason,
            "fhir_id": fhir_id,
            "src": body.source_channel or "web",
        },
    ).first()
    appt_id = int(row[0])
    db.commit()

    # Audit (JSON-safe)
    audit_safe(
        db=db,
        actor=body.patient_email,  # no user object here; use patient email
        action="APPOINTMENT_BOOKED",
        target=fhir_id,
        details={
            "slot_id": body.slot_id,
            "source_channel": body.source_channel or "web",
            "purpose_of_use": x_purpose_of_use,
        },
    )

    # Fire-and-forget eligibility task
    try:
        celery_app.send_task(
            "eligibility.check_270",
            kwargs={
                "appointment_id": appt_id,
                "patient_email": body.patient_email,
                "reason": body.reason,
                "insurance_number": body.insurance_number,
            },
        )
    except Exception:
        # non-fatal for booking
        log.exception("failed to enqueue eligibility")

    return {"id": appt_id, "fhir_appointment_id": fhir_id, "status": "BOOKED"}
