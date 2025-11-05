# apps/api/app/routers/admin.py
from __future__ import annotations

from fastapi import APIRouter, Query, Depends, HTTPException, Header, Body  # <-- add Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any  # <-- ensure these are present

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



def _require_ops_pou(x_purpose_of_use: Optional[str]):
    if not x_purpose_of_use or x_purpose_of_use.upper() != "OPERATIONS":
        raise HTTPException(status_code=403, detail="Missing/invalid X-Purpose-Of-Use")

@router.post("/tasks")
def create_admin_task(
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    x_purpose_of_use: Optional[str] = Header(None, alias="X-Purpose-Of-Use"),
):
    """
    Admin-only helper to create follow-up tasks that don't fit the public /v1/tasks schema.
    Expected body:
      {
        "type": "eligibility_followup",
        "status": "open" | "in_progress" | "done",
        "payload_json": { ... arbitrary JSON ... }
      }
    """
    _require_ops_pou(x_purpose_of_use)

    # Ensure minimal 'tasks' schema exists (idempotent)
    db.execute(text("""
      CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        payload_json JSON NOT NULL DEFAULT '{}'::json,
        assignee TEXT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    """))

    ttype = str(body.get("type") or "eligibility_followup")
    status = str(body.get("status") or "open").lower()
    payload = body.get("payload_json") or {}

    row = db.execute(
        text("""
          INSERT INTO tasks(type, status, payload_json)
          VALUES (:t, :s, :p)
          RETURNING id
        """).bindparams(bindparam("p", type_=sa.JSON())),
        {"t": ttype, "s": status, "p": payload},
    ).first()
    db.commit()
    return {"id": int(row[0]), "type": ttype, "status": status}