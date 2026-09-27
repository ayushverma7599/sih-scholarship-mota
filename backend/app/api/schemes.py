"""Scheme Configuration Engine — the configurable core of the platform.

Admins create/edit schemes (eligibility rules, required documents, merit weights)
entirely through data — no code changes per scheme. Applicants/officers read them.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models import (
    EligibilityRuleset, MeritCriteria, Roles, Scheme, SchemeDocument, User,
)
from app.schemas import EligibilityCheckIn, SchemeIn, SchemeUpdateIn
from app.services import audit, rule_engine
from app.services.serialize import scheme_public

router = APIRouter()


def _apply_documents(db: Session, scheme: Scheme, documents: list):
    for d in list(scheme.documents):
        db.delete(d)
    scheme.documents = []
    for d in documents:
        db.add(SchemeDocument(
            scheme_id=scheme.id, doc_type=d.doc_type, label=d.label,
            mandatory=d.mandatory, extract_fields=d.extract_fields, order=d.order,
        ))


@router.get("")
def list_schemes(
    active_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Scheme)
    if active_only:
        q = q.filter(Scheme.is_active == True)  # noqa: E712
    return [scheme_public(s) for s in q.order_by(Scheme.id).all()]


@router.get("/{scheme_id}")
def get_scheme(scheme_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    scheme = db.get(Scheme, scheme_id)
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    return scheme_public(scheme)


@router.post("", status_code=201)
def create_scheme(
    payload: SchemeIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Roles.ADMIN)),
):
    scheme = Scheme(
        code=payload.code, name=payload.name, description=payload.description,
        academic_year=payload.academic_year, slots=payload.slots,
        window_open=payload.window_open, window_close=payload.window_close,
        is_active=payload.is_active, is_sample=payload.is_sample,
    )
    db.add(scheme)
    db.flush()
    scheme.ruleset = EligibilityRuleset(scheme_id=scheme.id, rules=payload.rules)
    scheme.merit_criteria = MeritCriteria(
        scheme_id=scheme.id, weights=payload.merit_weights,
        tiebreak=payload.merit_tiebreak, quotas=payload.merit_quotas,
    )
    _apply_documents(db, scheme, payload.documents)
    db.commit()
    db.refresh(scheme)
    audit.record(db, actor=user, entity="scheme", entity_id=scheme.id,
                 action="create", after={"code": scheme.code, "name": scheme.name})
    return scheme_public(scheme)


@router.put("/{scheme_id}")
def update_scheme(
    scheme_id: int,
    payload: SchemeUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Roles.ADMIN)),
):
    scheme = db.get(Scheme, scheme_id)
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    before = scheme_public(scheme)

    for field in ("name", "description", "academic_year", "slots",
                  "window_open", "window_close", "is_active", "is_sample"):
        val = getattr(payload, field)
        if val is not None:
            setattr(scheme, field, val)

    if payload.rules is not None:
        if scheme.ruleset:
            scheme.ruleset.rules = payload.rules
        else:
            scheme.ruleset = EligibilityRuleset(scheme_id=scheme.id, rules=payload.rules)
    if payload.merit_weights is not None or payload.merit_tiebreak is not None \
            or payload.merit_quotas is not None:
        mc = scheme.merit_criteria or MeritCriteria(scheme_id=scheme.id)
        if payload.merit_weights is not None:
            mc.weights = payload.merit_weights
        if payload.merit_tiebreak is not None:
            mc.tiebreak = payload.merit_tiebreak
        if payload.merit_quotas is not None:
            mc.quotas = payload.merit_quotas
        scheme.merit_criteria = mc
    if payload.documents is not None:
        _apply_documents(db, scheme, payload.documents)

    db.commit()
    db.refresh(scheme)
    audit.record(db, actor=user, entity="scheme", entity_id=scheme.id,
                 action="config_change", before=before, after=scheme_public(scheme))
    return scheme_public(scheme)


@router.post("/{scheme_id}/eligibility-check")
def eligibility_check(
    scheme_id: int,
    payload: EligibilityCheckIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dry-run the scheme's rules against a supplied profile (+ optional form data)."""
    scheme = db.get(Scheme, scheme_id)
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    ctx = rule_engine.build_context(payload.profile, payload.form_data)
    result = rule_engine.evaluate(scheme.ruleset.rules if scheme.ruleset else None, ctx)
    return {"scheme_id": scheme_id, "scheme_code": scheme.code, **result}
