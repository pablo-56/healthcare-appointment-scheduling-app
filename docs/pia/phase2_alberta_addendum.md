# PIA Addendum — Phase 2 (Intake, E-consent, Doc Gen)

- New PHI collected: intake answers (demographics, insurance), e-signature metadata.
- Storage: Postgres (answers_json), S3/MinIO (PDFs under `s3://docs/intake/` and `s3://docs/consent/`).
- Security controls:
  - HMAC validation on `/v1/signature/webhook` (secret in Secrets Manager later).
  - Server-side encryption (AES256) for object storage in dev; SSE-KMS in prod.
  - Append-only `audit_logs` for `CONSENT_REQUESTED` and `CONSENT_SIGNED`.
- Retention:
  - PDFs retained for legal minimum; lifecycle rules to Glacier/IA after 180 days (prod).
- Subprocessors/vendors (mock now; real later): e-sign provider.
- Breach playbook updated to include e-signature and document stores.
