"""MOCK government verification endpoints (DigiLocker / e-District).

Clearly labelled — every response carries "mock": true.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.rbac import require_roles
from app.models import Roles, User
from app.services import govmocks

router = APIRouter()


class STVerifyIn(BaseModel):
    certificate_number: str
    name: str


class IncomeVerifyIn(BaseModel):
    certificate_number: str
    income: float


@router.post("/digilocker/verify-st")
def verify_st(payload: STVerifyIn,
              officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    return govmocks.verify_st_certificate(payload.certificate_number, payload.name)


@router.post("/edistrict/verify-income")
def verify_income(payload: IncomeVerifyIn,
                  officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    return govmocks.verify_income_certificate(payload.certificate_number, payload.income)
