"""SQLAlchemy ORM models for the Scholarship & Fellowship Management System.

All models live here for simple imports (`from app.models import User, ...`).
JSON columns are used for configurable rule sets / weights and portable across
SQLite and PostgreSQL.
"""
from __future__ import annotations

from datetime import datetime, date, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Roles / Application status — kept as string constants (configurable-friendly)
# --------------------------------------------------------------------------- #
class Roles:
    APPLICANT = "applicant"
    SCRUTINY = "scrutiny"
    COMMITTEE = "committee"
    ADMIN = "admin"
    ALL = ["applicant", "scrutiny", "committee", "admin"]


class AppStatus:
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    AUTO_VERIFIED = "AUTO_VERIFIED"
    UNDER_SCRUTINY = "UNDER_SCRUTINY"
    DEFICIENCY_RAISED = "DEFICIENCY_RAISED"
    RESUBMITTED = "RESUBMITTED"
    SCREENED = "SCREENED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    FELLOWSHIP_ACTIVE = "FELLOWSHIP_ACTIVE"
    # Ordered pipeline for the applicant timeline widget.
    PIPELINE = [
        "SUBMITTED", "AUTO_VERIFIED", "UNDER_SCRUTINY", "DEFICIENCY_RAISED",
        "RESUBMITTED", "SCREENED", "SELECTED", "FELLOWSHIP_ACTIVE",
    ]


# --------------------------------------------------------------------------- #
# Users & roles
# --------------------------------------------------------------------------- #
class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    users: Mapped[list[User]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    mobile: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    # profile: personal, tribe/community, income, academics, bank(encrypted)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    campus_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    role: Mapped[Role] = relationship(back_populates="users")
    applications: Mapped[list[Application]] = relationship(back_populates="applicant")


# --------------------------------------------------------------------------- #
# Scheme configuration (the configurable core)
# --------------------------------------------------------------------------- #
class Scheme(Base):
    __tablename__ = "schemes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), index=True)   # NFST | NOS | ...
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    academic_year: Mapped[str] = mapped_column(String(16), default="")
    slots: Mapped[int] = mapped_column(Integer, default=0)
    window_open: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_close: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # UI badge: sample values pending official MoTA guidelines.
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    ruleset: Mapped[EligibilityRuleset] = relationship(
        back_populates="scheme", uselist=False, cascade="all, delete-orphan"
    )
    documents: Mapped[list[SchemeDocument]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    merit_criteria: Mapped[MeritCriteria] = relationship(
        back_populates="scheme", uselist=False, cascade="all, delete-orphan"
    )
    applications: Mapped[list[Application]] = relationship(back_populates="scheme")


class EligibilityRuleset(Base):
    __tablename__ = "eligibility_rulesets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id"))
    # {"combinator": "all", "rules": [{"field","op","value","label"}]}
    rules: Mapped[dict] = mapped_column(JSON, default=dict)

    scheme: Mapped[Scheme] = relationship(back_populates="ruleset")


class SchemeDocument(Base):
    __tablename__ = "scheme_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id"))
    doc_type: Mapped[str] = mapped_column(String(64))          # st_certificate, income_certificate...
    label: Mapped[str] = mapped_column(String(160))
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    # fields to extract via OCR, e.g. ["name","certificate_number","issuing_authority"]
    extract_fields: Mapped[list] = mapped_column(JSON, default=list)
    order: Mapped[int] = mapped_column(Integer, default=0)

    scheme: Mapped[Scheme] = relationship(back_populates="documents")


class MeritCriteria(Base):
    __tablename__ = "merit_criteria"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id"))
    # weights: {"marks":0.4,"income_bracket":0.2,"university_rank":0.2,"research_proposal":0.2}
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    # tiebreak: ["marks","age_asc"]
    tiebreak: Mapped[list] = mapped_column(JSON, default=list)
    # quotas: {"women":0.3,"pvtg":0.1}
    quotas: Mapped[dict] = mapped_column(JSON, default=dict)

    scheme: Mapped[Scheme] = relationship(back_populates="merit_criteria")


# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #
class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id"))
    status: Mapped[str] = mapped_column(String(32), default=AppStatus.DRAFT, index=True)
    form_data: Mapped[dict] = mapped_column(JSON, default=dict)
    draft: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    applicant: Mapped[User] = relationship(back_populates="applications")
    scheme: Mapped[Scheme] = relationship(back_populates="applications")
    documents: Mapped[list[ApplicationDocument]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    flags: Mapped[list[AIFlag]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    deficiencies: Mapped[list[Deficiency]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    events: Mapped[list[StatusEvent]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    merit: Mapped[MeritScore] = relationship(
        back_populates="application", uselist=False, cascade="all, delete-orphan"
    )
    fellowship: Mapped[Fellowship] = relationship(
        back_populates="application", uselist=False, cascade="all, delete-orphan"
    )


class ApplicationDocument(Base):
    __tablename__ = "application_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    scheme_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheme_documents.id"), nullable=True
    )
    doc_type: Mapped[str] = mapped_column(String(64))        # expected slot type
    detected_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512))
    original_name: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(64), default="")
    readability: Mapped[float] = mapped_column(Float, default=0.0)
    sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    application: Mapped[Application] = relationship(back_populates="documents")
    extracted: Mapped[list[ExtractedField]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_document_id: Mapped[int] = mapped_column(ForeignKey("application_documents.id"))
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(String(255), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    document: Mapped[ApplicationDocument] = relationship(back_populates="extracted")


# --------------------------------------------------------------------------- #
# AI flags, deficiencies, status events, merit
# --------------------------------------------------------------------------- #
class AIFlag(Base):
    __tablename__ = "ai_flags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    type: Mapped[str] = mapped_column(String(48))        # mismatch, income_exceeded, wrong_doc...
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high
    reason: Mapped[str] = mapped_column(Text, default="")  # human-readable WHY
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    overridden_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    override_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    application: Mapped[Application] = relationship(back_populates="flags")


class Deficiency(Base):
    __tablename__ = "deficiencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    doc_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text)             # plain-language
    status: Mapped[str] = mapped_column(String(16), default="OPEN")  # OPEN|RESOLVED
    raised_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    applicant_response: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    application: Mapped[Application] = relationship(back_populates="deficiencies")


class StatusEvent(Base):
    __tablename__ = "status_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    application: Mapped[Application] = relationship(back_populates="events")


class MeritScore(Base):
    __tablename__ = "merit_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    total: Mapped[float] = mapped_column(Float, default=0.0)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)  # per-criterion contribution
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quota_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    adjusted: Mapped[bool] = mapped_column(Boolean, default=False)
    adjustment_note: Mapped[str] = mapped_column(Text, default="")

    application: Mapped[Application] = relationship(back_populates="merit")


# --------------------------------------------------------------------------- #
# Post-selection / fellowship management
# --------------------------------------------------------------------------- #
class Fellowship(Base):
    __tablename__ = "fellowships"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    stage: Mapped[str] = mapped_column(String(8), default="JRF")   # JRF | SRF
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="AWAITING_JOINING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    application: Mapped[Application] = relationship(back_populates="fellowship")
    progress_reports: Mapped[list[ProgressReport]] = relationship(
        back_populates="fellowship", cascade="all, delete-orphan"
    )
    disbursements: Mapped[list[Disbursement]] = relationship(
        back_populates="fellowship", cascade="all, delete-orphan"
    )


class ProgressReport(Base):
    __tablename__ = "progress_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fellowship_id: Mapped[int] = mapped_column(ForeignKey("fellowships.id"))
    period: Mapped[str] = mapped_column(String(32))
    file_path: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(16), default="SUBMITTED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    fellowship: Mapped[Fellowship] = relationship(back_populates="progress_reports")


class Disbursement(Base):
    __tablename__ = "disbursements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fellowship_id: Mapped[int] = mapped_column(ForeignKey("fellowships.id"))
    period: Mapped[str] = mapped_column(String(32))
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="SCHEDULED")  # mock DBT/PFMS
    scheduled_for: Mapped[date | None] = mapped_column(Date, nullable=True)

    fellowship: Mapped[Fellowship] = relationship(back_populates="disbursements")


# --------------------------------------------------------------------------- #
# Grievance, notifications, audit
# --------------------------------------------------------------------------- #
class Grievance(Base):
    __tablename__ = "grievances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="OPEN")  # OPEN|IN_PROGRESS|RESOLVED
    response: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16), default="in_app")  # in_app|email|sms(mock)
    title: Mapped[str] = mapped_column(String(200), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(32), default="")
    entity: Mapped[str] = mapped_column(String(48))       # application, scheme, ai_flag...
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(48))       # status_change, override, config_change
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


__all__ = [
    "Roles", "AppStatus", "Role", "User", "Scheme", "EligibilityRuleset",
    "SchemeDocument", "MeritCriteria", "Application", "ApplicationDocument",
    "ExtractedField", "AIFlag", "Deficiency", "StatusEvent", "MeritScore",
    "Fellowship", "ProgressReport", "Disbursement", "Grievance", "Notification",
    "AuditLog",
]
