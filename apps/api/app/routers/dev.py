# apps/api/app/routers/dev.py
from fastapi import APIRouter, Response, Request, Query
from typing import Optional
from urllib.parse import quote

router = APIRouter(prefix="/v1/dev", tags=["dev"])

# simple mapping so one param sets both email and role
PERSONAS = {
    "patient":   ("patient1@example.com",   "PATIENT"),
    "clinician": ("clinician1@example.com", "CLINICIAN"),
    "ops":       ("ops1@example.com",       "OPS"),
}

@router.get("/session")
def dev_session(
    response: Response,
    request: Request,
    email: Optional[str] = Query(None),
    role: Optional[str] = Query(None, description="PATIENT|CLINICIAN|OPS"),
    persona: Optional[str] = Query(None, description="patient|clinician|ops"),
    redirect: Optional[str] = Query(None),
):
    """
    DEV-ONLY: Sets a cookie-based session usable by the web UI.
    Works across localhost ports; cookie stays on API origin and is sent on
    every frontend fetch to the API (as long as fetch uses credentials: 'include').
    """
    if persona and persona.lower() in PERSONAS:
        email, role = PERSONAS[persona.lower()]

    email = email or "patient1@example.com"
    role  = (role or "PATIENT").upper()

    # Set small, host-only cookies on API origin
    response.set_cookie("demo_email", email, path="/", samesite="lax")
    response.set_cookie("demo_role", role,  path="/", samesite="lax")

    # Small body so opening this URL directly is also informative
    body = f"DEV session set for {email} ({role})."
    if redirect:
        # FastAPI Response has no redirect helper on bare Response, just send 307
        response.status_code = 307
        response.headers["Location"] = redirect
        body += f" Redirecting to {redirect}"
    return body

@router.get("/logout")
def dev_logout(response: Response, redirect: Optional[str] = None):
    response.delete_cookie("demo_email", path="/")
    response.delete_cookie("demo_role", path="/")
    if redirect:
        response.status_code = 307
        response.headers["Location"] = redirect
        return "Logged out"
    return "Logged out"
