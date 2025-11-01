# apps/api/app/routers/compliance.py
from __future__ import annotations

from typing import Optional

import sqlalchemy as sa
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel, Field
from app.middleware.purpose_of_use import require_pou, doc_purpose_of_use
from app.db import get_db
from app.middleware.purpose_of_use import require_pou
from app.tasks.compliance import export_request, pia_pack_generate, erasure_request
from app.celery_app import celery_app
from kombu.exceptions import OperationalError

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])

# ---------- Bodies so Swagger shows parameters ----------

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

@router.get("/audit", dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],)
def get_audit(
    request: Request,
    actor: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    since: Optional[str] = Query(None, description="ISO timestamp filter"),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    """
    List audit entries (redacted). Rows are appended by middleware elsewhere.
    """
    sql = """
        SELECT id, actor, action, target, details, patient_id, created_at
          FROM audit_logs
         WHERE 1=1
    """
    params: dict = {}
    if actor:
        sql += " AND actor = :actor"
        params["actor"] = actor
    if patient_id is not None:
        sql += " AND patient_id = :pid"
        params["pid"] = patient_id
    if since:
        # 'since' applies to created_at in your schema
        sql += " AND created_at >= :since"
        params["since"] = since
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

@router.post("/export", dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],)
def request_export(body: ExportBody | None = None, db: Session = Depends(get_db)):
    """
    Create an export compliance request. Accepts optional patient_id / reason.
    """
    meta = (body.model_dump(exclude_none=True) if body else {})

    stmt = (
        text("""
            INSERT INTO compliance_requests (kind, status, meta, created_at)
            VALUES (:kind, :status, :meta, NOW())
            RETURNING id
        """)
        .bindparams(bindparam("meta", type_=sa.JSON))
    )

    row = db.execute(stmt, {"kind": "export", "status": "NEW", "meta": meta}).first()
    db.commit()
    cid = int(row[0])

    try:
        if celery_app.conf.task_always_eager:
            export_request.apply(args=[cid])
        else:
            export_request.delay(cid)
    except OperationalError:
        # Broker not up in dev -> run inline so the API doesn’t 500
        export_request.apply(args=[cid])

    return {"ok": True, "request_id": cid}

# ---------- POST /pia-pack ----------

@router.post("/pia-pack", dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],)
def request_pia_pack(body: PiaPackBody | None = None, db: Session = Depends(get_db)):
    meta = (body.model_dump(exclude_none=True) if body else {})

    stmt = (
        text("""
            INSERT INTO compliance_requests (kind, status, meta, created_at)
            VALUES (:kind, :status, :meta, NOW())
            RETURNING id
        """)
        .bindparams(bindparam("meta", type_=sa.JSON))
    )

    row = db.execute(stmt, {"kind": "pia_pack", "status": "NEW", "meta": meta}).first()
    db.commit()
    cid = int(row[0])

    try:
        if celery_app.conf.task_always_eager:
            pia_pack_generate.apply(args=[cid])
        else:
            pia_pack_generate.delay(cid)
    except OperationalError:
        pia_pack_generate.apply(args=[cid])

    return {"ok": True, "request_id": cid}

# ---------- POST /erasure ----------

@router.post("/erasure", dependencies=[Depends(doc_purpose_of_use), Depends(require_pou({"OPERATIONS"}))],)
def request_erasure(body: ErasureBody, db: Session = Depends(get_db)):
    meta = body.model_dump(exclude_none=True)

    stmt = (
        text("""
            INSERT INTO compliance_requests (kind, status, meta, created_at)
            VALUES (:kind, :status, :meta, NOW())
            RETURNING id
        """)
        .bindparams(bindparam("meta", type_=sa.JSON))
    )

    row = db.execute(stmt, {"kind": "erasure", "status": "NEW", "meta": meta}).first()
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
