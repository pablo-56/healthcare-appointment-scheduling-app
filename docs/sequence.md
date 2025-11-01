```mermaid
sequenceDiagram
    autonumber
    actor Patient
    participant Web
    participant API
    participant Orchestrator
    participant EHR
    participant Worker
    participant Store
    participant Notify
    actor Clinician
    participant Billing

    Patient->>Web: Start booking / reply SMS
    Web->>API: POST /v1/sessions (OTP)
    API-->>Store: Audit session
    Web->>API: POST /v1/agents/scheduling/intake
    API->>Orchestrator: Triage + rules
    Orchestrator->>EHR: Schedule/Slot
    API->>EHR: Appointment.create
    EHR-->>API: id
    API-->>Store: appointments(BOOKED)
    API->>Notify: Confirmation + intake link

    Patient->>Web: Intake + Consent
    Web->>API: GET/POST intake; POST /documents/render
    API->>Worker: Render PDFs
    Worker-->>Store: documents + consents
    API->>EHR: DocumentReference mirror

    Patient->>Web: Check-in
    API->>EHR: Observation (vitals)
    Clinician->>API: Start scribe
    Worker-->>API: Draft note
    Clinician->>API: Approve
    API->>EHR: Encounter + DocumentReference

    API->>Worker: Discharge doc
    Worker-->>Store: documents
    API->>Notify: Summary + follow-up

    API->>Worker: Build 837
    Worker->>Billing: Submit claim
    Billing-->>Worker: 835 remit
    Worker-->>Store: claims.status
```
