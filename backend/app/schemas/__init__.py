"""Pydantic v2 request/response schemas.

Kept intentionally lightweight — configurable JSON blobs (rules, weights, form
data) are validated as `dict`/`list` so the platform stays scheme-agnostic.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class RegisterIn(BaseModel):
    email: EmailStr
    mobile: str | None = None
    full_name: str = ""
    password: str = Field(min_length=6)
    role: str = "applicant"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class OTPRequestIn(BaseModel):
    identifier: str  # email or mobile


class OTPVerifyIn(BaseModel):
    identifier: str
    otp: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str


class UserOut(BaseModel):
    id: int
    email: str
    mobile: str | None = None
    full_name: str
    role: str
    campus_verified: bool
    profile: dict = {}


class ProfileUpdateIn(BaseModel):
    full_name: str | None = None
    mobile: str | None = None
    profile: dict = {}


# --------------------------------------------------------------------------- #
# Schemes / config
# --------------------------------------------------------------------------- #
class SchemeDocumentIn(BaseModel):
    doc_type: str
    label: str
    mandatory: bool = True
    extract_fields: list[str] = []
    order: int = 0


class SchemeIn(BaseModel):
    code: str
    name: str
    description: str = ""
    academic_year: str = ""
    slots: int = 0
    window_open: date | None = None
    window_close: date | None = None
    is_active: bool = True
    is_sample: bool = True
    rules: dict = {}
    documents: list[SchemeDocumentIn] = []
    merit_weights: dict = {}
    merit_tiebreak: list[str] = []
    merit_quotas: dict = {}


class SchemeUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    academic_year: str | None = None
    slots: int | None = None
    window_open: date | None = None
    window_close: date | None = None
    is_active: bool | None = None
    is_sample: bool | None = None
    rules: dict | None = None
    documents: list[SchemeDocumentIn] | None = None
    merit_weights: dict | None = None
    merit_tiebreak: list[str] | None = None
    merit_quotas: dict | None = None


class EligibilityCheckIn(BaseModel):
    profile: dict = {}
    form_data: dict = {}


# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #
class ApplicationCreateIn(BaseModel):
    scheme_id: int
    form_data: dict = {}


class ApplicationUpdateIn(BaseModel):
    form_data: dict | None = None
    draft: dict | None = None


class DeficiencyRespondIn(BaseModel):
    response: str = ""


# --------------------------------------------------------------------------- #
# Scrutiny / officer actions
# --------------------------------------------------------------------------- #
class VerifyIn(BaseModel):
    note: str = ""


class RaiseDeficiencyIn(BaseModel):
    items: list[dict] = []   # [{"doc_type":..,"message":..}]
    note: str = ""


class RejectIn(BaseModel):
    reason: str


class OverrideIn(BaseModel):
    note: str = Field(min_length=3)


class BulkVerifyIn(BaseModel):
    application_ids: list[int]
    note: str = ""


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #
class MeritAdjustIn(BaseModel):
    rank: int | None = None
    selected: bool | None = None
    justification: str = Field(min_length=5)


# --------------------------------------------------------------------------- #
# Fellowship / grievance
# --------------------------------------------------------------------------- #
class JoiningIn(BaseModel):
    joining_date: date


class ProgressIn(BaseModel):
    period: str
    note: str = ""


class UpgradeIn(BaseModel):
    stage: str = "SRF"
    note: str = ""


class GrievanceIn(BaseModel):
    subject: str
    body: str = ""
    application_id: int | None = None


class GrievanceUpdateIn(BaseModel):
    status: str | None = None
    response: str | None = None
