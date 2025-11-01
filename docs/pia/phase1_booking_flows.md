# PIA Addendum — Phase 1 (Access & Scheduling)

**Purpose:** Collect minimal PHI to schedule visits; deliver a one-time intake link to the patient.

**Flows covered:**
- Reason-of-visit capture ➜ slot search ➜ booking ➜ confirmation notify
- Data elements: email (optional, for confirmation), reason free-text, selected slot, timestamps
- System disclosures: EHR (FHIR Appointment.create), notification provider (stub in dev)
- Logging: `audit_logs` records `APPOINTMENT_BOOKED` (actor=email, target=fhir_appointment_id)

**Purpose-of-Use:** Booking writes require `X-Purpose-Of-Use: TREATMENT`. Soft enforcement on reads.

**Retention:** Appointment rows retained per clinic policy; audit logs append-only.

**Security controls:** JWT-authenticated session; PoU middleware; Prometheus/Grafana monitoring.
