from fastapi import FastAPI, status
from pydantic import BaseModel
from uuid import uuid4
from typing import List, Dict, Any

app = FastAPI(title='EHR Connector Mock')
_doc_refs = []
_id = 1

# these are additive mocks that your Celery task can call

# if your file already defines `app = FastAPI()`, reuse it.
try:
    app  # type: ignore  # noqa: F401
except NameError:
    app = FastAPI()


@app.get('/ping')
def ping(): return {'pong': True}

@app.get('/fhir/Schedule')
def schedule():
    return {'resourceType': 'Bundle', 'entry': [{'resource': {'id': 'sched-1', 'actor': [{'display': 'Dr. Mock'}]}}]}

@app.get('/fhir/Slot')
def slot():
    return {
        'resourceType':'Bundle',
        'entry':[
            {'resource': {'id':'slot-1','start':'2025-01-01T09:00:00Z','end':'2025-01-01T09:20:00Z'}},
            {'resource': {'id':'slot-2','start':'2025-01-01T09:20:00Z','end':'2025-01-01T09:40:00Z'}},
        ]
    }

class Appointment(BaseModel):
    resourceType: str = "Appointment"
    status: str = "booked"
    start: str
    end: str
    reasonCode: List[dict] = []
    slot: List[dict] = []

@app.post('/fhir/Appointment', status_code=status.HTTP_201_CREATED)
def create_appt(appt: Appointment):
    # return minimal FHIR-ish response
    return {"resourceType":"Appointment","id":"ehr-appt-123","status":appt.status,"start":appt.start,"end":appt.end}

class FHIRResource(BaseModel):
    resourceType: str
    # accept any content
    # we’ll not enforce full FHIR in mock

#@app.post("/fhir/DocumentReference")
#def create_document_reference(res: Dict[str, Any]):
 #   global _id
  #  res["id"] = f"dr-{_id}"
   # _id += 1
    #_doc_refs.append(res)
    #return res

app = FastAPI()

class DocRef(BaseModel):
    resourceType: str
    status: str
    type: dict | None = None
    description: str | None = None
    content: list | None = None

@app.post("/fhir/DocumentReference")
def document_reference_create(body: DocRef):
    # Mock accept + echo back an id
    return {"resourceType": "DocumentReference", "id": "docref-1", "status": body.status}

class ObservationReq(BaseModel):
    appointment_id: int
    vitals: dict
    effectiveDateTime: str | None = None

@app.post("/fhir/Observation")
def create_observation(req: ObservationReq):
    """
    Mock FHIR Observation.create — accepts vitals JSON and returns an ID.
    """
    obs_id = f"obs-{uuid4().hex[:8]}"
    return {"id": obs_id, "status": "created", "appointment_id": req.appointment_id}

# services/ehr-connector/main.py (append these mock endpoints)

@app.get("/fhir/Appointment/{ehr_appt_id}")
def get_appointment(ehr_appt_id: str):
    # Lightweight appointment echo
    return {
        "resourceType": "Appointment",
        "id": ehr_appt_id,
        "status": "booked",
        "start": "2025-01-01T09:00:00Z",
        "end": "2025-01-01T09:20:00Z",
    }

@app.get("/fhir/Condition")
def list_condition(appointment: str | None = None):
    return {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Condition", "code": {"text": "Hypertension"}}},
            {"resource": {"resourceType": "Condition", "code": {"text": "Prediabetes"}}},
        ]
    }

@app.get("/fhir/MedicationStatement")
def list_medications(appointment: str | None = None):
    return {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "MedicationStatement",
                          "medicationCodeableConcept": {"text": "Lisinopril 10 mg daily"}}},
            {"resource": {"resourceType": "MedicationStatement",
                          "medicationCodeableConcept": {"text": "Metformin 500 mg bid"}}},
        ]
    }

@app.get("/fhir/Observation")
def list_observations(appointment: str | None = None):
    return {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Observation", "code": {"text": "BP 128/78 mmHg"}}},
            {"resource": {"resourceType": "Observation", "code": {"text": "BMI 27.4 kg/m²"}}},
        ]
    }

@app.get("/fhir/Encounter")
def list_encounters(appointment: str | None = None):
    return {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Encounter",
                    "type": [{"text": "Primary care follow-up"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "type": [{"text": "Annual physical"}],
                }
            },
        ],
    }


# --- Phase 6 EHR mocks (append) ---
from fastapi import Body
from uuid import uuid4

@app.post("/fhir/DocumentReference")
def create_document_reference(body: dict = Body(...)):
    """
    Minimal mock that accepts a DocumentReference JSON and returns an id.
    Stores nothing; just acknowledges.
    """
    return {"resourceType": "DocumentReference", "id": f"docref-{uuid4()}", "status": "current"}

@app.post("/fhir/Encounter/{enc_id}/$update")
def update_encounter(enc_id: str, body: dict = Body(...)):
    """
    Minimal mock for encounter update (status, etc.)
    """
    return {"resourceType": "Encounter", "id": enc_id, "status": body.get("status", "in-progress")}

