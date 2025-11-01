# app/tasks/events.py
from __future__ import annotations

from app.celery_app import celery_app


@celery_app.task(name="events.emit", bind=True)
def emit(self, doc_id: int, topic: str | None = None, payload: dict | None = None) -> dict:
    # TODO: your actual event emission logic here
    # keep indentation as 4 spaces everywhere
    return {"status": "ok", "document_id": doc_id, "topic": topic}
