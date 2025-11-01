from fastapi import APIRouter
from pydantic import BaseModel
from ..agents import scheduling_graph

router = APIRouter()

class IntakeBody(BaseModel):
    reason: str

@router.post("/v1/agents/scheduling/intake")
def scheduling_intake(body: IntakeBody):
    """
    Returns triage intent + available slots from EHR mock.
    """
    state = scheduling_graph.run(body.reason)
    return {
        "intent": state["intent"],
        "slots": state["slots"],
    }
