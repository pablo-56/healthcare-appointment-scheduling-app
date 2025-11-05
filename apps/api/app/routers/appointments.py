# apps/api/app/routers/appointments.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import text
from app.db import get_db
import httpx, os

router = APIRouter(prefix="/v1/appointments", tags=["appointments"])
EHR = os.getenv("EHR_CONNECTOR_URL", "http://ehr-connector:8100")

# ---------------------------
# CREATE (already in your repo)
# ---------------------------
@router.post("")
def create_appointment(payload: dict, db=Depends(get_db)):
    """
    Expected payload:
    {
      "patient_id": 123,
      "reason": "annual physical",
      "start": "...Z",
      "end": "...Z",
      "source_channel": "web" | "portal" | "sms" | "admin" | ...
    }
    """
    # 1) Create in EHR mock (returns a FHIR Appointment id)
    try:
        appt_fhir = {
            "status": "booked",
            "reasonCode": [{"text": payload.get("reason")}],
            "start": payload.get("start"),
            "end": payload.get("end"),
            "participant": [{
                "actor": {"reference": f"Patient/{payload.get('patient_id','demo')}"}
            }],
        }
        r = httpx.post(f"{EHR}/fhir/Appointment", json=appt_fhir, timeout=5.0)
        r.raise_for_status()
        fhir_appt = r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"EHR error: {e}") from e

    # 2) Normalize source_channel BEFORE insert
    src = str(payload.get("source_channel") or "web").lower()

    # 3) Persist locally
    row = db.execute(
        text("""
        INSERT INTO appointments
          (patient_id, reason, start_at, end_at, status, fhir_appointment_id, source_channel)
        VALUES
          (:pid, :reason, :start, :end, 'BOOKED', :fhir_id, :src)
        RETURNING id
        """),
        {
            "pid": payload.get("patient_id"),
            "reason": payload.get("reason"),
            "start": payload.get("start"),
            "end": payload.get("end"),
            "fhir_id": fhir_appt.get("id"),
            "src": src,
        },
    ).first()

    db.commit()
    return {"ok": True, "id": row[0], "fhir": fhir_appt}

# ---------------------------
# READ (new): /v1/appointments/{id}
# ---------------------------
@router.get("/{appointment_id}")
def read_appointment(
    appointment_id: int,
    db=Depends(get_db),
    x_purpose_of_use: str | None = Header(None, alias="X-Purpose-Of-Use")
):
    """
    Fetch a single appointment to render the Confirm page.
    Allowed PoU: OPERATIONS or TREATMENT (fetcher sends OPERATIONS for GET).
    """
    if not x_purpose_of_use or x_purpose_of_use.upper() not in {"OPERATIONS", "TREATMENT"}:
        # Matches the rest of your PoU style
        raise HTTPException(status_code=400, detail="Missing X-Purpose-Of-Use header")

    row = db.execute(
        text("""
        SELECT
          id, patient_id, reason, start_at, end_at, status,
          fhir_appointment_id, source_channel, created_at
        FROM appointments
        WHERE id = :id
        """),
        {"id": appointment_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"appointment": dict(row)}

# ---------------------------
# UPDATE (OPS/TREATMENT): /v1/appointments/{id}
# Allows front-desk to flip status to ARRIVED/IN_ROOM/NO_SHOW, etc.
# ---------------------------

@router.patch("/{appointment_id}")
def patch_appointment(
    appointment_id: int,
    payload: dict,
    db=Depends(get_db),
    x_purpose_of_use: str | None = Header(None, alias="X-Purpose-Of-Use"),
):
    """
    Minimal patcher for front-desk ops. Supports fields:
      - status: BOOKED | ARRIVED | IN_ROOM | COMPLETED | CANCELED | NO_SHOW
      - reason, start_at, end_at (optional)
    Note: we keep this tight to avoid accidental wide updates from the UI.
    """
    if not x_purpose_of_use or x_purpose_of_use.upper() not in {"OPERATIONS", "TREATMENT"}:
      raise HTTPException(status_code=400, detail="Missing X-Purpose-Of-Use header")

    allowed_status = {"BOOKED", "ARRIVED", "IN_ROOM", "COMPLETED", "CANCELED", "NO_SHOW"}
    updates = []
    params = {"id": appointment_id}

    if "status" in payload:
        new_status = str(payload["status"]).upper()
        if new_status not in allowed_status:
            raise HTTPException(status_code=422, detail="Invalid status")
        updates.append("status = :status")
        params["status"] = new_status

    if "reason" in payload:
        updates.append("reason = :reason")
        params["reason"] = str(payload["reason"])

    if "start_at" in payload:
        updates.append("start_at = :start_at")
        params["start_at"] = payload["start_at"]

    if "end_at" in payload:
        updates.append("end_at = :end_at")
        params["end_at"] = payload["end_at"]

    if not updates:
        # Nothing to do—return 200 with no updates to keep UI simple
        return {"ok": True, "updated": 0}

    row = db.execute(
        text(f"UPDATE appointments SET {', '.join(updates)} WHERE id=:id RETURNING id, status"),
        params,
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Appointment not found")

    db.commit()
    return {"ok": True, "appointment": dict(row)}