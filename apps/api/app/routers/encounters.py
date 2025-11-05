# apps/api/app/routers/encounters.py
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..db import get_db

router = APIRouter(prefix="/v1", tags=["encounters"])

def _appt_id_from_enc(encounter_id: str) -> int | None:
    # supports "enc-123" or plain "123"
    if encounter_id.startswith("enc-"):
        enc = encounter_id.split("enc-", 1)[1]
    else:
        enc = encounter_id
    try:
        return int(enc)
    except Exception:
        return None

@router.get("/encounters/{encounter_id}/summary")
def get_summary(encounter_id: str = Path(...), db: Session = Depends(get_db)):
    """
    Returns a simple patient-friendly JSON summary for the encounter.
    If the appointment doesn't exist, return 404 so the Portal UI keeps polling.
    """
    appt_id = _appt_id_from_enc(encounter_id)
    if not appt_id:
        raise HTTPException(404, "Encounter not found")

    row = db.execute(
        text("""
          SELECT id, patient_id, reason, start_at, end_at, status
          FROM appointments WHERE id=:id
        """),
        {"id": appt_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Encounter not found")

    # If you want to simulate "not ready yet", uncomment to return 404 until ARRIVED:
    if row["status"] != "ARRIVED":
        raise HTTPException(404, "Note not ready")

    note = {
        "title": "Visit summary",
        "reason": row["reason"],
        "status": row["status"],
        "when": row["start_at"].isoformat() if row["start_at"] else None,
        "meds": ["Acetaminophen 500 mg PO q6h prn pain"],
        "instructions": [
            "Drink fluids, rest.",
            "If symptoms worsen, call the clinic or go to ER."
        ],
        "follow_up": "Book a follow-up in 1–2 weeks if needed.",
    }
    return {"encounter_id": encounter_id, "note": note}
