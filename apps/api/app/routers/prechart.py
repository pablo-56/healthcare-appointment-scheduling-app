# apps/api/app/routers/prechart.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import get_db
from app.middleware.purpose_of_use import require_pou

router = APIRouter(prefix="/v1/prechart", tags=["prechart"])

@router.get(
    "/{appointment_id}",
    dependencies=[Depends(require_pou({"TREATMENT","OPERATIONS"}))],
)
def get_prechart(appointment_id: int, db: Session = Depends(get_db)):
    """
    Return the latest Prechart document for this appointment or 404 (UI shows 'generating…').
    """
    row = db.execute(
        text("""
          SELECT id, url, meta, created_at
          FROM documents
          WHERE kind='Prechart'
            AND COALESCE((meta->>'appointment_id')::int, 0) = :aid
          ORDER BY id DESC
          LIMIT 1
        """),
        {"aid": appointment_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Prechart not found")
    return dict(row)
