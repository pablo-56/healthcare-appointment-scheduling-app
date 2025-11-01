# Alberta HIA PIA Checklist (Phase 0)
- Custodian & affiliates identified
- Purpose & scope defined (login/session)
- Data elements: email/phone, audit logs
- Safeguards: JWT, PoU soft enforcement, TLS in transit
- Retention: OTP TTL 5m; audit logs retained
- Risks: OTP interception (mitigated by TTL), weak PoU (dev only)
- Plan: Harden in later phases (approval flows, encryption at rest, key mgmt)
