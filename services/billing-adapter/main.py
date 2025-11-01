from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import os

app = FastAPI(title="Mock Billing Adapter")

class EligibilityRequest(BaseModel):
    appointment_id: int
    patient_email: str
    insurance_number: Optional[str] = None
    reason: Optional[str] = None
    plan_hint: Optional[str] = None

class EligibilityResponse(BaseModel):
    eligible: bool
    plan: str
    copay_cents: int
    raw_json: Dict

@app.get("/health")
def health():
    return {"ok": True}

# ultra-simple "rules"
_PLAN_TABLE = {
    "annual physical": ("PPO-GOLD", 2000),
    "follow up": ("PPO-SILVER", 3500),
}

@app.post("/eligibility", response_model=EligibilityResponse)
def check(req: EligibilityRequest):
    # Eligibility: require an insurance_number to return eligible=True
    eligible = bool(req.insurance_number)

    plan, copay = _PLAN_TABLE.get((req.reason or "").lower(), ("PPO-BASIC", 5000))
    if req.plan_hint:
        plan = req.plan_hint

    raw = {
        "x12": {
            "request": {"270": {"appt": req.appointment_id, "member": req.insurance_number}},
            "response": {"271": {"eligible": eligible, "plan": plan, "copay_cents": copay}},
        }
    }
    return EligibilityResponse(eligible=eligible, plan=plan, copay_cents=copay, raw_json=raw)


class ClaimIn(BaseModel):
    claim_id: int
    edi837: str
    payload: Dict[str, Any]

@app.post("/claims")
def claims_create(body: ClaimIn):
    # pretend clearinghouse acceptance and give back a payer reference
    return {
        "accepted": True,
        "payer_ref": f"CH-{body.claim_id}-{int(datetime.utcnow().timestamp())}",
        "received_at": datetime.utcnow().isoformat() + "Z",
    }