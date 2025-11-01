from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Index, Boolean 
from sqlalchemy.sql import func
from .db import Base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy import text as sa_text
from sqlalchemy.orm import relationship


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    mrn = Column(String(64), unique=True, index=True, nullable=True)
    first_name = Column(String(128))
    last_name = Column(String(128))
    phone = Column(String(32), index=True, nullable=True)
    email = Column(String(256), index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    start_at = Column(DateTime(timezone=True))
    end_at = Column(DateTime(timezone=True))
    status = Column(String(32), index=True)
    fhir_appointment_id = Column(String(128), nullable=True)
    reason = Column(String(256), nullable=True)
    source_channel = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class IntakeForm(Base):
    __tablename__ = "intake_forms"
    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    answers_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Consent(Base):
    __tablename__ = "consents"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    pdf_url = Column(Text, nullable=True)
    sha256 = Column(String(64), nullable=True)
    signer_name = Column(String(128), nullable=True)
    signer_ip = Column(String(64), nullable=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    kind = Column(String(64), index=True)
    url = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    type = Column(String(64), index=True)
    status = Column(String(32), index=True, default="open")
    payload_json = Column(JSON, nullable=True)
    assignee = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Claim(Base):
    __tablename__ = "claims"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    status = Column(String(32), index=True, default="NEW")
    payer_ref = Column(String(128), nullable=True)
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PolicyChunk(Base):
    __tablename__ = "policy_chunks"
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)  # true vector column created in migration
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor = Column(String(128))
    action = Column(String(128), index=True)
    target = Column(String(128), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
# --- Phase 3 table ---
class EligibilityResponse(Base):
    __tablename__ = "eligibility_responses"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, index=True, nullable=False)
    eligible = Column(Boolean, nullable=False, default=False)
    plan = Column(String, nullable=False)
    copay_cents = Column(Integer, nullable=False, default=0)
    raw_json = Column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)  


# --- Phase 6 optional ORM (tables already created via raw SQL in router) ---
class ScribeSession(Base):
    __tablename__ = "scribe_sessions"
    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, index=True, nullable=False)
    status = Column(String(32), index=True, default="DRAFT")
    draft_json = Column(JSONB, nullable=True)
    confidence_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PatientSurvey(Base):
    __tablename__ = "patient_surveys"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    instrument = Column(String(32), index=True, nullable=False)             # e.g., "phq9", "gad7"
    score = Column(Integer, nullable=False)
    answers = Column(JSON, nullable=False)                                  # list[int] or dict per instrument
    meta = Column(JSON, nullable=True)                                      # optional (encounter_id, language, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Compliance requests ------------------------------------------------------
class ComplianceRequest(Base):
    """
    Tracks export/erasure requests and system-initiated scans (e.g., anomaly).
    """
    __tablename__ = "compliance_requests"

    id = Column(Integer, primary_key=True)
    # 'export' | 'erasure' | 'anomaly' | 'retention'
    kind = Column(String(32), index=True, nullable=False)

    # scope/subject of the request (e.g., patient to export/erase)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True, index=True)

    # workflow + bookkeeping
    status = Column(String(32), index=True, nullable=False, default="NEW")  # NEW|PENDING|APPROVED|RUNNING|DONE|DENIED|ERROR
    requested_by = Column(String(255), nullable=True)  # email/subject
    approved_by = Column(String(255), nullable=True)
    legal_hold = Column(Boolean, nullable=False, default=False)

    # result artifact (e.g., s3://… or data: URL) when applicable
    result_url = Column(String(1024), nullable=True)

    # freeform data (filters, reasons, error messages, counts, redaction plan, etc.)
    meta = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# === Phase 11: Analytics & Experiments ======================================

class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    status = Column(String(16), nullable=False, default="open")  # open|paused|closed
    # Variants definition stored as JSON, e.g.:
    # {"A":{"subject":"Reminder A","channel":"email","timing":"24h"},
    #  "B":{"subject":"Reminder B","channel":"sms","timing":"48h"}}
    variants = Column(JSON, nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assignments = relationship("ExperimentAssignment", cascade="all, delete-orphan",
                               backref="experiment")

class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"),
                           index=True, nullable=False)
    # Subject is the entity that receives the reminder (often a patient_id)
    subject_id = Column(Integer, nullable=True)
    channel = Column(String(16), nullable=True)      # email|sms|push
    variant = Column(String(32), nullable=False)     # "A" | "B" | ...
    sent_at = Column(DateTime(timezone=True), nullable=True)
    outcome = Column(String(32), nullable=True)      # opened|clicked|no_show|completed|...
    meta = Column(JSON, nullable=True)               # transport ids, delivery response, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())


Index("ix_audit_action_time", AuditLog.action, AuditLog.created_at.desc())
