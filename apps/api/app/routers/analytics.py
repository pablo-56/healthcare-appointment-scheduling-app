# apps/api/app/routers/analytics.py
from __future__ import annotations

import csv, io
from typing import Optional, Dict, Any, List

import sqlalchemy as sa
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.db import get_db
from app.middleware.purpose_of_use import pou_required  # shows PoU header in Swagger
from app.models import Experiment  # ORM: id, name, status, variants(JSON), start_at, end_at, created_at

router = APIRouter(prefix="/v1", tags=["analytics", "experiments"])

# -------------- small helpers ------------------------------------------------
def _table_exists(db: Session, table: str) -> bool:
    q = text("""SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name=:t""")
    return db.execute(q, {"t": table}).first() is not None

def _columns(db: Session, table: str) -> set[str]:
    q = text("""SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name=:t""")
    return {r[0] for r in db.execute(q, {"t": table}).all()}

def _pick_first_present(db: Session, table: str, candidates: list[str]) -> Optional[str]:
    cols = _columns(db, table)
    for c in candidates:
        if c in cols:
            return c
    return None

def _csv_response(rows: list[Dict[str, Any]]):
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return StreamingResponse(iter([buf.getvalue().encode("utf-8")]), media_type="text/csv")

# -------------- /v1/analytics/ops -------------------------------------------
@router.get(
    "/analytics/ops",
    dependencies=[Depends(pou_required({"OPERATIONS"}))],
    summary="Ops metrics: no-show rate, avg time-to-appointment (hours)",
)
def analytics_ops(request: Request, csv: int = Query(0, ge=0, le=1), db: Session = Depends(get_db)):
    if not _table_exists(db, "appointments"):
        data = {"available": False, "reason": "appointments table not found"}
        return _csv_response([data]) if csv else data

    status_col  = _pick_first_present(db, "appointments", ["status", "state"])
    start_col   = _pick_first_present(db, "appointments", ["start_at", "starts_at", "scheduled_at"])
    created_col = _pick_first_present(db, "appointments", ["created_at", "booked_at"])

    noshow_sql = "0.0" if not status_col else f"""
      CASE WHEN COUNT(*)=0 THEN 0.0
           ELSE SUM(CASE WHEN lower({status_col}) IN ('no_show','noshow') THEN 1 ELSE 0 END)::float
                / COUNT(*)::float
      END
    """
    tta_sql = "NULL" if not (start_col and created_col) else f"""
      AVG(EXTRACT(EPOCH FROM ({start_col} - {created_col})))/3600.0
    """

    row = db.execute(text(f"SELECT {noshow_sql} AS no_show_rate, {tta_sql} AS tta_hours_avg FROM appointments")).mappings().first() or {}
    data = {"available": True, "no_show_rate": row.get("no_show_rate"), "tta_hours_avg": row.get("tta_hours_avg")}
    return _csv_response([data]) if csv else data

# -------------- /v1/analytics/rcm -------------------------------------------
@router.get(
    "/analytics/rcm",
    dependencies=[Depends(pou_required({"OPERATIONS"}))],
    summary="RCM metrics: first-pass acceptance; DSO if available",
)
def analytics_rcm(request: Request, csv: int = Query(0, ge=0, le=1), db: Session = Depends(get_db)):
    fpa = None
    if _table_exists(db, "eligibility_responses"):
        r = db.execute(text("""
            SELECT COUNT(*)::float AS total,
                   SUM(CASE WHEN eligible THEN 1 ELSE 0 END)::float AS ok
            FROM eligibility_responses
        """)).mappings().first()
        total = (r["total"] or 0.0) if r else 0.0
        ok = (r["ok"] or 0.0) if r else 0.0
        fpa = (ok / total) if total else None

    dso = None; dso_available = False
    if _table_exists(db, "payments") and _table_exists(db, "invoices"):
        dso_available = True
        r = db.execute(text("""
            SELECT AVG(EXTRACT(EPOCH FROM (p.received_at - i.issued_at)))/86400.0 AS dso
            FROM invoices i JOIN payments p ON p.invoice_id = i.id
            WHERE p.received_at IS NOT NULL AND i.issued_at IS NOT NULL
        """)).mappings().first()
        dso = r.get("dso") if r else None

    data = {"available": True, "first_pass_acceptance": fpa, "dso": dso, "dso_available": dso_available}
    return _csv_response([data]) if csv else data

# -------------- Experiments: POST + GET list --------------------------------
from pydantic import BaseModel, Field, validator
from sqlalchemy.dialects.postgresql import JSON as PGJSON

class ExperimentIn(BaseModel):
    name: str = Field(..., max_length=128, description="e.g. reminders_v1")
    status: str = Field("open", pattern="^(open|paused|closed)$")
    # variants is a dict: {"A": {subject, channel, timing_min}, "B": {...}}
    variants: Dict[str, Dict[str, Any]]
    start_at: Optional[str] = None
    end_at: Optional[str] = None

    @validator("variants")
    def validate_variants(cls, v: Dict[str, Dict[str, Any]]):
        if not v or not isinstance(v, dict):
            raise ValueError("variants must be an object like {\"A\":{...}}")
        for k, meta in v.items():
            subj = (meta or {}).get("subject")
            ch = (meta or {}).get("channel")
            tmin = (meta or {}).get("timing_min")
            if not subj or not isinstance(subj, str):
                raise ValueError(f'variant "{k}": subject is required')
            if ch not in {"sms", "email"}:
                raise ValueError(f'variant "{k}": channel must be "sms" or "email"')
            try:
                tmin = int(tmin)
                if tmin <= 0:
                    raise ValueError()
            except Exception:
                raise ValueError(f'variant "{k}": timing_min must be a positive integer')
        return v

@router.post(
    "/experiments",
    dependencies=[Depends(pou_required({"OPERATIONS"}))],
    summary="Create or upsert an experiment with reminder variants",
)
def create_experiment(body: ExperimentIn, db: Session = Depends(get_db)):
    # upsert by name
    exists = db.execute(text("SELECT id FROM experiments WHERE name=:n"), {"n": body.name}).first()
    if exists:
        db.execute(
            text("""
              UPDATE experiments
                 SET status=:s,
                     variants=:v::json,
                     start_at=COALESCE(:start, start_at),
                     end_at=COALESCE(:end, end_at)
               WHERE name=:n
            """).bindparams(bindparam("v", type_=PGJSON)),
            {"n": body.name, "s": body.status, "v": body.variants, "start": body.start_at, "end": body.end_at},
        )
        row = db.execute(text("SELECT * FROM experiments WHERE name=:n"), {"n": body.name}).mappings().first()
        db.commit()
        return row

    exp = Experiment(name=body.name, status=body.status, variants=body.variants,
                     start_at=body.start_at, end_at=body.end_at)
    db.add(exp); db.commit(); db.refresh(exp)
    return {"id": exp.id, "name": exp.name, "status": exp.status, "variants": exp.variants,
            "start_at": exp.start_at, "end_at": exp.end_at, "created_at": exp.created_at}

@router.get(
    "/experiments",
    dependencies=[Depends(pou_required({"OPERATIONS"}))],
    summary="List experiments",
)
def list_experiments(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id, name, status, variants, start_at, end_at, created_at
          FROM experiments ORDER BY id DESC LIMIT :n
    """), {"n": limit}).mappings().all()
    return {"items": [dict(r) for r in rows]}
