# apps/api/app/routers/scribe.py
from __future__ import annotations

import os
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..middleware.purpose_of_use import require_pou

router = APIRouter(prefix="/v1/scribe", tags=["scribe"])

EHR_BASE = os.getenv("EHR_CONNECTOR_URL", "http://ehr-connector:8100")

# -----------------------------------------------------------------------------
# DDL helper (idempotent) – keeps demo simple without a migration
# -----------------------------------------------------------------------------
def _ensure_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS scribe_sessions (
              id SERIAL PRIMARY KEY,
              appointment_id INTEGER NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
              status TEXT NOT NULL DEFAULT 'DRAFT',      -- DRAFT | APPROVED
              meta   JSONB NOT NULL DEFAULT '{}'::jsonb, -- model, confidences, etc.
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    db.commit()


# -----------------------------------------------------------------------------
# I/O models
# -----------------------------------------------------------------------------
class StartReq(BaseModel):
    appointment_id: int


class StartResp(BaseModel):
    session_id: int
    draft: str
    status: str = "DRAFT"  # UI shows this in the scribe page header


class ApproveResp(BaseModel):
    ok: bool
    session_id: int
    status: str = "APPROVED"
    encounter_id: str  # lets UI deep-link to /portal/summary/:encounterId


# -----------------------------------------------------------------------------
# Draft generation – use OpenAI if configured; otherwise a safe stub
# -----------------------------------------------------------------------------
def _stub_draft(appt: Dict[str, Any]) -> str:
    return (
        f"Subjective: Patient presents for {appt.get('reason','visit')}.\n"
        f"Objective: Vitals and exam within expected ranges.\n"
        f"Assessment: {appt.get('reason','Encounter')}.\n"
        f"Plan: Continue current management. Follow-up as scheduled."
    )


def _generate_draft(db: Session, appt_id: int) -> str:
    appt = db.execute(
        text(
            """
            SELECT id, reason, start_at, end_at, fhir_appointment_id
            FROM appointments
            WHERE id = :id
            """
        ),
        {"id": appt_id},
    ).mappings().first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _stub_draft(dict(appt))

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        prompt = (
            "Create a concise SOAP note draft for a primary-care visit. "
            "Use short bullet-like sentences. Do not invent PHI.\n\n"
            f"Appointment ID: {appt['id']}\n"
            f"Reason: {appt.get('reason','')}\n"
            f"Start:  {appt.get('start_at')}\n"
            f"End:    {appt.get('end_at')}\n"
        )

        out = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a clinical scribe assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=450,
        )
        text_out = (out.choices[0].message.content or "").strip()
        return text_out or _stub_draft(dict(appt))
    except Exception:
        # Any upstream failure must not block the workflow – UI keeps manual note enabled
        return _stub_draft(dict(appt))


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post(
    "/sessions",
    response_model=StartResp,
    # Clinician workflow requires TREATMENT PoU
    dependencies=[Depends(require_pou({"TREATMENT"}))],
)
def start_session(body: StartReq, db: Session = Depends(get_db)):
    """
    Start a scribe session for an appointment.
    - Creates scribe_sessions row.
    - Generates an initial draft (OpenAI if configured; otherwise stub).
    - Inserts a DRAFT 'EncounterNote' document (documents.meta is JSON, not JSONB).
    """
    _ensure_tables(db)

    # Create a session row
    row = db.execute(
        text(
            "INSERT INTO scribe_sessions(appointment_id, status, meta) "
            "VALUES (:aid, 'DRAFT', '{}'::jsonb) RETURNING id"
        ),
        {"aid": body.appointment_id},
    ).mappings().first()
    session_id = int(row["id"])

    # Produce initial draft (non-blocking, always returns text)
    draft = _generate_draft(db, body.appointment_id)

    # Write a DRAFT EncounterNote document; meta column is JSON → build via JSONB then cast ::json
    db.execute(
        text(
            """
            INSERT INTO documents(kind, url, meta)
            VALUES (
              'EncounterNote',
              :url,
              (
                jsonb_build_object(
                  'session_id', :sid,
                  'appointment_id', :aid,
                  'status', 'DRAFT'
                )
              )::json
            )
            """
        ),
        {"url": f"inline://scribe/{session_id}.txt", "sid": session_id, "aid": body.appointment_id},
    )
    db.commit()

    return StartResp(session_id=session_id, draft=draft)


class ApproveBody(BaseModel):
    # UI sends back the final free-text note; we keep it in meta preview
    draft: Optional[str] = None


@router.post(
    "/sessions/{session_id}/approve",
    response_model=ApproveResp,
    dependencies=[Depends(require_pou({"TREATMENT"}))],
)
def approve_session(
    session_id: int,
    db: Session = Depends(get_db),
    body: ApproveBody = Body(default=ApproveBody()),
):
    """
    Approve a scribe session:
    - Flip scribe_sessions.status → APPROVED.
    - Flip EncounterNote document meta.status → FINAL (+ preview of final draft).
    - Create back-office coding task (status='open').
    - Best-effort: notify EHR connector with a DocumentReference.
    - Best-effort: kick a renderer (Celery) to produce patient-facing summary.
    - Return an encounter_id that the UI can use to deep-link to /portal/summary/:encId
    """
    _ensure_tables(db)

    sess = db.execute(
        text("SELECT id, appointment_id, status FROM scribe_sessions WHERE id = :sid"),
        {"sid": session_id},
    ).mappings().first()
    if not sess:
        raise HTTPException(status_code=404, detail="Scribe session not found")

    appt_id = int(sess["appointment_id"])
    encounter_id = f"enc-{appt_id}"

    # 1) Session → APPROVED
    db.execute(
        text("UPDATE scribe_sessions SET status='APPROVED' WHERE id=:sid"),
        {"sid": session_id},
    )

    # 2) Document 'EncounterNote' → FINAL (documents.meta is JSON; cast JSONB->JSON)
    db.execute(
        text(
            """
            UPDATE documents
            SET meta = (
                COALESCE(meta::jsonb, '{}'::jsonb)
                || jsonb_build_object(
                     'status','FINAL',
                     'encounter_id', :enc,
                     'final_preview', :preview
                   )
            )::json
            WHERE kind='EncounterNote'
              AND (meta->>'session_id')::int = :sid
            """
        ),
        {"sid": session_id, "enc": encounter_id, "preview": (body.draft or "")[:4000]},
    )

    # 3) Create coding task for back-office queue (your tasks table uses lowercase statuses)
    db.execute(
        text(
            """
            INSERT INTO tasks(type, status, payload_json)
            VALUES ('coding_review', 'open', jsonb_build_object('session_id', :sid, 'appointment_id', :aid))
            """
        ),
        {"sid": session_id, "aid": appt_id},
    )

    db.commit()

    # 4) Best-effort: push a DocumentReference to the EHR connector (non-fatal)
    try:
        import httpx

        payload = {
            "resourceType": "DocumentReference",
            "status": "current",
            "description": f"Encounter note for appointment {appt_id} (session {session_id})",
            # In a real system you'd include content/attachments here
        }
        with httpx.Client(timeout=3.0) as client:
            client.post(f"{EHR_BASE}/fhir/DocumentReference", json=payload)
    except Exception:
        pass  # ignore – workflow must continue

    # 5) Best-effort: kick an async renderer (if Celery is present in your app)
    try:
        from app.celery_app import celery_app as _cel
        _cel.send_task(
            "documents.render",
            kwargs={"appointment_id": appt_id, "encounter_id": encounter_id},
        )
    except Exception:
        pass  # safe no-op in dev

    return ApproveResp(ok=True, session_id=session_id, status="APPROVED", encounter_id=encounter_id)
