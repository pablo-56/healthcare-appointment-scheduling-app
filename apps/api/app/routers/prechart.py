# apps/api/app/routers/prechart.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

# use your existing helpers/middleware
from app.db import get_db
from app.middleware.purpose_of_use import require_pou

# Route base: /v1/prechart/...
router = APIRouter(prefix="/v1/prechart", tags=["prechart"])

@router.get(
    "/{appointment_id}",
    # Reject requests missing X-Purpose-Of-Use or with an unsupported value
    dependencies=[Depends(require_pou({"TREATMENT", "OPERATIONS"}))],
)
def get_prechart(appointment_id: int, db: Session = Depends(get_db)):
    """
    Return the latest Prechart document row for this appointment_id.

    documents.meta is JSON (not JSONB), so we extract the stored appointment_id
    with ->> and cast to int.
    """
    row = db.execute(
        text(
            """
            SELECT id, url, meta, created_at
            FROM documents
            WHERE kind = 'Prechart'
              AND COALESCE((meta->>'appointment_id')::int, 0) = :aid
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"aid": appointment_id},
    ).mappings().first()

    if not row:
        # Keep the error body consistent with your other endpoints
        raise HTTPException(status_code=404, detail="Prechart not found")

    # Shape the JSON exactly as your web page expects
    return {
        "id": row["id"],
        "url": row["url"],
        "meta": row["meta"],
        "created_at": row["created_at"],
    }
