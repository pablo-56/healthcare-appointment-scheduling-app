from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
import os
import httpx

from ..db import get_db
from ..utils.audit import audit_safe
from ..settings import settings

router = APIRouter(prefix="/v1", tags=["checkin"])

# Allow overriding in docker-compose/.env but provide a safe default
#EHR_BASE = os.getenv("EHR_CONNECTOR_BASE", "http://ehr-connector:9300")

EHR_BASE = settings.ehr_base

class Vitals(BaseModel):
    heart_rate: int | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    temperature_c: float | None = None
    respiration: int | None = None
    spo2: int | None = None

class CheckInBody(BaseModel):
    appointment_id: int
    patient_email: EmailStr | None = None
    kiosk_device_id: str | None = None
    vitals: Vitals | None = None

@router.post("/checkin")
def check_in(
    body: CheckInBody,
    db: Session = Depends(get_db),
    x_purpose_of_use: str | None = Header(default=None, convert_underscores=False),
):
    # Require PoU for write in prod (middleware already handles this; this is a friendly guard)
    if not x_purpose_of_use:
        # middleware is "soft" by default; we keep this gentle
        pass

    # Load appointment
    row = db.execute(
        text("""
            SELECT id, status, fhir_appointment_id, patient_id, start_at, end_at, reason
            FROM appointments
            WHERE id = :id
        """),
        {"id": body.appointment_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")

    # Flip status -> ARRIVED (idempotent)
    if row["status"] != "ARRIVED":
        db.execute(
            text("""
                UPDATE appointments
                SET status = 'ARRIVED'
                WHERE id = :id
            """),
            {"id": body.appointment_id},
        )
        db.commit()

    # Audit: patient/device checked in
    audit_safe(
        db=db,
        actor=body.patient_email or "kiosk",
        action="CHECKIN",
        target=str(row["fhir_appointment_id"] or row["id"]),
        details={
            "appointment_id": row["id"],
            "kiosk_device_id": body.kiosk_device_id,
            "status": "ARRIVED",
        },
    )

    # Optional vitals → EHR Observation mock
    observation_id = None
    if body.vitals:
        payload = {
            "appointment_id": row["id"],
            "vitals": {k: v for k, v in body.vitals.model_dump().items() if v is not None},
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(f"{EHR_BASE}/fhir/Observation", json=payload)
                r.raise_for_status()
                observation_id = r.json().get("id")
        except Exception as e:
            # Non-fatal; just audit the failure
            audit_safe(
                db=db,
                actor="system",
                action="EHR_OBSERVATION_POST_FAILED",
                target=str(row["fhir_appointment_id"] or row["id"]),
                details={"error": str(e)},
            )

    return {
        "appointment": {
            "id": row["id"],
            "fhir_appointment_id": row["fhir_appointment_id"],
            "status": "ARRIVED",
            "reason": row["reason"],
            "start_at": row["start_at"].isoformat() if row["start_at"] else None,
            "end_at": row["end_at"].isoformat() if row["end_at"] else None,
        },
        "observation_id": observation_id,
        "message": "Checked in",
    }
