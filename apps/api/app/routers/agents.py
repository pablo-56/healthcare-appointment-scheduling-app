# apps/api/app/routers/agents.py
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy import text
from app.db import get_db
import httpx
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/v1/agents", tags=["agents"])

def infer_intent(message: str) -> str:
    m = (message or "").lower()
    if any(k in m for k in ["book", "schedule", "reschedule", "cancel", "appointment"]):
        return "SCHEDULING"
    if any(k in m for k in ["intake", "consent", "form", "questionnaire"]):
        return "INTAKE"
    if any(k in m for k in ["eligibility", "coverage", "estimate", "copay", "insurance"]):
        return "BILLING"
    if any(k in m for k in ["document", "upload", "signature"]):
        return "DOCS"
    return "QNA"

# === Request body the Book UI sends ===
class AgentRequest(BaseModel):
    # Accept both 'message' and 'reason'; default to empty so no 422
    message: str = ""
    reason: Optional[str] = None
    # <-- NEW: UI passes preferred 'when' as ISO string; orchestrator chooses slot
    when: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    appointment_id: Optional[int] = None
    patient_id: Optional[int] = None
    source_channel: Optional[str] = None 

def _parse_iso_utc(s: str) -> datetime:
    """
    Accept 'YYYY-MM-DDTHH:MM:SS.sssZ' or with offset; normalize to UTC aware datetime.
    """
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

@router.post("/scheduling/intake")
def scheduling_intake(
    body: AgentRequest,
    x_purpose_of_use: Optional[str] = Header(None, alias="X-Purpose-Of-Use"),
    db=Depends(get_db),
):
    # 0) PoU: TREATMENT or OPERATIONS is allowed for booking/intake orchestration
    if not x_purpose_of_use or x_purpose_of_use.upper() not in {"TREATMENT", "OPERATIONS"}:
        raise HTTPException(status_code=400, detail="Missing X-Purpose-Of-Use header")

    # 1) Normalize intent (not strictly needed here but safe for logs/analytics)
    user_msg = (body.message or body.reason or "").strip()
    state: Dict[str, Any] = dict(body.context or {})
    state["intent"] = state.get("intent") or infer_intent(user_msg)

    # 2) Minimal slot selection:
    #    - If 'when' is provided and is in the future, we accept it as the slot.
    #    - Otherwise, return 404 so UI shows "No slots available...".
    if not body.when:
        raise HTTPException(status_code=404, detail="No slots available")  # triggers UI message

    try:
        start_utc = _parse_iso_utc(body.when)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid 'when' format")

    now_utc = datetime.now(timezone.utc)
    if start_utc <= now_utc:
        raise HTTPException(status_code=404, detail="No slots available")  # past -> disallow

    # Round to a 30-min block (optional, keeps scheduler sane)
    minute_block = (start_utc.minute // 30) * 30
    start_utc = start_utc.replace(minute=minute_block, second=0, microsecond=0)
    end_utc = start_utc + timedelta(minutes=30)

    # 3) Choose patient_id:
    #    - Prefer explicit patient_id in body or context
    #    - Fall back to 1 in dev (you can wire real sessions later)
    patient_id = body.patient_id or state.get("patient_id") or 1

    source_channel = str(body.source_channel or state.get("source_channel") or "web").lower()

    # 4) Book the appointment by calling your existing /v1/appointments route
    #    (keeps all DB/EHR logic centralized there).
    appointment_payload = {
        "patient_id": int(patient_id),
        "reason": (body.reason or body.message or "office visit").strip(),
        "start": start_utc.isoformat(),   # API expects ISO strings
        "end": end_utc.isoformat(),
        "source_channel": source_channel, 
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "http://localhost:8000/v1/appointments",
                headers={"X-Purpose-Of-Use": "TREATMENT"},
                json=appointment_payload,
            )
        if resp.status_code == 404:
            # Propagate as "no slots" for the UI workflow you wanted
            raise HTTPException(status_code=404, detail="No slots available")
        resp.raise_for_status()
        appt = resp.json()  # {'ok': True, 'id': <int>, 'fhir': {...}}
    except httpx.HTTPError as e:
        # Network/backend failure → the web fetcher will surface as "Failed to fetch"
        raise HTTPException(status_code=502, detail=f"Booking failed: {e}") from e

    # 5) Return exactly what the Book UI expects
    return {"appointment_id": appt.get("id")}
