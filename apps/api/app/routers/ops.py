# apps/api/app/routers/ops.py
from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from ..db import get_db

router = APIRouter(prefix="/v1/ops", tags=["ops"])

# -----------------------------
# Queue (arrivals / no-shows)
# -----------------------------
@router.get("/queue")
def get_queue(
    db: Session = Depends(get_db),
    horizon_minutes: int = Query(480, ge=30, le=1440),   # next 8h
    lookback_minutes: int = Query(120, ge=0, le=1440),   # past 2h
    include_status: List[str] = Query(["BOOKED", "ARRIVED"]),
):
    """
    Returns upcoming/past-due appointments in a small window for the ops queue.
    The UI renders *fields* (first/last/email/phone), not a raw patient object.
    """
    now = datetime.now(timezone.utc)
    start_window = now - timedelta(minutes=lookback_minutes)
    end_window = now + timedelta(minutes=horizon_minutes)

    rows = db.execute(
        text("""
            SELECT
              a.id,
              a.patient_id,
              a.start_at,
              a.end_at,
              a.status,
              a.reason,
              a.fhir_appointment_id,
              p.first_name,
              p.last_name,
              p.email,
              p.phone
            FROM appointments a
            LEFT JOIN patients p ON p.id = a.patient_id
            WHERE a.start_at BETWEEN :start_window AND :end_window
              AND a.status = ANY(:include_status)
            ORDER BY a.start_at ASC
        """),
        {
            "start_window": start_window,
            "end_window": end_window,
            "include_status": include_status,
        },
    ).mappings().all()

    queue = []
    for r in rows:
        start_at = r["start_at"]
        late = False
        no_show = False
        minutes_to_start = None
        minutes_since_start = None

        if start_at:
            delta = start_at - now
            minutes_to_start = int(delta.total_seconds() // 60)
            minutes_since_start = int((now - start_at).total_seconds() // 60)

            # Simple rules:
            # - LATE: ARRIVED but >5 min after start time
            # - NO_SHOW: BOOKED and now > start+15 min (hasn't checked in)
            if r["status"] == "ARRIVED" and minutes_since_start > 5:
                late = True
            if r["status"] == "BOOKED" and minutes_since_start > 15:
                no_show = True

        queue.append({
            "appointment_id": r["id"],
            "status": r["status"],
            "reason": r["reason"],
            "fhir_appointment_id": r["fhir_appointment_id"],
            "start_at": start_at.isoformat() if start_at else None,
            "end_at": r["end_at"].isoformat() if r["end_at"] else None,
            "patient": {
                "id": r["patient_id"],
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "email": r["email"],
                "phone": r["phone"],
            },
            "minutes_to_start": minutes_to_start,
            "late": late,
            "no_show": no_show,
        })

    return {"items": queue, "now": now.isoformat()}


# -----------------------------
# Escalations (urgent cases)
# -----------------------------
def _require_ops_pou(x_purpose_of_use: Optional[str]):
    if not x_purpose_of_use or x_purpose_of_use.upper() != "OPERATIONS":
        raise HTTPException(403, detail="Missing/invalid X-Purpose-Of-Use")

@router.get("/escalations")
def get_escalations(
    x_purpose_of_use: Optional[str] = Header(None, alias="X-Purpose-Of-Use"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Returns open care escalations (e.g., high PHQ-9). Requires PoU=OPERATIONS.
    The UI should render selected fields; API returns a flat task row.
    """
    _require_ops_pou(x_purpose_of_use)

    rows = db.execute(
        text(f"""
            SELECT id, type, status, payload_json, assignee, created_at
              FROM tasks
             WHERE type='care_escalation' AND status='open'
          ORDER BY id DESC
             LIMIT :n
        """),
        {"n": limit},
    ).mappings().all()

    return {"items": [dict(r) for r in rows]}
