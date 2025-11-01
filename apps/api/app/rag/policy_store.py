# apps/api/app/rag/policy_store.py
from __future__ import annotations
import os, logging
from typing import List, Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

def _embed_query(q: str) -> list[float] | None:
    """
    Try to embed the query with OpenAI if OPENAI_API_KEY is present.
    If not available, return None to trigger SQL fallback.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        # Works with openai>=1.x (SDK commonly used in your project)
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        out = client.embeddings.create(model=os.getenv("EMBEDDING_MODEL","text-embedding-3-small"), input=q)
        return out.data[0].embedding
    except Exception as e:
        log.warning("Embedding fallback due to error: %s", e)
        return None


def best_policy_chunks(db: Session, query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Returns top-k policy chunks either by pgvector similarity, or (fallback)
    the latest k rows if vector search isn't available.
    """
    emb = _embed_query(query)
    if emb:
        try:
            rows = db.execute(
                text("""
                    SELECT id, text
                    FROM policy_chunks
                    ORDER BY embedding <#> :q
                    LIMIT :k
                """),
                {"q": emb, "k": k},
            ).mappings().all()
            return [{"id": int(r["id"]), "preview": (r["text"] or "")[:160]} for r in rows]
        except Exception as e:
            log.warning("Vector search failed, using recency fallback: %s", e)

    rows = db.execute(
        text("SELECT id, text FROM policy_chunks ORDER BY id DESC LIMIT :k"),
        {"k": k},
    ).mappings().all()
    return [{"id": int(r["id"]), "preview": (r["text"] or "")[:160]} for r in rows]
