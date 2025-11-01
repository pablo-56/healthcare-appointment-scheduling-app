# apps/api/app/tasks/compliance.py
"""
Celery tasks for Phase 10 (Compliance).
Matches repo DB patterns:
- Uses SessionLocal from app.db (no get_engine / get_db_session).
- Wraps each task with an explicit session lifecycle (commit/rollback/close).
- Stores small PDF/JSON artifacts via put_pdf_and_sha (same helper used by documents router).
- Updates compliance_requests.meta (JSON) safely via jsonb_set.
"""

from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO
from typing import Any, Dict, Optional

from celery import shared_task
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from sqlalchemy import text, bindparam
import sqlalchemy as sa

from app.db import SessionLocal  # <- matches your repo
from app.storage import put_pdf_and_sha  # same helper used elsewhere
# If you don't have storage wired yet, you can stub put_pdf_and_sha to return ("memory://pia.pdf", "sha")


# ----------------------------
# Session helper (repo-consistent)
# ----------------------------
@contextmanager
def session_scope():
    """Create/commit/rollback/close a SessionLocal() for Celery tasks."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ----------------------------
# Small PDF builder for PIA pack
# ----------------------------
def _build_simple_pdf(title: str, lines: Dict[str, Any]) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    w, h = LETTER

    y = h - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, title)
    y -= 24
    c.setFont("Helvetica", 10)

    for k, v in lines.items():
        txt = f"{k}: {str(v)[:160]}"
        c.drawString(50, y, txt)
        y -= 14
        if y < 50:
            c.showPage()
            y = h - 50
            c.setFont("Helvetica", 10)

    c.showPage()
    c.save()
    return buf.getvalue()


# ----------------------------
# Utilities to update request row
# ----------------------------
def _set_request_status(db, req_id: int, status: str, extra_meta: Optional[Dict[str, Any]] = None):
    """
    Update compliance_requests.status and merge keys into meta JSON.
    Assumes table: compliance_requests(id, kind, status, meta JSON, created_at, updated_at?)
    """
    # Build JSONB merge: meta := meta || :extra_meta::jsonb (if extra provided)
    if extra_meta:
        db.execute(
            text(
                """
                UPDATE compliance_requests
                SET status = :status,
                    meta   = COALESCE(meta::jsonb, '{}'::jsonb) || :extra::jsonb
                WHERE id = :id
                """
            ).bindparams(bindparam("extra", type_=sa.JSON)),
            {"status": status, "extra": extra_meta, "id": req_id},
        )
    else:
        db.execute(
            text("UPDATE compliance_requests SET status = :status WHERE id = :id"),
            {"status": status, "id": req_id},
        )


def _get_request(db, req_id: int) -> Optional[Dict[str, Any]]:
    row = db.execute(
        text("SELECT id, kind, status, meta FROM compliance_requests WHERE id = :id"),
        {"id": req_id},
    ).mappings().first()
    return dict(row) if row else None


# ----------------------------
# Tasks
# ----------------------------

@shared_task(name="compliance.pia_pack_generate")
def pia_pack_generate(request_id: int) -> Dict[str, Any]:
    """
    Generate a lightweight PIA/IMA PDF artifact and attach URL into meta.result_url.
    """
    with session_scope() as db:
        req = _get_request(db, request_id)
        if not req:
            return {"ok": False, "error": "request_not_found", "request_id": request_id}

        meta = req.get("meta") or {}
        summary = {
            "Request ID": request_id,
            "Kind": req.get("kind"),
            "Status(before)": req.get("status"),
            "Data flows": meta.get("data_flows", "N/A"),
            "Subprocessors": meta.get("subprocessors", "N/A"),
            "Retention": meta.get("retention", "N/A"),
        }
        pdf = _build_simple_pdf("PIA/IMA Pack", summary)

        # Store artifact (S3/minio/etc.)
        key = f"compliance/pia/{request_id}.pdf"
        url, sha = put_pdf_and_sha(key, pdf)

        _set_request_status(
            db,
            request_id,
            status="DONE",
            extra_meta={"result_url": url, "artifact_sha256": sha},
        )
        return {"ok": True, "request_id": request_id, "url": url}


@shared_task(name="compliance.export_request")
def export_request(request_id: int) -> Dict[str, Any]:
    """
    Assemble export package (simple JSON stub here) and mark DONE with result_url.
    """
    with session_scope() as db:
        req = _get_request(db, request_id)
        if not req:
            return {"ok": False, "error": "request_not_found", "request_id": request_id}

        meta = req.get("meta") or {}
        export_note = {
            "request_id": request_id,
            "scope": meta.get("scope", "patient_all_data"),
            "redactions": meta.get("redactions", ["secrets", "internal_keys"]),
        }

        pdf = _build_simple_pdf("Compliance Export Summary", export_note)
        key = f"compliance/export/{request_id}.pdf"
        url, sha = put_pdf_and_sha(key, pdf)

        _set_request_status(
            db, request_id, status="DONE", extra_meta={"result_url": url, "artifact_sha256": sha}
        )
        return {"ok": True, "request_id": request_id, "url": url}


@shared_task(name="compliance.erasure_request")
def erasure_request(request_id: int) -> Dict[str, Any]:
    """
    Perform redaction/erasure according to policy (this is a stub that just flips status).
    In a real flow, you would:
      - mark legal hold checks
      - delete/soft-delete eligible rows
      - emit audit log entries
    """
    with session_scope() as db:
        req = _get_request(db, request_id)
        if not req:
            return {"ok": False, "error": "request_not_found", "request_id": request_id}

        # TODO: implement actual erasure logic on your tables per policy
        _set_request_status(db, request_id, status="DONE", extra_meta={"erased": True})
        return {"ok": True, "request_id": request_id}


@shared_task(name="compliance.anomaly_scan")
def anomaly_scan() -> Dict[str, Any]:
    """
    Simple heuristic scan over audit_logs to look for unusually high daily access.
    Matches typical schema where audit_logs has at least: id, actor, action, created_at.
    If your column names differ, adjust the SQL accordingly.
    """
    with session_scope() as db:
        # Count by actor for the last 1 day vs last 7 days.
        # Uses created_at (since your repo doesn't have a 'ts' column).
        recent = db.execute(
            text(
                """
                SELECT actor, COUNT(*) AS c
                FROM audit_logs
                WHERE created_at >= NOW() - INTERVAL '1 day'
                GROUP BY actor
                """
            )
        ).mappings().all()

        week = db.execute(
            text(
                """
                SELECT actor, COUNT(*) AS c
                FROM audit_logs
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY actor
                """
            )
        ).mappings().all()

        week_map = {r["actor"]: r["c"] for r in week}
        flagged = []
        for r in recent:
            a, day_c = r["actor"], r["c"]
            wk_c = max(week_map.get(a, 0), 1)
            if day_c >= 3 * (wk_c / 7.0) + 10:  # simple spike threshold
                flagged.append({"actor": a, "day": int(day_c), "week": int(wk_c)})

        # Optionally persist summary into a compliance_request or an ops task:
        # (Skipping DB writes here to keep this task schema-agnostic.)
        return {"ok": True, "flagged": flagged}
