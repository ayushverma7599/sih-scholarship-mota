"""Officer Workbench — scrutiny queue, split-screen review, actions, SLA timers."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_roles
from app.models import (
    AIFlag, AppStatus, Application, Deficiency, Roles, StatusEvent, User,
)
from app.schemas import (
    BulkVerifyIn, OverrideIn, RaiseDeficiencyIn, RejectIn, VerifyIn,
)
from app.services import audit, risk
from app.services.notifications import notify
from app.services.serialize import application_public

router = APIRouter()

# Statuses that sit in the scrutiny queue.
_QUEUE_STATUSES = [
    AppStatus.SUBMITTED, AppStatus.AUTO_VERIFIED,
    AppStatus.UNDER_SCRUTINY, AppStatus.RESUBMITTED,
]


def _sla_hours(app: Application) -> float:
    ref = app.submitted_at or app.created_at
    if not ref:
        return 0.0
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - ref
    return round(delta.total_seconds() / 3600, 1)


@router.get("/queue")
def queue(
    scheme_id: int | None = None,
    status: str | None = None,
    state: str | None = None,
    min_risk: float | None = None,
    db: Session = Depends(get_db),
    officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN)),
):
    q = db.query(Application).filter(Application.status.in_(_QUEUE_STATUSES))
    if scheme_id:
        q = q.filter(Application.scheme_id == scheme_id)
    if status:
        q = q.filter(Application.status == status)
    rows = q.all()

    out = []
    for a in rows:
        if state and (a.applicant.profile or {}).get("state") != state:
            continue
        if min_risk is not None and a.risk_score < min_risk:
            continue
        item = application_public(a)
        item["sla_hours"] = _sla_hours(a)
        item["risk_level"] = ("high" if a.risk_score >= 60
                              else "medium" if a.risk_score >= 25 else "low")
        out.append(item)
    out.sort(key=lambda x: (-x["risk_score"], -x["sla_hours"]))
    return out


@router.get("/{app_id}")
def review(app_id: int, db: Session = Depends(get_db),
           officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    # Opening a fresh application moves it into scrutiny.
    if app.status in (AppStatus.SUBMITTED, AppStatus.AUTO_VERIFIED, AppStatus.RESUBMITTED):
        prev = app.status
        db.add(StatusEvent(application_id=app.id, from_status=prev,
                           to_status=AppStatus.UNDER_SCRUTINY, actor_id=officer.id,
                           note="Opened by scrutiny officer."))
        app.status = AppStatus.UNDER_SCRUTINY
        audit.record(db, actor=officer, entity="application", entity_id=app.id,
                     action="status_change", before={"status": prev},
                     after={"status": app.status}, commit=False)
        db.commit()
        db.refresh(app)
    data = application_public(app, detail=True)
    data["sla_hours"] = _sla_hours(app)
    data["risk"] = risk.compute_risk(app.flags)
    return data


@router.post("/{app_id}/verify")
def verify(app_id: int, payload: VerifyIn, db: Session = Depends(get_db),
           officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if any(d.status == "OPEN" for d in app.deficiencies):
        raise HTTPException(409, "Resolve or clear open deficiencies before verifying.")
    prev = app.status
    db.add(StatusEvent(application_id=app.id, from_status=prev,
                       to_status=AppStatus.SCREENED, actor_id=officer.id,
                       note=payload.note or "Verified by scrutiny officer."))
    app.status = AppStatus.SCREENED
    audit.record(db, actor=officer, entity="application", entity_id=app.id,
                 action="verify", before={"status": prev},
                 after={"status": app.status, "note": payload.note}, commit=False)
    notify(db, user_id=app.user_id, title="Application verified",
           message="Your application has cleared scrutiny and moved to screening.",
           channels=("in_app", "email"), commit=False)
    db.commit()
    return {"id": app.id, "status": app.status}


@router.post("/{app_id}/raise-deficiency")
def raise_deficiency(app_id: int, payload: RaiseDeficiencyIn, db: Session = Depends(get_db),
                     officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if not payload.items:
        raise HTTPException(400, "At least one deficiency item is required.")
    for item in payload.items:
        db.add(Deficiency(application_id=app.id, doc_type=item.get("doc_type"),
                          message=item.get("message", ""), status="OPEN",
                          raised_by=officer.id))
    prev = app.status
    db.add(StatusEvent(application_id=app.id, from_status=prev,
                       to_status=AppStatus.DEFICIENCY_RAISED, actor_id=officer.id,
                       note=payload.note or "Deficiency raised by officer."))
    app.status = AppStatus.DEFICIENCY_RAISED
    audit.record(db, actor=officer, entity="application", entity_id=app.id,
                 action="raise_deficiency", before={"status": prev},
                 after={"status": app.status, "items": payload.items}, commit=False)
    notify(db, user_id=app.user_id, title="Deficiency raised on your application",
           message=f"{len(payload.items)} item(s) need your attention. See your deficiency inbox.",
           channels=("in_app", "email"), commit=False)
    db.commit()
    return {"id": app.id, "status": app.status,
            "open_deficiencies": sum(1 for d in app.deficiencies if d.status == "OPEN")}


@router.post("/{app_id}/reject")
def reject(app_id: int, payload: RejectIn, db: Session = Depends(get_db),
           officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    prev = app.status
    db.add(StatusEvent(application_id=app.id, from_status=prev,
                       to_status=AppStatus.REJECTED, actor_id=officer.id,
                       note=payload.reason))
    app.status = AppStatus.REJECTED
    audit.record(db, actor=officer, entity="application", entity_id=app.id,
                 action="reject", before={"status": prev},
                 after={"status": app.status, "reason": payload.reason}, commit=False)
    notify(db, user_id=app.user_id, title="Application not accepted",
           message=f"Your application was rejected. Reason: {payload.reason}",
           channels=("in_app", "email"), commit=False)
    db.commit()
    return {"id": app.id, "status": app.status}


@router.post("/{app_id}/escalate")
def escalate(app_id: int, payload: VerifyIn, db: Session = Depends(get_db),
             officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    audit.record(db, actor=officer, entity="application", entity_id=app.id,
                 action="escalate", after={"note": payload.note})
    return {"id": app.id, "escalated": True, "note": payload.note}


@router.post("/bulk-verify")
def bulk_verify(payload: BulkVerifyIn, db: Session = Depends(get_db),
                officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    """Verify multiple clean, auto-verified applications at once."""
    verified, skipped = [], []
    for app_id in payload.application_ids:
        app = db.get(Application, app_id)
        if not app:
            skipped.append({"id": app_id, "reason": "not found"})
            continue
        if any(d.status == "OPEN" for d in app.deficiencies) or \
                any(not f.overridden and f.severity == "high" for f in app.flags):
            skipped.append({"id": app_id, "reason": "has open deficiency / high-severity flag"})
            continue
        prev = app.status
        db.add(StatusEvent(application_id=app.id, from_status=prev,
                           to_status=AppStatus.SCREENED, actor_id=officer.id,
                           note=payload.note or "Bulk verified (clean)."))
        app.status = AppStatus.SCREENED
        audit.record(db, actor=officer, entity="application", entity_id=app.id,
                     action="bulk_verify", before={"status": prev},
                     after={"status": app.status}, commit=False)
        verified.append(app_id)
    db.commit()
    return {"verified": verified, "skipped": skipped}


@router.post("/ai-flags/{flag_id}/override")
def override_flag(flag_id: int, payload: OverrideIn, db: Session = Depends(get_db),
                  officer: User = Depends(require_roles(Roles.SCRUTINY, Roles.ADMIN))):
    """Human override of an AI flag — always logged with a mandatory justification."""
    flag = db.get(AIFlag, flag_id)
    if not flag:
        raise HTTPException(404, "Flag not found")
    before = {"overridden": flag.overridden, "note": flag.override_note}
    flag.overridden = True
    flag.overridden_by = officer.id
    flag.override_note = payload.note
    # Recompute risk after override.
    app = flag.application
    app.risk_score = risk.compute_risk(app.flags)["score"]
    audit.record(db, actor=officer, entity="ai_flag", entity_id=flag.id,
                 action="override", before=before,
                 after={"overridden": True, "note": payload.note}, commit=False)
    db.commit()
    return {"id": flag.id, "overridden": True, "risk_score": app.risk_score}
