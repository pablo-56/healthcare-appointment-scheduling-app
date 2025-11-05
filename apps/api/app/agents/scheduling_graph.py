import os
import httpx
from fastapi import HTTPException

EHR = os.getenv("EHR_CONNECTOR_URL", "http://ehr-connector:8100")

def fetch_slots() -> list[dict]:
    """
    Always return a list of slots: [{"id": "...","start":"...","end":"..."}].
    Try uppercase then lowercase endpoint for resilience.
    """
    last_exc = None
    for path in ("/fhir/Slot", "/fhir/slot"):
        try:
            r = httpx.get(f"{EHR}{path}", timeout=5.0)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            data = r.json() or {}
            entries = data.get("entry") or []
            out = []
            for e in entries:
                res = (e or {}).get("resource") or {}
                if res.get("resourceType") == "Slot" and str(res.get("status", "free")).lower() == "free":
                    out.append({
                        "id": res.get("id"),
                        "start": res.get("start"),
                        "end": res.get("end"),
                    })
            return out
        except httpx.HTTPError as exc:
            last_exc = exc
            continue
    # Hard failure -> return empty; caller will raise a clean HTTP error
    print(f"[scheduling] Slot endpoint unavailable: {last_exc or '404 Not Found'}")
    return []

# ... inside your orchestrator/run() logic:
def run(reason: str) -> dict:
    state: dict = {"reason": reason}

    slots = fetch_slots()          # <-- list, not dict
    state["slots"] = slots
    if not slots:
        # Surface a 503 back to the router (no cryptic 500s)
        raise HTTPException(status_code=503, detail="No free slots available from EHR connector")

    state["selected"] = slots[0]   # safe now
    # ... rest of your logic that books Appointment using `state["selected"]` ...
    return state
