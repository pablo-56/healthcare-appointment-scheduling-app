# apps/api/app/routers/rbac.py
from __future__ import annotations

from typing import Optional, Literal, Dict, Any
from fastapi import APIRouter, Depends, Request, Response, HTTPException, Query, Body
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(prefix="/v1", tags=["rbac", "auth"])

# -- Roles we support
Role = Literal["PATIENT", "CLINICIAN", "OPS"]

# -- Ensure "users" table has a role column (idempotent, safe in dev)
def _ensure_users_role(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
          id SERIAL PRIMARY KEY,
          email TEXT UNIQUE NOT NULL,
          phone TEXT NULL,
          password_hash TEXT NULL,
          role TEXT NOT NULL DEFAULT 'PATIENT',
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'PATIENT'"))
    db.commit()

# -- Seed 3 personas (safe to re-run)
@router.post("/admin/seed/personas")
def seed_personas(db: Session = Depends(get_db)):
    _ensure_users_role(db)
    for email, role in [
        ("patient1@example.com",   "PATIENT"),
        ("clinician1@example.com", "CLINICIAN"),
        ("ops1@example.com",       "OPS"),
    ]:
        db.execute(
            text("""
                INSERT INTO users(email, role) VALUES (:e, :r)
                ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role
            """),
            {"e": email, "r": role},
        )
    db.commit()
    return {"ok": True, "seeded": 3}

# --- Helper: resolve the current user (DEV-friendly)
def _current_user(request: Request, db: Session) -> Dict[str, Any] | None:
    """
    DEV strategy:
      1) If cookie 'demo_email' is set, use it.
      2) Else try 'Authorization: Bearer <email>' (very dev).
      3) Else anonymous.
    In real prod, you likely have a session/JWT to parse; hook it here.
    """
    email: Optional[str] = None

    # (1) cookie from /v1/dev/session
    if "demo_email" in request.cookies:
        email = request.cookies.get("demo_email")

    # (2) super-simple dev bearer (optional)
    if not email:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            email = auth.split(" ", 1)[1].strip()

    if not email:
        return None

    row = db.execute(
        text("SELECT id, email, role FROM users WHERE email=:e"),
        {"e": email},
    ).mappings().first()
    return dict(row) if row else None

# --- Who am I? -> used by the frontend guard
@router.get("/auth/me")
def auth_me(request: Request, db: Session = Depends(get_db)):
    _ensure_users_role(db)
    u = _current_user(request, db)
    if not u:
        return {"role": "ANON"}
    return {"id": u["id"], "email": u["email"], "role": u["role"]}

# --- DEV ONLY: set a cookie to impersonate a seeded user
@router.post("/dev/session")
def dev_session(
    response: Response,
    email: str = Query(..., description="Use a seeded email, e.g. patient1@example.com"),
    db: Session = Depends(get_db),
):
    _ensure_users_role(db)
    row = db.execute(text("SELECT id, role FROM users WHERE email=:e"), {"e": email}).mappings().first()
    if not row:
        raise HTTPException(404, "User not found; seed via POST /v1/admin/seed/personas")
    # simple signed-less cookie for DEV only
    response.set_cookie(key="demo_email", value=email, httponly=False, samesite="Lax", path="/")
    return {"ok": True, "email": email, "role": row["role"]}
