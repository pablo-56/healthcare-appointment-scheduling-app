# Healthcare Applications
AI agents can streamline appointment scheduling and management, assist with patient intake and onboarding processes, and support compliance and documentation by generating required regulatory records


One-liner

Agent-first Healthcare OS (FastAPI + React + FHIR):  MVP that automates booking, intake, e-consent, pre-charting, check-in, ambient scribe (HITL), RCM, compliance, and analytics with A/B testing.

Why it matters

Cuts no-shows and time-to-appointment with triage + smart scheduling.

Shrinks charting time via ambient scribe; improves first-pass claim acceptance.

Built with privacy by design (audit logs, PIA pack, de-ident exports).

What I built (concrete)

50+ REST endpoints (FastAPI), Celery workers, pgvector search.

FHIR bridge (mock EHR connector) for Schedule/Slot/Appointment/Encounter.

End-to-end patient journey (React): Book → Intake → Consent → Check-in → Summary → Follow-up → Tasks.

Compliance suite: audit/export/erasure with X-Purpose-Of-Use header enforcement.

Analytics & A/B: ops/RCM metrics APIs, Grafana dashboards, reminder experiments.

Demo script (what you’ll show live in 4–5 minutes)

Book a visit → slot selected automatically → confirmation.

Intake form → e-consent → docs appear.

Day-of check-in → queue position.

Provider closes note → patient sees summary → books follow-up.

Admin opens /admin/analytics → no-show/TTA; /admin/experiments → create reminder variants.

Architecture (short)

Frontend: React + Vite (typed fetch helper, optimistic UI).

API: FastAPI + SQLAlchemy + Alembic; LangGraph for agent orchestration.

Workers: Celery + Redis.

DB: Postgres (pgvector for RAG); metrics SQL views.

Observability: Prometheus + Grafana dashboards.

Security: JWT/cookies, purpose-of-use dependency, audit log.

Proof it’s real (screens/links)

GIFs: booking, intake/consent, check-in, analytics.

Swagger: /docs (shows analytics, compliance, experiments).

Grafana dashboards: ops & RCM panels.

My role / ownership

Led the design, wrote most of the API/DB, built the patient & admin UIs, wired FHIR mock, and added analytics/A-B infra.

Next steps

Swap mock EHR with real FHIR endpoint, add scribe streaming, and ship canary experiments for reminder timing.
