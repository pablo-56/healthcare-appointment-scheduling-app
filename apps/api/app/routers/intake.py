# apps/api/app/routers/intake.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from sqlalchemy import text, bindparam
import sqlalchemy as sa
import httpx
from datetime import datetime
from ..db import SessionLocal
from ..tasks.intake import render_intake_pdf

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Lightweight intake form set (3 sections) ---
# Keep it simple but realistic. We can branch on reason later if you want.
FORMS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Demographics",
        "schema": {
            "type": "object",
            "properties": {
                "full_name": {"title": "Full name", "type": "string"},
                "dob": {"title": "Date of birth", "type": "string"},
                "address": {"title": "Address", "type": "string"},
                "email": {"title": "Email", "type": "string"},
            },
            "required": ["full_name"],
        },
    },
    {
        "id": 2,
        "title": "Coverage",
        "schema": {
            "type": "object",
            "properties": {
                "insurer": {"title": "Insurer", "type": "string"},
                "insurance_number": {"title": "Insurance ID", "type": "string"},
            },
            "required": [],
        },
    },
    {
        "id": 3,
        "title": "Screeners",
        "schema": {
            "type": "object",
            "properties": {
                "has_fever": {"title": "Do you have fever?", "type": "boolean"},
                "medications": {"title": "Current medications", "type": "string"},
                "allergies": {"title": "Allergies", "type": "string"},
            },
            "required": ["has_fever"],
        },
    },
]

@router.get("/v1/intake/forms")
def get_intake_forms(appointment_id: int = Query(...), db=Depends(get_db)):
    """
    Return a consistent array shape the UI expects: { forms: [ {id,title,schema}, ... ] }.
    """
    # Fail early if appointment doesn’t exist (lets UI show a clean error).
    row = db.execute(text("SELECT id FROM appointments WHERE id=:id"), {"id": appointment_id}).first()
    if not row:
        raise HTTPException(404, "Appointment not found")
    return {"appointment_id": appointment_id, "forms": FORMS}

class IntakeSubmit(BaseModel):
    answers: Dict[str, Any]  # flattened as "<formId>.<field>" -> value

def _validate_required(forms: List[Dict[str, Any]], answers: Dict[str, Any]) -> Dict[str, str]:
    """
    Build { "<formId>.<field>": "Required" } when any required field is missing/empty.
    """
    errors: Dict[str, str] = {}
    for f in forms:
        fid = f["id"]
        req = (f.get("schema") or {}).get("required", []) or []
        for field in req:
            key = f"{fid}.{field}"
            val = answers.get(key, None)
            if (val is None) or (isinstance(val, str) and not val.strip()):
                errors[key] = "Required"
    return errors

def _consent_needed(db, appointment_id: int, answers: Dict[str, Any]) -> bool:
    """
    Simple rule: if no existing Consent doc for this appointment, require consent.
    (You can add richer payer/policy rules later.)
    """
    row = db.execute(
        text(
            "SELECT 1 FROM documents "
            "WHERE kind='Consent' AND (meta->>'appointment_id') = :aid LIMIT 1"
        ),
        {"aid": str(appointment_id)},
    ).first()
    return row is None

@router.post("/v1/intake/forms/{appointment_id}/submit")
def submit_intake(
    appointment_id: int = Path(...),
    body: IntakeSubmit = ...,
    x_purpose_of_use: Optional[str] = Header(None, alias="X-Purpose-Of-Use"),
    db=Depends(get_db)
):
    # --- 0) PoU: accept TREATMENT / OPERATIONS like the rest of your API ---
    if not x_purpose_of_use or x_purpose_of_use.upper() not in ("TREATMENT", "OPERATIONS"):
        raise HTTPException(400, "X-Purpose-Of-Use required (TREATMENT|OPERATIONS)")

    # --- 1) Validate required fields and return a "soft" 200 with errors for UI highlighting ---
    errors = _validate_required(FORMS, body.answers or {})
    if errors:
        # UI will keep user on the page, highlight fields, and preserve answers
        return {"ok": False, "errors": errors}

    # --- 2) Persist intake answers (your original behavior) ---
    db.execute(
        text("INSERT INTO intake_forms (appointment_id, answers_json, created_at) "
             "VALUES (:aid, :ans, NOW())")
        .bindparams(bindparam("ans", type_=sa.JSON())),
        {"aid": appointment_id, "ans": body.answers},
    )
    db.execute(
        text("INSERT INTO audit_logs (actor, action, target, details, created_at) "
             "VALUES (:actor, 'INTAKE_SUBMITTED', :t, :d, NOW())")
        .bindparams(bindparam("d", type_=sa.JSON())),
        {"actor": "patient", "t": str(appointment_id), "d": {"count": len(body.answers)}},
    )
    db.commit()

    # --- 3) Fire PDF render (async, non-blocking) ---
    try:
        render_intake_pdf.delay(appointment_id, body.answers)
    except Exception:
        pass  # do not block user flow in dev

    # --- 4) Decide next step: Consent OR Docs ---
    if _consent_needed(db, appointment_id, body.answers):
        # Create a signature request now (kicked off by intake submission)
        signer_name = str(body.answers.get("1.full_name") or "Patient")
        signer_email = str(body.answers.get("1.email") or "patient@example.com")

        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    "http://localhost:8000/v1/signature/requests",
                    json={"appointment_id": appointment_id, "signer_name": signer_name, "email": signer_email},
                    headers={"X-Purpose-Of-Use": "OPERATIONS"},
                )
                r.raise_for_status()
            rid = r.json().get("request_id")
        except httpx.HTTPError as e:
            # Could not create request → treat like server error; UI will toast & preserve answers
            raise HTTPException(502, f"Signature provider error: {e}")

        return {"ok": True, "next": "consent", "request_id": rid, "appointment_id": appointment_id}

    # Otherwise, skip to Docs
    return {"ok": True, "next": "docs", "appointment_id": appointment_id}
