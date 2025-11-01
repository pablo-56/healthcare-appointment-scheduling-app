# apps/api/app/routers/analytics.py
from __future__ import annotations

import csv
import io
import math
from typing import Optional, Dict, Any

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse

from app.db import get_db
from app.middleware.purpose_of_use import pou_required  # shows header in Swagger when used

router = APIRouter(prefix="/v1", tags=["analytics", "experiments"])

# ---------- utils -------------------------------------------------------------

def _table_exists(db: Session, table: str) -> bool:
    q = text("""
        SELECT 1 FROM information_schema.tables
         WHERE table_schema='public' AND table_name=:t
        """)
    return db.execute(q, {"t": table}).first() is not None

def _columns(db: Session, table: str) -> set[str]:
    q = text("""
      SELECT column_name
        FROM information_schema.columns
       WHERE table_schema='public' AND table_name=:t
    """)
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
    return StreamingResponse(iter([buf.getvalue().encode("utf-8")]),
                             media_type="text/csv")

# ---------- /v1/analytics/ops ------------------------------------------------
@router.get(
    "/analytics/ops",
    dependencies=[Depends(pou_required({"OPERATIONS"}))],  # header appears in Swagger; one copy only
    summary="Ops metrics (no-show rate, time-to-appointment avg hours)",
)
def analytics_ops(
    request: Request,
    csv: int = Query(0, ge=0, le=1),
    db: Session = Depends(get_db),
):
    if not _table_exists(db, "appointments"):
        data = {"available": False, "reason": "appointments table not found"}
        return _csv_response([data]) if csv else data

    status_col = _pick_first_present(db, "appointments", ["status", "state"])
    start_col  = _pick_first_present(db, "appointments", ["starts_at", "scheduled_at", "start_time"])
    created_col= _pick_first_present(db, "appointments", ["created_at", "booked_at"])

    # Build dynamic, tolerant SQL
    noshow_sql = "0.0"
    if status_col:
        noshow_sql = f"""
          CASE WHEN COUNT(*)=0 THEN 0.0
               ELSE SUM(CASE WHEN lower({status_col}) IN ('no_show','noshow') THEN 1 ELSE 0 END)::float
                    / COUNT(*)::float
          END
        """

    tta_sql = "NULL"
    if start_col and created_col:
        tta_sql = f"""
          AVG(EXTRACT(EPOCH FROM ({start_col} - {created_col})))/3600.0
        """

    sql = f"""
      SELECT
        {noshow_sql} AS no_show_rate,
        {tta_sql}    AS tta_hours_avg
      FROM appointments
    """
    row = db.execute(text(sql)).mappings().first() or {}
    data = {
        "available": True,
        "no_show_rate": row.get("no_show_rate"),
        "tta_hours_avg": row.get("tta_hours_avg"),
    }
    return _csv_response([data]) if csv else data

# ---------- /v1/analytics/rcm ------------------------------------------------
@router.get(
    "/analytics/rcm",
    dependencies=[Depends(pou_required({"OPERATIONS"}))],
    summary="RCM metrics (first-pass acceptance from eligibility; DSO if available)",
)
def analytics_rcm(
    request: Request,
    csv: int = Query(0, ge=0, le=1),
    db: Session = Depends(get_db),
):
    # First-pass acceptance from eligibility_responses(eligible bool)
    fpa = None
    if _table_exists(db, "eligibility_responses"):
        q = text("""
            SELECT
              COUNT(*)::float AS total,
              SUM(CASE WHEN eligible THEN 1 ELSE 0 END)::float AS ok
            FROM eligibility_responses
        """)
        r = db.execute(q).mappings().first()
        total = (r["total"] or 0.0) if r else 0.0
        ok = (r["ok"] or 0.0) if r else 0.0
        fpa = (ok / total) if total else None

    # DSO (optional) — try common schemas, otherwise mark unavailable
    dso = None
    dso_available = False
    if _table_exists(db, "payments") and _table_exists(db, "invoices"):
        dso_available = True
        r = db.execute(text("""
          SELECT AVG(EXTRACT(EPOCH FROM (p.received_at - i.issued_at)))/86400.0 AS dso
            FROM invoices i
            JOIN payments p ON p.invoice_id = i.id
           WHERE p.received_at IS NOT NULL AND i.issued_at IS NOT NULL
        """)).mappings().first()
        dso = r.get("dso") if r else None

    data = {
        "available": True,
        "first_pass_acceptance": fpa,
        "dso": dso,
        "dso_available": dso_available,
    }
    return _csv_response([data]) if csv else data

# ---------- /v1/experiments (define variants) --------------------------------
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlalchemy import bindparam, cast
from app.models import Experiment

class ExperimentIn(BaseModel):
    name: str = Field(..., max_length=128)
    status: str = Field("open", pattern="^(open|paused|closed)$")
    variants: dict  # validated JSON (subject, channel, timing)
    start_at: Optional[str] = None
    end_at: Optional[str] = None

@router.post(
    "/experiments",
    dependencies=[Depends(pou_required({"OPERATIONS"}))],
    summary="Create or upsert an experiment with reminder variants",
)
def create_experiment(body: ExperimentIn, db: Session = Depends(get_db)):
    # Upsert by name to be convenient for admin flows
    existing = db.execute(
        text("SELECT id FROM experiments WHERE name=:n"),
        {"n": body.name},
    ).first()

    if existing:
        db.execute(
            text("""
              UPDATE experiments
                 SET status=:s,
                     variants = :v::json,
                     start_at = COALESCE(:start_at, start_at),
                     end_at   = COALESCE(:end_at, end_at)
               WHERE name=:n
            """).bindparams(
                bindparam("v", type_=PGJSON)  # <-- JSON bound safely (no psycopg2 ::json error)
            ),
            {"n": body.name, "s": body.status,
             "v": body.variants, "start_at": body.start_at, "end_at": body.end_at},
        )
        row = db.execute(text("SELECT * FROM experiments WHERE name=:n"), {"n": body.name}).mappings().first()
        db.commit()
        return row

    # Create new via ORM (cleanest for JSON columns)
    exp = Experiment(
        name=body.name,
        status=body.status,
        variants=body.variants,
        start_at=body.start_at,
        end_at=body.end_at,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return {
        "id": exp.id,
        "name": exp.name,
        "status": exp.status,
        "variants": exp.variants,
        "start_at": exp.start_at,
        "end_at": exp.end_at,
        "created_at": exp.created_at,
    }
