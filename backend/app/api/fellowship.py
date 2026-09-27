"""Post-Selection / Fellowship Management: joining, progress, JRF->SRF, disbursements."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models import (
    AppStatus, Disbursement, Fellowship, ProgressReport, Roles, StatusEvent, User,
)
from app.schemas import JoiningIn, ProgressIn, UpgradeIn
from app.services import audit
from app.services.govmocks import dbt_status
from app.services.notifications import notify

router = APIRouter()


def _get_fellowship(db: Session, fid: int, user: User) -> Fellowship:
    f = db.get(Fellowship, fid)
    if not f:
        raise HTTPException(404, "Fellowship not found")
    if user.role.name == Roles.APPLICANT and f.application.user_id != user.id:
        raise HTTPException(403, "Not your fellowship")
    return f


@router.get("/me")
def my_fellowships(db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    fels = (db.query(Fellowship).join(Fellowship.application)
            .filter(Fellowship.application.has(user_id=user.id)).all())
    return [_serialize(f) for f in fels]


@router.get("/{fid}")
def get_fellowship(fid: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    return _serialize(_get_fellowship(db, fid, user))


@router.post("/{fid}/joining")
def submit_joining(fid: int, payload: JoiningIn, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    f = _get_fellowship(db, fid, user)
    f.joining_date = payload.joining_date
    f.status = "ACTIVE"
    app = f.application
    if app.status != AppStatus.FELLOWSHIP_ACTIVE:
        db.add(StatusEvent(application_id=app.id, from_status=app.status,
                           to_status=AppStatus.FELLOWSHIP_ACTIVE, actor_id=user.id,
                           note="Joining report submitted."))
        app.status = AppStatus.FELLOWSHIP_ACTIVE

    # Seed a mock disbursement schedule (quarterly), clearly marked as mock DBT.
    if not f.disbursements:
        for i in range(4):
            db.add(Disbursement(
                fellowship_id=f.id, period=f"Q{i+1}", amount=75000.0,
                status="SCHEDULED", scheduled_for=payload.joining_date + timedelta(days=90 * i),
            ))
    audit.record(db, actor=user, entity="fellowship", entity_id=f.id,
                 action="joining", after={"joining_date": str(payload.joining_date)}, commit=False)
    notify(db, user_id=app.user_id, title="Fellowship activated",
           message="Your joining report is recorded and your fellowship is now active.",
           channels=("in_app",), commit=False)
    db.commit()
    return _serialize(f)


@router.post("/{fid}/progress")
def submit_progress(fid: int, payload: ProgressIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    f = _get_fellowship(db, fid, user)
    pr = ProgressReport(fellowship_id=f.id, period=payload.period, status="SUBMITTED")
    db.add(pr)
    audit.record(db, actor=user, entity="fellowship", entity_id=f.id,
                 action="progress_report", after={"period": payload.period}, commit=False)
    db.commit()
    return _serialize(f)


@router.post("/{fid}/upgrade")
def upgrade_stage(fid: int, payload: UpgradeIn, db: Session = Depends(get_db),
                  user: User = Depends(require_roles(Roles.ADMIN, Roles.COMMITTEE))):
    """JRF -> SRF upgradation (NFST). Renewal/upgrade check by admin/committee."""
    f = _get_fellowship(db, fid, user)
    before = {"stage": f.stage}
    f.stage = payload.stage
    audit.record(db, actor=user, entity="fellowship", entity_id=f.id,
                 action="upgrade", before=before,
                 after={"stage": f.stage, "note": payload.note}, commit=False)
    notify(db, user_id=f.application.user_id, title=f"Fellowship upgraded to {f.stage}",
           message=f"Your fellowship stage has been upgraded to {f.stage}.",
           channels=("in_app", "email"), commit=False)
    db.commit()
    return _serialize(f)


@router.get("/{fid}/disbursements")
def disbursements(fid: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    f = _get_fellowship(db, fid, user)
    return {
        "fellowship_id": f.id,
        "dbt_status": dbt_status(f"BEN{f.id:06d}"),   # MOCK
        "schedule": [
            {"period": d.period, "amount": d.amount, "status": d.status,
             "scheduled_for": d.scheduled_for.isoformat() if d.scheduled_for else None}
            for d in sorted(f.disbursements, key=lambda x: x.period)
        ],
    }


def _serialize(f: Fellowship) -> dict:
    return {
        "id": f.id, "application_id": f.application_id,
        "applicant_name": f.application.applicant.full_name,
        "scheme_code": f.application.scheme.code,
        "stage": f.stage, "status": f.status,
        "joining_date": f.joining_date.isoformat() if f.joining_date else None,
        "progress_reports": [
            {"id": p.id, "period": p.period, "status": p.status} for p in f.progress_reports
        ],
        "disbursements": [
            {"period": d.period, "amount": d.amount, "status": d.status}
            for d in f.disbursements
        ],
    }
