# apps/api/app/routers/billing.py
from __future__ import annotations
import sqlalchemy as sa
import json, datetime as dt, httpx, logging
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from datetime import datetime
import httpx, os
from ..db import SessionLocal, get_db
from ..settings import settings
from ..middleware.purpose_of_use import require_pou
from ..celery_app import celery_app

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["billing"])

# --- shared DB session helper (keeps your pattern) ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- minimal schema bootstrap so you don't need a migration for the demo -----
# NOTE: does nothing if the table already exists.
CREATE_CLAIMS_SQL = """
CREATE TABLE IF NOT EXISTS claims (
  id SERIAL PRIMARY KEY,
  encounter_id TEXT NOT NULL,
  appointment_id INT NULL,
  patient_id INT NULL,
  status TEXT NOT NULL DEFAULT 'NEW',         -- NEW | SUBMITTED | PAID | DENIED | REJECTED
  payer_ref TEXT NULL,                        -- clearinghouse reference / claim # returned by adapter
  total_cents INT NULL,
  payload_json JSON NOT NULL DEFAULT '{}'::json,  -- "837-like" assembled payload
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_claims_status ON claims(status);
"""

# imports (make sure both are present)
def _ensure_claims_schema(db: Session) -> None:
    """
    Dev-safe: create 'claims' if missing and add any columns we need.
    Idempotent on every call. Avoids dropping user data.
    """
    # Create if not exists with a minimal skeleton
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS claims (
          id SERIAL PRIMARY KEY
        )
    """))

    # Add/patch columns we need (no failures if they already exist)
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS encounter_id TEXT"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS appointment_id INT"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS patient_id INT REFERENCES patients(id)"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'NEW'"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS total_cents INT NOT NULL DEFAULT 0"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS payload_json JSON NOT NULL DEFAULT '{}'::json"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()"))

    # Optional: if you want NOT NULL on encounter_id later, only set it after backfilling
    db.commit()

# --- seed endpoint (dev only) ------------------------------------------------

@router.post(
    "/coding/seed",  # NOTE: no leading /v1 here; router already has prefix="/v1"
    dependencies=[Depends(require_pou({"OPERATIONS", "PAYMENT"}))],
)
def seed_claim_for_demo(
    encounter_id: str = Query(..., description="E.g., enc-1"),
    appointment_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Dev-only helper to create a simple NEW claim so the UI has data.
    Looks up patient_id from appointment if available.
    """
    _ensure_claims_schema(db)

    # Resolve patient_id from appointments if present (NULL is fine in demo)
    patient_id: Optional[int] = None
    if appointment_id is not None:
        row = db.execute(
            text("SELECT patient_id FROM appointments WHERE id = :id"),
            {"id": appointment_id},
        ).first()
        if row and row[0] is not None:
            patient_id = int(row[0])

    # Minimal demo payload (pass a dict; SQLAlchemy JSON bindparam handles encoding)
    payload = {
        "encounter_id": encounter_id,
        "svc": [{"cpt": "99213", "units": 1, "charge_cents": 12500}],
        "diag": ["J06.9"],
        "facility": "MAIN_CLINIC",
    }
    total_cents = sum(int(s.get("charge_cents", 0)) for s in payload.get("svc", []))

    # Insert using a JSON bindparam; DO NOT json.dumps(payload)
    stmt = text("""
        INSERT INTO claims (encounter_id, appointment_id, patient_id, status, total_cents, payload_json)
        VALUES (:enc, :appt, :pid, 'NEW', :tot, :payload)
        RETURNING id
    """).bindparams(bindparam("payload", type_=sa.JSON()))

    row = db.execute(
        stmt,
        {
            "enc": encounter_id,
            "appt": appointment_id,
            "pid": patient_id,      # may be None (FK allows NULL)
            "tot": total_cents,
            "payload": payload,     # dict -> JSON
        },
    ).first()
    db.commit()

    return {"id": int(row[0]), "status": "NEW"}



# --- required API: open worklist for coder/biller -----------------------------
@router.get(
    "/coding/cases",
    dependencies=[Depends(require_pou({"OPERATIONS", "PAYMENT"}))],
)
def list_coding_cases(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Returns claims that are relevant to coders/billers.
    NEW, SUBMITTED (in-flight), DENIED/REJECTED (work), PAID is filtered out.
    """
    _ensure_claims_table(db)
    rows = db.execute(
        text(
            """
            SELECT id, encounter_id, appointment_id, status, payer_ref, total_cents, payload_json, updated_at
            FROM claims
            WHERE status IN ('NEW','SUBMITTED','DENIED','REJECTED')
            ORDER BY updated_at DESC
            LIMIT :n
            """
        ),
        {"n": limit},
    ).mappings().all()
    return {"items": [dict(r) for r in rows]}

# Convenience: detail for the claim page
@router.get(
    "/claims/{claim_id}",
    dependencies=[Depends(require_pou({"OPERATIONS", "PAYMENT"}))],
)
def get_claim(claim_id: int = Path(...), db: Session = Depends(get_db)):
    _ensure_claims_table(db)
    row = db.execute(
        text("SELECT * FROM claims WHERE id=:id"),
        {"id": claim_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Claim not found")
    return dict(row)

# --- required API: submit a claim to the billing adapter ----------------------

# ---------------------------------------------------------------------------
# Schema helpers (idempotent — safe to call every time)
# ---------------------------------------------------------------------------

def _ensure_claims_schema(db: Session) -> None:
    db.execute(text("CREATE TABLE IF NOT EXISTS claims (id SERIAL PRIMARY KEY)"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS encounter_id TEXT"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS appointment_id INT"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS patient_id INT REFERENCES patients(id)"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'NEW'"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS total_cents INT NOT NULL DEFAULT 0"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS payload_json JSON NOT NULL DEFAULT '{}'::json"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS payer_ref TEXT"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS last_submit_at TIMESTAMP"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS clearinghouse_resp JSON"))
    db.execute(text("ALTER TABLE claims ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()"))
    db.commit()

# old callsites used this name; keep an alias so they don’t 500:
def _ensure_claims_table(db: Session) -> None:
    _ensure_claims_schema(db)

# ---------------------------------------------------------------------------
# Simple 837 assembler (demo). In prod, call your Celery task instead.
# ---------------------------------------------------------------------------

def _assemble_837(payload: Dict[str, Any]) -> str:
    enc = payload.get("encounter_id") or "enc-?"
    now = datetime.utcnow()
    total = sum(int(x.get("charge_cents", 0)) for x in payload.get("svc", [])) / 100.0
    segs = [
        f"ISA*00*          *00*          *ZZ*SENDER         *ZZ*PAYERID        *{now:%y%m%d}*{now:%H%M}*^*00501*000000905*0*T*:~",
        "GS*HC*SENDER*PAYERID*20250101*0101*1*X*005010X222A1~",
        "ST*837*0001*005010X222A1~",
        f"BHT*0019*00*{enc}*{now:%Y%m%d}*{now:%H%M}*CH~",
        "SE*5*0001~",
        "GE*1*1~",
        "IEA*1*000000905~",
        f"NM1*GW*1*TOTAL****{total:.2f}~",
    ]
    return "\n".join(segs)

ADAPTER_BASE = getattr(settings, "billing_adapter_base", os.getenv("BILLING_ADAPTER_BASE", "http://billing-adapter:9100"))

# ---------------------------------------------------------------------------
# DEV helper already provided earlier: POST /v1/coding/seed (keep yours)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Submit a claim -> billing-adapter; update status & payer_ref
# ---------------------------------------------------------------------------

@router.post(
    "/claims/{claim_id}/submit",
    dependencies=[Depends(require_pou({"PAYMENT", "OPERATIONS"}))],
)
def submit_claim(
    claim_id: int = Path(...),
    db: Session = Depends(get_db),
    x_purpose_of_use: Optional[str] = Header(default=None, convert_underscores=False),
):
    _ensure_claims_table(db)

    row = db.execute(
        text("""
            SELECT id, status, payload_json
            FROM claims
            WHERE id = :id
        """),
        {"id": claim_id},
    ).mappings().first()

    if not row:
        raise HTTPException(404, detail="Claim not found")

    status = (row["status"] or "").upper()
    if status not in {"NEW", "RESUBMIT", "DENIED"}:
        raise HTTPException(409, detail=f"Claim is {status}; cannot submit")

    payload = row["payload_json"] or {}
    edi837 = _assemble_837(payload)

    # Try billing-adapter; fall back to a simulated accept if unavailable
    payer_ref = f"demo-{claim_id}"
    ch_resp: Dict[str, Any] = {"simulated": True, "accepted": True}

    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(
                f"{ADAPTER_BASE}/claims",
                json={"claim_id": claim_id, "edi837": edi837, "payload": payload},
            )
            if r.status_code < 300:
                data = r.json()
                payer_ref = data.get("payer_ref") or data.get("id") or payer_ref
                ch_resp = data
            else:
                # keep simulated acceptance; surface adapter error for visibility
                ch_resp = {"simulated": True, "adapter_status": r.status_code, "adapter_body": r.text}
    except Exception as e:
        ch_resp = {"simulated": True, "error": str(e)}

    # Persist submission outcome
     # Persist submission outcome (no bindparams, cast the JSON explicitly)
    db.execute(
        text("""
            UPDATE claims
            SET status = :status,
                payer_ref = :ref,
                last_submit_at = NOW(),
                clearinghouse_resp = CAST(:resp AS JSON)
            WHERE id = :id
        """),
        {
            "id": claim_id,
            "status": "SUBMITTED",
            "ref": payer_ref,
            # store the whole adapter/simulated response as JSON
            "resp": json.dumps(ch_resp),
        },
    )
    db.commit()

    return {
        "id": claim_id,
        "status": "SUBMITTED",
        "payer_ref": payer_ref,
        "adapter_base": ADAPTER_BASE,
        "simulated": bool(ch_resp.get("simulated")),
    }

# --- optional: mock an 835 remit to flip status (PAID or DENIED) -------------
@router.post(
    "/remits/mock",
    dependencies=[Depends(require_pou({"PAYMENT", "OPERATIONS"}))],
)
def mock_835_ingest(
    claim_id: int = Query(...),
    paid_cents: int = Query(0, ge=0),
    denial_code: Optional[str] = Query(None, description="E.g., CO-97"),
    db: Session = Depends(get_db),
):
    """
    Testing helper: simulate an 835. If paid_cents>0 -> PAID else -> DENIED with code.
    """
    _ensure_claims_table(db)
    payload = {"claim_id": claim_id, "paid_cents": paid_cents, "denial_code": denial_code}
    celery_app.send_task("remits.ingest_835", kwargs={"remit": payload})
    return {"queued": True, "payload": payload}
