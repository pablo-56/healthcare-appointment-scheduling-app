# apps/api/app/schemas_scribe.py
# Pydantic types for the Ambient Scribe pilot (draft SOAP + coding suggestions)

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

class CodeSuggestion(BaseModel):
    system: Literal["ICD-10", "SNOMED", "CPT"] = Field(..., description="Coding system")
    code: str = Field(..., description="The code string")
    display: str = Field(..., description="Human readable label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence 0..1")
    rationale: Optional[str] = Field(None, description="Why this code was suggested")

class ScribeDraft(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    codes: List[CodeSuggestion] = Field(default_factory=list)
    confidence_overall: float = Field(default=0.7, ge=0.0, le=1.0)

class ScribeSessionCreate(BaseModel):
    appointment_id: int
    seed_text: Optional[str] = None  # optional quick note/seed

class ScribeApprove(BaseModel):
    note: ScribeDraft
    post_to_ehr: bool = True  # toggle in case you want to test without EHR side effects
