import logging
from sqlalchemy import text, bindparam
import sqlalchemy as sa

logger = logging.getLogger("api")

def _col_exists(db, table: str, col: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": col},
    ).first()
    return bool(row)

def audit_safe(db, action: str, actor: str, target: str | None = None, meta: dict | None = None):
    """
    Best-effort audit insert that adapts to actual schema.
    - If `details` (json) exists -> insert dict via JSON bindparam.
    - elif `meta_json` exists -> insert dict via JSON bindparam (or text if column is text).
    - else -> insert without extra details.
    Never raises.
    """
    meta = meta or {}

    try:
        has_details = _col_exists(db, "audit_logs", "details")
        has_meta    = _col_exists(db, "audit_logs", "meta_json")

        if has_details:
            stmt = (
                text(
                    "INSERT INTO audit_logs (action, actor, target, details, created_at) "
                    "VALUES (:a, :r, :t, :details, NOW())"
                )
                .bindparams(bindparam("details", type_=sa.JSON()))
            )
            db.execute(stmt, {"a": action, "r": actor, "t": target, "details": meta})
            db.commit()
            return

        if has_meta:
            # Try JSON first; if the column is TEXT, Postgres will still accept a string.
            try:
                stmt = (
                    text(
                        "INSERT INTO audit_logs (action, actor, target, meta_json, created_at) "
                        "VALUES (:a, :r, :t, :meta, NOW())"
                    )
                    .bindparams(bindparam("meta", type_=sa.JSON()))
                )
                db.execute(stmt, {"a": action, "r": actor, "t": target, "meta": meta})
            except Exception:
                # fallback: stringify
                stmt = text(
                    "INSERT INTO audit_logs (action, actor, target, meta_json, created_at) "
                    "VALUES (:a, :r, :t, :meta, NOW())"
                )
                db.execute(stmt, {"a": action, "r": actor, "t": target, "meta": json.dumps(meta)})
            db.commit()
            return

        # No details/meta_json column — write minimal record
        db.execute(
            text(
                "INSERT INTO audit_logs (action, actor, target, created_at) "
                "VALUES (:a, :r, :t, NOW())"
            ),
            {"a": action, "r": actor, "t": target},
        )
        db.commit()

    except Exception as e:
        db.rollback()
        logger.warning("audit insert failed (non-fatal): %s", e)
