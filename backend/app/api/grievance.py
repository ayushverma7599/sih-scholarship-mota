"""Grievance module: applicants raise tickets, admins/committee update status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models import Grievance, Roles, User
from app.schemas import GrievanceIn, GrievanceUpdateIn
from app.services import audit
from app.services.notifications import notify

router = APIRouter()


@router.get("")
def list_grievances(db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    q = db.query(Grievance)
    if user.role.name == Roles.APPLICANT:
        q = q.filter(Grievance.user_id == user.id)
    return [
        {"id": g.id, "subject": g.subject, "body": g.body, "status": g.status,
         "response": g.response, "application_id": g.application_id,
         "created_at": g.created_at.isoformat()}
        for g in q.order_by(Grievance.created_at.desc()).all()
    ]


@router.post("", status_code=201)
def create_grievance(payload: GrievanceIn, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    g = Grievance(user_id=user.id, subject=payload.subject, body=payload.body,
                  application_id=payload.application_id, status="OPEN")
    db.add(g)
    db.commit()
    db.refresh(g)
    return {"id": g.id, "status": g.status}


@router.put("/{gid}")
def update_grievance(gid: int, payload: GrievanceUpdateIn, db: Session = Depends(get_db),
                     user: User = Depends(require_roles(Roles.ADMIN, Roles.COMMITTEE, Roles.SCRUTINY))):
    g = db.get(Grievance, gid)
    if not g:
        raise HTTPException(404, "Grievance not found")
    before = {"status": g.status, "response": g.response}
    if payload.status:
        g.status = payload.status
    if payload.response is not None:
        g.response = payload.response
    audit.record(db, actor=user, entity="grievance", entity_id=g.id,
                 action="update", before=before,
                 after={"status": g.status, "response": g.response}, commit=False)
    notify(db, user_id=g.user_id, title="Update on your grievance",
           message=f"Your grievance '{g.subject}' is now {g.status}.",
           channels=("in_app",), commit=False)
    db.commit()
    return {"id": g.id, "status": g.status, "response": g.response}
