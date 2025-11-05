# app/tasks/events.py
from __future__ import annotations

import json
import logging
import time
import uuid

from app.celery_app import celery_app
from app.utils.redis_cache import get_redis_client

logger = logging.getLogger(__name__)


@celery_app.task(name="events.emit", bind=True)
def emit(self, doc_id: int, topic: str | None = None, payload: dict | None = None) -> dict:
    topic = topic or "documents.generic"
    payload = payload if isinstance(payload, dict) else {}

    event = {
        "id": uuid.uuid4().hex,
        "doc_id": doc_id,
        "topic": topic,
        "payload": payload,
        "emitted_at_ms": time.time_ns() // 1_000_000,
        "task_id": getattr(getattr(self, "request", None), "id", None),
    }

    message = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
    channel = f"events:{topic}"
    published = 0

    try:
        client = get_redis_client()
        publish_fn = getattr(client, "publish", None)
        if callable(publish_fn):
            published = int(publish_fn(channel, message) or 0)
        else:
            buffer = getattr(client, "_event_buffer", None)
            if buffer is None:
                buffer = []
                setattr(client, "_event_buffer", buffer)
            buffer.append((channel, event))
            published = 1
    except Exception as exc:  # pragma: no cover - guardrail for runtime issues
        logger.exception("Failed to emit event for doc %s on %s: %s", doc_id, topic, exc)
        return {"status": "error", "document_id": doc_id, "topic": topic}

    return {
        "status": "ok",
        "document_id": doc_id,
        "topic": topic,
        "event_id": event["id"],
        "delivered": bool(published),
    }
