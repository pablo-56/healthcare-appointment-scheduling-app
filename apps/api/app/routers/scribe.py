# apps/api/app/routers/scribe.py
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..middleware.purpose_of_use import require_pou

router = APIRouter(prefix="/v1/scribe", tags=["scribe"])

# --- DDL helper: ensure Phase-6 table exists (idempotent) ---------------------
def _ensure_phase6_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS scribe_sessions (
              id SERIAL PRIMARY KEY,
              appointment_id INTEGER NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
              status TEXT NOT NULL DEFAULT 'DRAFT',          -- DRAFT | APPROVED
              meta JSONB NOT NULL DEFAULT '{}'::jsonb,       -- model info, confidences, etc.
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    db.commit()


# --- Pydantic I/O -------------------------------------------------------------
class StartReq(BaseModel):
    appointment_id: int


class StartResp(BaseModel):
    session_id: int
    draft: str
    status: str = "DRAFT"


class ApproveResp(BaseModel):
    ok: bool
    session_id: int
    status: str = "APPROVED"


# --- Simple draft generator (uses OpenAI if key present, falls back otherwise)
def _make_stub_draft(appt: dict) -> str:
    # Fallback draft that always works
    return (
        f"Subjective: Patient presents for {appt.get('reason','follow-up')}.\n"
        f"Objective: Vitals and exam within expected ranges.\n"
        f"Assessment: {appt.get('reason','Encounter')}.\n"
        f"Plan: Continue current management. Follow-up as scheduled."
    )


def _generate_draft(db: Session, appt_id: int) -> str:
    # Grab a bit of context from the DB (reason, times)
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
        return _make_stub_draft(dict(appt))

    # Best-effort OpenAI call; safely falls back on any error.
    try:
        from openai import OpenAI  # OpenAI Python SDK >=1.0 style
        client = OpenAI(api_key=api_key)

        prompt = (
            "Create a concise SOAP note draft for the following primary-care visit. "
            "Use short bullet-y sentences. Do not include PHI beyond what’s provided.\n\n"
            f"Appointment ID: {appt['id']}\n"
            f"Reason: {appt.get('reason','')}\n"
            f"Start:  {appt.get('start_at')}\n"
            f"End:    {appt.get('end_at')}\n"
        )

        # Use a small model name you already use elsewhere; change if needed.
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a clinical scribe assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=450,
        )
        content = completion.choices[0].message.content or ""
        return content.strip() or _make_stub_draft(dict(appt))
    except Exception:
        return _make_stub_draft(dict(appt))


# --- Routes -------------------------------------------------------------------

@router.post(
    "/sessions",
    response_model=StartResp,
    dependencies=[Depends(require_pou({"TREATMENT"}))],  # Clinician workflow
)
def start_session(body: StartReq, db: Session = Depends(get_db)):
    _ensure_phase6_tables(db)

    # Insert session row
    row = db.execute(
        text(
            """
            INSERT INTO scribe_sessions(appointment_id, status, meta)
            VALUES (:appt, 'DRAFT', '{}'::jsonb)
            RETURNING id
            """
        ),
        {"appt": body.appointment_id},
    ).mappings().first()
    session_id = int(row["id"])

    # Generate initial draft text
    draft = _generate_draft(db, body.appointment_id)

    # Write a DRAFT document row we can show in UI (kind='EncounterNote')
     
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
                  'appointment_id', :appt,
                  'status', 'DRAFT'
                )
              )::json  -- <-- cast JSONB -> JSON to match column type
            )
            """
        ),
        {
            "url": f"inline://scribe/{session_id}.txt",
            "sid": session_id,
            "appt": body.appointment_id,
        },
    )
    db.commit()

    return StartResp(session_id=session_id, draft=draft)


@router.post(
    "/sessions/{session_id}/approve",
    response_model=ApproveResp,
    dependencies=[Depends(require_pou({"TREATMENT"}))],  # keep strict
)
def approve_session(session_id: int, db: Session = Depends(get_db)):
    _ensure_phase6_tables(db)

    sess = db.execute(
        text("SELECT id, appointment_id, status FROM scribe_sessions WHERE id = :sid"),
        {"sid": session_id},
    ).mappings().first()
    if not sess:
        raise HTTPException(status_code=404, detail="Scribe session not found")

    # Mark session approved
    db.execute(
        text("UPDATE scribe_sessions SET status='APPROVED' WHERE id = :sid"),
        {"sid": session_id},
    )

   
    # Flip document status to FINAL (handle JSON column by casting to/from JSONB)
    db.execute(
        text(
            """
            UPDATE documents
            SET meta = (
                COALESCE(meta::jsonb, '{}'::jsonb)
                || jsonb_build_object('status','FINAL')
            )::json
            WHERE kind = 'EncounterNote'
              AND (meta->>'session_id')::int = :sid
            """
        ),
        {"sid": session_id},
    )

    # Inside routers/scribe.py -> approve_session (AFTER you mark the encounter/note final):
    from app.celery_app import celery_app as _cel
    _ = _cel.send_task("documents.render", kwargs={"appointment_id": appt_id, "encounter_id": f"enc-{appt_id}"})


    # Create a coding_review task (OPEN)
    db.execute(
        text(
            """
            INSERT INTO tasks(type, status, payload_json)
            VALUES ('coding_review', 'OPEN', jsonb_build_object('session_id', :sid, 'appointment_id', :appt))
            """
        ),
        {"sid": session_id, "appt": sess["appointment_id"]},
    )

    db.commit()

    # (Optional) Best-effort mock call to EHR connector for DocumentReference (ignored on error)
    try:
        import httpx

        httpx.post(
            "http://ehr-connector:9200/fhir/DocumentReference",
            json={
                "resourceType": "DocumentReference",
                "status": "current",
                "description": f"Encounter note for appointment {sess['appointment_id']} (session {session_id})",
            },
            timeout=2.0,
        )
    except Exception:
        pass

    return ApproveResp(ok=True, session_id=session_id)
