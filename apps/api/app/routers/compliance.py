# apps/api/app/routers/compliance.py
from __future__ import annotations
from typing import Optional, Dict, Any, List

import sqlalchemy as sa
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Path
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from app.middleware.purpose_of_use import require_pou, doc_purpose_of_use
from app.db import get_db
from app.celery_app import celery_app
from kombu.exceptions import OperationalError

# If you have Celery tasks wired
from app.tasks.compliance import export_request, pia_pack_generate, erasure_request

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])

# ---------- Bodies ----------
class ExportBody(BaseModel):
    patient_id: int | None = Field(None, description="Restrict export to a patient (optional)")
    reason: str | None = Field(None, description="Business justification / note")

class PiaPackBody(BaseModel):
    scope: str | None = Field(None, description="Optional scope string for the PIA generator")

class ErasureBody(BaseModel):
    patient_id: int = Field(..., description="Patient to erase per policy")
    reason: str | None = Field(None, description="Business justification / note")

# ---------- Helpers ----------
def _redact_meta(meta: dict | None) -> dict | None:
    if not meta or not isinstance(meta, dict):
        return meta
    m = dict(meta)
    for k in ("authorization", "token", "access_token", "id_token"):
        if k in m:
            m[k] = "***"
    return m

# ---------- GET /audit ----------
@router.get(
    "/audit",
    dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],
)
def get_audit(
    request: Request,
    actor: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    since: Optional[str] = Query(None, description="ISO timestamp filter"),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    """
    List audit entries (redacted). Middleware elsewhere appends rows.
    Requires PoU=OPERATIONS; the UI sends it via complianceGet().
    """
    sql = """
        SELECT id, actor, action, target, details, patient_id, created_at
          FROM audit_logs
         WHERE 1=1
    """
    params: dict = {}
    if actor:
        sql += " AND actor = :actor"; params["actor"] = actor
    if patient_id is not None:
        sql += " AND patient_id = :pid"; params["pid"] = patient_id
    if since:
        sql += " AND created_at >= :since"; params["since"] = since
    sql += " ORDER BY id DESC LIMIT :lim"
    params["lim"] = limit

    rows = db.execute(text(sql), params).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d["details"] = _redact_meta(d.get("details"))
        out.append(d)
    return {"items": out, "count": len(out)}

# ---------- POST /export ----------
@router.post(
    "/export",
    dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],
)
def request_export(body: ExportBody | None = None, db: Session = Depends(get_db)):
    meta = (body.model_dump(exclude_none=True) if body else {})
    row = db.execute(
        text("""
            INSERT INTO compliance_requests (kind, status, meta, created_at)
            VALUES ('export', 'NEW', :meta, NOW())
            RETURNING id
        """).bindparams(bindparam("meta", type_=sa.JSON)),
        {"meta": meta},
    ).first()
    db.commit()
    cid = int(row[0])

    try:
        if celery_app.conf.task_always_eager:
            export_request.apply(args=[cid])
        else:
            export_request.delay(cid)
    except OperationalError:
        export_request.apply(args=[cid])

    return {"ok": True, "request_id": cid}

# ---------- POST /pia-pack ----------
@router.post(
    "/pia-pack",
    dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],
)
def request_pia_pack(body: PiaPackBody | None = None, db: Session = Depends(get_db)):
    meta = (body.model_dump(exclude_none=True) if body else {})
    row = db.execute(
        text("""
            INSERT INTO compliance_requests (kind, status, meta, created_at)
            VALUES ('pia_pack', 'NEW', :meta, NOW())
            RETURNING id
        """).bindparams(bindparam("meta", type_=sa.JSON)),
        {"meta": meta},
    ).first()
    db.commit()
    cid = int(row[0])

    try:
        if celery_app.conf.task_always_eager:
            pia_pack_generate.apply(args=[cid])
        else:
            pia_pack_generate.delay(cid)
    except OperationalError:
        # Broker down in dev → run inline; the UI still shows a toast
        pia_pack_generate.apply(args=[cid])

    return {"ok": True, "request_id": cid}

# ---------- POST /erasure ----------
@router.post(
    "/erasure",
    dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],
)
def request_erasure(body: ErasureBody, db: Session = Depends(get_db)):
    meta = body.model_dump(exclude_none=True)
    row = db.execute(
        text("""
            INSERT INTO compliance_requests (kind, status, meta, created_at)
            VALUES ('erasure', 'NEW', :meta, NOW())
            RETURNING id
        """).bindparams(bindparam("meta", type_=sa.JSON)),
        {"meta": meta},
    ).first()
    db.commit()
    cid = int(row[0])

    try:
        if celery_app.conf.task_always_eager:
            erasure_request.apply(args=[cid])
        else:
            erasure_request.delay(cid)
    except OperationalError:
        erasure_request.apply(args=[cid])

    return {"ok": True, "request_id": cid}

# ---------- GET /requests/{id} (status for polling) ----------
@router.get(
    "/requests/{rid}",
    dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],
)
def get_request_status(rid: int = Path(...), db: Session = Depends(get_db)):
    row = db.execute(
        text("""
            SELECT id, kind, status, meta, created_at, finished_at
              FROM compliance_requests
             WHERE id = :id
        """),
        {"id": rid},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Request not found")
    d = dict(row)
    # Return meta as JSON (sa maps OK); UI only reads 'status'
    return d

# ---------- POST /retention (compute counters + rows) ----------
@router.post(
    "/retention",
    dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],
)
def retention_scan(db: Session = Depends(get_db)):
    """
    Very simple retention "scan":
      - Look at documents and compute age (days)
      - Flag those older than 365d (example policy)
      - Return the rows so UI can download CSV
    """
    now = datetime.now(timezone.utc)

    rows = db.execute(
        text("""
            SELECT id AS doc_id, kind, created_at
              FROM documents
          ORDER BY id DESC
             LIMIT 1000
        """)
    ).mappings().all()

    out: List[Dict[str, Any]] = []
    for r in rows:
        created = r["created_at"]
        age_days = 0
        if created:
            # created_at assumed timezone-aware; if not, adjust as needed
            delta = now - created
            age_days = int(delta.total_seconds() // 86400)

        out.append({
            "doc_id": int(r["doc_id"]),
            "kind": r.get("kind") or "",
            "created_at": created.isoformat() if created else None,
            "age_days": age_days,
            "flagged": bool(age_days >= 365),
        })

    return {"ok": True, "generated_at": now.isoformat(), "rows": out}
