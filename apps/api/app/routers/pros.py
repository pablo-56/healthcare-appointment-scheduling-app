# apps/api/app/routers/pros.py
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Path
from pydantic import BaseModel, validator
from typing import Optional, List
from sqlalchemy import text, bindparam
import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..db import get_db
from ..middleware.purpose_of_use import require_pou  # your existing PoU checker

router = APIRouter(prefix="/v1", tags=["pros"])

# ---------- Models ----------

class ProsSubmit(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    encounter_id: Optional[str] = None
    language: Optional[str] = "en"
    answers: List[int]  # enforce via validator below

    @validator("answers")
    def answers_not_empty(cls, v: List[int]):
        if not v or len(v) < 1:
            raise ValueError("answers must contain at least one item")
        return [int(x) for x in v]

# ---------- Utilities ----------

def score_phq9(answers: List[int]) -> int:
    # Sum of first 9 items (0..3 each)
    return sum(int(x) for x in answers[:9])

def instrument_score(instrument: str, answers: List[int]) -> int:
    ins = instrument.lower()
    if ins in {"phq9", "phq-9", "phq_9"}:
        return score_phq9(answers)
    # default: sum
    return sum(int(x) for x in answers)

# ---------- Endpoints ----------

@router.get("/pros/{instrument}")
def get_instrument_results(
    instrument: str = Path(..., description="e.g., phq9"),
    patient_id: Optional[int] = Query(None),
    x_purpose_of_use: Optional[str] = Header(None, alias="X-Purpose-Of-Use"),
    db: Session = Depends(get_db),
):
    require_pou(x_purpose_of_use)

    sql = text("""
        SELECT id, patient_id, appointment_id, instrument, score,
               answers, encounter_id, language, created_at
        FROM patient_surveys
        WHERE instrument = :ins
          AND (:pid IS NULL OR patient_id = :pid)
        ORDER BY id DESC
        LIMIT 50
    """)
    rows = db.execute(sql, {"ins": instrument.lower(), "pid": patient_id}).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.post("/pros/{instrument}")
def submit_instrument(
    instrument: str,
    body: ProsSubmit,
    x_purpose_of_use: Optional[str] = Header(None, alias="X-Purpose-Of-Use"),
    db: Session = Depends(get_db),
):
    require_pou(x_purpose_of_use)

    ins = instrument.lower()
    score = instrument_score(ins, body.answers)

    # Insert survey result (bind answers as JSON)
    insert_sql = text("""
        INSERT INTO patient_surveys
            (patient_id, appointment_id, instrument, score,
             answers, encounter_id, language, created_at)
        VALUES
            (:pid, :appt, :ins, :score,
             :answers, :enc, :lang, NOW())
        RETURNING id, patient_id, appointment_id, instrument, score,
                  answers, encounter_id, language, created_at
    """).bindparams(
        bindparam("answers", type_=sa.JSON())
    )

    row = db.execute(
        insert_sql,
        {
            "pid": body.patient_id,
            "appt": body.appointment_id,
            "ins": ins,
            "score": score,
            "answers": body.answers,
            "enc": body.encounter_id,
            "lang": body.language or "en",
        },
    ).mappings().first()
    db.commit()

    result = dict(row)

    # Escalation rule: PHQ-9 >= 15 → create care_escalation task
    if ins.startswith("phq") and score >= 15:
        payload = {
            "reason": "high_phq9_score",
            "instrument": ins,
            "score": score,
            "encounter_id": body.encounter_id,
            "survey_id": result["id"],
        }
        task_sql = text("""
            INSERT INTO tasks(type, status, assignee, payload_json, created_at)
            VALUES ('care_escalation', 'open', 'nurse_queue', :payload, NOW())
            RETURNING id
        """).bindparams(
            bindparam("payload", type_=sa.JSON())
        )
        tid = db.execute(task_sql, {"pid": body.patient_id, "payload": payload}).scalar_one()
        db.commit()
        result["escalation_task_id"] = tid

    return result
