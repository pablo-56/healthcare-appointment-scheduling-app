# app/utils/audit.py
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

def audit_safe(db, actor: str, action: str, target: str, details: dict | None):
    details = details or {}
    stmt = text("""
        INSERT INTO audit_logs (actor, action, target, details)
        VALUES (:actor, :action, :target, :details)
    """).bindparams(bindparam("details", type_=JSONB))

    db.execute(stmt, {"actor": actor, "action": action, "target": target, "details": details})
    db.commit()
