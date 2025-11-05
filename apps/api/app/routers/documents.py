# apps/api/app/routers/documents.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from sqlalchemy import text
from sqlalchemy.orm import Session
import base64
from datetime import datetime, timedelta

from ..db import get_db
from ..settings import settings

# PyJWT is required
try:
    import jwt  # PyJWT
except Exception as _e:  # pragma: no cover
    raise HTTPException(
        status_code=500,
        detail="PyJWT not installed. Add 'PyJWT==2.8.0' to requirements.txt and rebuild the API image.",
    )

router = APIRouter(prefix="/v1", tags=["documents"])

# ---------------------------
# Pydantic models (Phase 7)
# ---------------------------

class RenderDocReq(BaseModel):
    # Discharge-focused payload
    kind: Literal["Discharge"]
    appointment_id: int
    encounter_id: str
    language: Literal["en", "fr"] = "en"
    # Optional customizations; safe defaults used if omitted
    body: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None


# ---------------------------
# Helpers
# ---------------------------

def _require_pou(request: Request, x_purpose_of_use: Optional[str]) -> str:
    """
    Accept a single X-Purpose-Of-Use header; be tolerant to casing/underscore differences
    some proxies introduce. Valid: TREATMENT | OPERATIONS
    """
    pou = x_purpose_of_use or request.headers.get("x-purpose-of-use") or request.headers.get("X-Purpose-Of-Use")
    if not pou or pou.upper() not in {"TREATMENT", "OPERATIONS"}:
        raise HTTPException(403, detail="Missing/invalid X-Purpose-Of-Use")
    return pou.upper()


def _html_from_payload(title: str, data: Dict[str, Any]) -> str:
    """Very simple patient-friendly HTML renderer."""
    meds = data.get("meds", [])
    when_to_call = data.get("when_to_call", ["If symptoms worsen, go to ER.", "If you develop new symptoms, call the clinic."])
    follow_up = data.get("follow_up", "Use the follow-up link to book a visit.")
    summary = data.get("summary", "We discussed your condition and next steps today.")
    enc = data.get("encounter_id", "")

    def li(items):
        return "".join(f"<li>{str(i)}</li>" for i in items) or "<li>—</li>"

    return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family:system-ui,Segoe UI,Arial,sans-serif;line-height:1.5;padding:18px">
  <h1 style="margin:0 0 8px">{title}</h1>
  <p>{summary}</p>

  <h3>Medication schedule</h3>
  <ul>{li(meds)}</ul>

  <h3>When to call</h3>
  <ul>{li(when_to_call)}</ul>

  <h3>Next steps</h3>
  <p>{follow_up}</p>

  <hr>
  <small>Encounter: {enc}</small>
</body>
</html>"""


def _data_url(html: str) -> str:
    return "data:text/html;base64," + base64.b64encode(html.encode("utf-8")).decode("ascii")


# ---------------------------
# List / Get (unchanged, handy for debugging)
# ---------------------------

# apps/api/app/routers/documents.py  (replace the list endpoint only)

@router.get("/documents")
def list_documents(
    appointment_id: Optional[int] = Query(default=None),
    limit: int = Query(default=20),
    db: Session = Depends(get_db),
):
    """
    If appointment_id is provided, return docs whose meta.appointment_id == :appointment_id.
    Otherwise return the latest N documents.
    """
    if appointment_id:
        rows = db.execute(
            text(
                "SELECT id, patient_id, kind, url, meta, created_at "
                "FROM documents WHERE (meta->>'appointment_id') = :aid "
                "ORDER BY id DESC LIMIT :n"
            ),
            {"aid": str(appointment_id), "n": limit},
        ).mappings().all()
    else:
        rows = db.execute(
            text(
                "SELECT id, patient_id, kind, url, meta, created_at "
                "FROM documents ORDER BY id DESC LIMIT :n"
            ),
            {"n": limit},
        ).mappings().all()
    return {"documents": [dict(r) for r in rows]}

# ---------------------------
# Phase 7: Render Discharge
# ---------------------------

@router.post("/documents/render")
def render_document(
    body: RenderDocReq,
    request: Request,
    db: Session = Depends(get_db),
    x_purpose_of_use: Optional[str] = Header(default=None, alias="X-Purpose-Of-Use", convert_underscores=False),
):
    """
    Renders a patient-friendly Discharge summary as data:URL HTML and stores a row in documents(kind='Discharge').
    Returns {id, token, encounter_id, url, portal_path}.
    """
    _require_pou(request, x_purpose_of_use)

    # 1) Resolve patient from appointment (if possible)
    pid: Optional[int] = None
    appt = db.execute(
        text("SELECT patient_id FROM appointments WHERE id=:id"),
        {"id": body.appointment_id},
    ).mappings().first()
    if appt and appt["patient_id"] is not None:
        # verify patient exists to avoid FK error; else keep NULL
        p = db.execute(
            text("SELECT 1 FROM patients WHERE id=:pid"),
            {"pid": appt["patient_id"]},
        ).first()
        if p:
            pid = int(appt["patient_id"])

    # 2) Build friendly HTML
    title = (body.body or {}).get("title") or "Your Discharge Summary"
    payload_data = body.data or {
        "summary": "We discussed your condition and the plan.",
        "meds": [],
        "when_to_call": ["If symptoms worsen, go to ER.", "If you develop new symptoms, call the clinic."],
        "follow_up": "Use the follow-up link to book.",
        "encounter_id": body.encounter_id,
    }
    html = _html_from_payload(title, payload_data)
    url = _data_url(html)

    # 3) Insert document; meta is JSON (not JSONB), so build via jsonb_build_object then cast ::json
    doc_id = db.execute(
        text(
            """
            INSERT INTO documents (patient_id, kind, url, meta, created_at)
            VALUES (
              :pid,
              'Discharge',
              :url,
              (
                jsonb_build_object(
                  'appointment_id', :aid,
                  'encounter_id', :enc,
                  'lang', :lang,
                  'title', :title,
                  'expires_at', NOW() + interval '7 days'
                )
              )::json,
              NOW()
            )
            RETURNING id
            """
        ),
        {
            "pid": pid,  # may be NULL, which avoids FK violations
            "url": url,
            "aid": body.appointment_id,
            "enc": body.encounter_id,
            "lang": body.language,
            "title": title,
        },
    ).scalar_one()
    db.commit()

    # 4) Mint a portal token that encodes encounter + doc and expires in 7 days
    token = jwt.encode(
        {
            "iss": "health-app",
            "enc": body.encounter_id,
            "doc": doc_id,
            "exp": datetime.utcnow() + timedelta(days=7),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    # Convenience field to avoid mixing up tokens
    portal_path = f"/v1/documents/discharge/{body.encounter_id}?token={token}"

    return {
        "id": doc_id,
        "token": token,
        "encounter_id": body.encounter_id,
        "url": url,
        "portal_path": portal_path,
    }


# ---------------------------
# Phase 7: Portal-safe fetch
# ---------------------------

@router.get("/documents/discharge/{encounter_id}")
def get_discharge_for_portal(
    encounter_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Portal-safe fetch: latest Discharge for this encounter IF the token is valid
    and enc claim matches the path param.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("enc") != encounter_id:
            raise HTTPException(403, detail="Token mismatch")
    except jwt.ExpiredSignatureError:
        raise HTTPException(404, detail="Discharge not found or token expired")
    except Exception:
        raise HTTPException(403, detail="Invalid token")

    row = db.execute(
        text(
            """
            SELECT id, kind, url, meta, created_at
            FROM documents
            WHERE kind='Discharge' AND (meta->>'encounter_id') = :enc
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"enc": encounter_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, detail="Discharge not found")

    return {
        "id": row["id"],
        "kind": row["kind"],
        "url": row["url"],
        "meta": row["meta"],
        "created_at": row["created_at"],
    }


def _render_simple_pdf(title: str, data: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    w, h = LETTER
    y = h - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, title)
    y -= 30
    c.setFont("Helvetica", 10)
    for k, v in data.items():
        c.drawString(50, y, f"{k}: {json.dumps(v)[:100]}")
        y -= 14
        if y < 50:
            c.showPage()
            y = h - 50
            c.setFont("Helvetica", 10)
    c.showPage()
    c.save()
    return buf.getvalue()