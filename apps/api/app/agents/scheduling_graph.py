# LangGraph-style, but intentionally lightweight: rule-based triage + slot fetch.
from typing import TypedDict, List, Dict, Any
import httpx
from ..settings import settings

class SchedState(TypedDict, total=False):
    reason: str
    intent: str
    slots: List[Dict[str, Any]]

KEYWORDS_CLINICAL = {"physical", "checkup", "cough", "pain", "injury", "diabetes", "bp", "blood", "fever"}
KEYWORDS_ADMIN = {"forms", "paperwork", "insurance", "admin", "note", "refill", "referral"}

def triage_intent(reason: str) -> str:
    r = reason.lower()
    if any(k in r for k in KEYWORDS_CLINICAL): return "clinical"
    if any(k in r for k in KEYWORDS_ADMIN):    return "admin"
    return "clinical"  # default safe

def fetch_slots() -> List[Dict[str, Any]]:
    # Pull mock Schedule & Slot from EHR connector; in prod you’d filter by provider/panel.
    with httpx.Client(timeout=10) as client:
        _ = client.get(f"{settings.ehr_base}/fhir/Schedule")
        res = client.get(f"{settings.ehr_base}/fhir/Slot")
        res.raise_for_status()
        data = res.json()
        entries = data.get("entry", []) if isinstance(data, dict) else []
        slots = []
        for e in entries:
            resrc = e.get("resource", {})
            if resrc.get("id") and resrc.get("start") and resrc.get("end"):
                slots.append({
                    "slot_id": resrc["id"],
                    "start": resrc["start"],
                    "end": resrc["end"],
                })
        return slots

def run(reason: str) -> SchedState:
    # This simulates a small graph: triage -> availability -> done
    state: SchedState = {"reason": reason}
    state["intent"] = triage_intent(reason)
    state["slots"] = fetch_slots()
    return state
