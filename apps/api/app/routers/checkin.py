# apps/api/app/routers/checkin.py
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone, timedelta
import os
import httpx

from ..db import get_db
from ..utils.audit import audit_safe

router = APIRouter(prefix="/v1", tags=["checkin"])

EHR_BASE = os.getenv("EHR_CONNECTOR_BASE", "http://ehr-connector:8100")

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
  # Soft PoU guard (prod can enforce TREATMENT)
  _ = x_purpose_of_use

  # 1) Load appointment
  row = db.execute(
    text("""
      SELECT id, status, fhir_appointment_id, patient_id, start_at, end_at, reason
      FROM appointments
      WHERE id = :id
    """),
    {"id": body.appointment_id},
  ).mappings().first()

  if not row:
    # Frontend will show reschedule button
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")

  # 2) Late check (grace 15 minutes after scheduled end)
  now = datetime.now(timezone.utc)
  if row["end_at"] and (now > (row["end_at"].replace(tzinfo=timezone.utc) + timedelta(minutes=15))):
    # 409 helps the UI differentiate from generic 400/500
    raise HTTPException(status_code=409, detail="Appointment late; please reschedule")

  # 3) Mark ARRIVED (idempotent)
  if row["status"] != "ARRIVED":
    db.execute(text("UPDATE appointments SET status='ARRIVED' WHERE id=:id"), {"id": row["id"]})
    db.commit()

  # 4) Audit the check-in
  audit_safe(
    db=db,
    actor=body.patient_email or "kiosk",
    action="CHECKIN",
    target=str(row["fhir_appointment_id"] or row["id"]),
    details={"appointment_id": row["id"], "status": "ARRIVED", "kiosk_device_id": body.kiosk_device_id},
  )

  # 5) Optional vitals → EHR Observation mock (non-fatal if it fails)
  observation_id = None
  if body.vitals:
    payload = {
      "appointment_id": row["id"],
      "vitals": {k: v for k, v in body.vitals.model_dump().items() if v is not None},
      "effectiveDateTime": now.isoformat(),
    }
    try:
      with httpx.Client(timeout=5.0) as client:
        r = client.post(f"{EHR_BASE}/fhir/Observation", json=payload)
        r.raise_for_status()
        observation_id = r.json().get("id")
    except Exception as e:
      audit_safe(
        db=db,
        actor="system",
        action="EHR_OBSERVATION_POST_FAILED",
        target=str(row["fhir_appointment_id"] or row["id"]),
        details={"error": str(e)},
      )

  # 6) Compute a simple queue position:
  #    count all ARRIVED with smaller id, then +1 = 1-based position
  pos_row = db.execute(
    text("SELECT COUNT(*) AS n FROM appointments WHERE status='ARRIVED' AND id < :id"),
    {"id": row["id"]},
  ).mappings().first()
  position = int((pos_row["n"] if pos_row and pos_row["n"] is not None else 0) + 1)

  # 7) Produce a synthetic Encounter id; the summary API will derive from it
  encounter_id = f"enc-{row['id']}"

  return {
    "appointment": {
      "id": row["id"],
      "fhir_appointment_id": row["fhir_appointment_id"],
      "status": "ARRIVED",
      "reason": row["reason"],
      "start_at": row["start_at"].isoformat() if row["start_at"] else None,
      "end_at": row["end_at"].isoformat() if row["end_at"] else None,
    },
    "position": position,
    "encounter_id": encounter_id,
    "observation_id": observation_id,
    "message": "Checked in",
  }
