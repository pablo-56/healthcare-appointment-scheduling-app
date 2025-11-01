# apps/api/app/routers/intake.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
from sqlalchemy import text, bindparam
import sqlalchemy as sa
from ..db import SessionLocal
from ..tasks.intake import render_intake_pdf

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Simple schemas per reason; expand as you wish
SCHEMAS = {
    "annual physical": {
        "type": "object",
        "properties": {
            "has_fever": {"type": "boolean"},
            "medications": {"type": "string"},
            "allergies": {"type": "string"},
            "insurance_number": {"type": "string"},
        },
        "required": ["has_fever"],
        "additionalProperties": True,
    },
    "default": {
        "type": "object",
        "properties": {"reason_free_text": {"type": "string"}},
    },
}

@router.get("/v1/intake/forms")
def get_intake_form(appointment_id: int = Query(...), db=Depends(get_db)):
    row = db.execute(text("SELECT reason FROM appointments WHERE id=:id"), {"id": appointment_id}).first()
    if not row:
        raise HTTPException(404, "Appointment not found")
    reason = (row.reason or "").strip().lower()
    schema = SCHEMAS.get(reason, SCHEMAS["default"])
    return {"appointment_id": appointment_id, "reason": reason, "schema": schema}

class IntakeSubmit(BaseModel):
    answers: Dict[str, Any]

@router.post("/v1/intake/forms/{appointment_id}/submit")
def submit_intake(
    appointment_id: int = Path(...),
    body: IntakeSubmit = ...,
    x_purpose_of_use: Optional[str] = Header(None, alias="X-Purpose-Of-Use"),
    db=Depends(get_db)
):
    if not x_purpose_of_use or x_purpose_of_use.upper() not in ("TREATMENT", "OPERATIONS"):
        raise HTTPException(400, "X-Purpose-Of-Use required (TREATMENT|OPERATIONS)")

    # store answers in intake_forms
    db.execute(
        text("INSERT INTO intake_forms (appointment_id, answers_json, created_at) "
             "VALUES (:aid, :ans, NOW())")
        .bindparams(bindparam("ans", type_=sa.JSON())),
        {"aid": appointment_id, "ans": body.answers},
    )
    # audit
    db.execute(
        text("INSERT INTO audit_logs (actor, action, target, details, created_at) "
             "VALUES (:actor, 'INTAKE_SUBMITTED', :t, :d, NOW())")
        .bindparams(bindparam("d", type_=sa.JSON())),
        {"actor": "patient", "t": str(appointment_id), "d": {"count": len(body.answers)}},
    )
    db.commit()

    # fire PDF render (async)
    render_intake_pdf.delay(appointment_id, body.answers)
    return {"ok": True}
