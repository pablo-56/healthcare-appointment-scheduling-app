from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Task, EligibilityResponse

router = APIRouter(prefix="/v1/admin", tags=["admin"])

@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    rows = (
        db.query(Task)
        .filter(Task.type == "eligibility_followup")
        .order_by(Task.id.desc())
        .limit(100)
        .all()
    )
    return {
        "items": [
            {"id": r.id, "status": r.status, "payload_json": r.payload_json, "created_at": getattr(r, "created_at", None)}
            for r in rows
        ]
    }

@router.get("/billing/eligibility")
def elig_detail(appointment_id: int = Query(...), db: Session = Depends(get_db)):
    row = (
        db.query(EligibilityResponse)
        .filter(EligibilityResponse.appointment_id == appointment_id)
        .order_by(EligibilityResponse.id.desc())
        .first()
    )
    if not row:
        return {"eligibility": None}
    return {
        "eligibility": {
            "appointment_id": row.appointment_id,
            "eligible": row.eligible,
            "plan": row.plan,
            "copay_cents": row.copay_cents,
            "created_at": row.created_at,
        }
    }
