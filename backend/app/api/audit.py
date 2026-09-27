"""Immutable audit log viewer (read-only; no update/delete endpoints exist)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_roles
from app.models import AuditLog, Roles, User

router = APIRouter()


@router.get("")
def list_audit(
    entity: str | None = None,
    action: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Roles.ADMIN)),
):
    q = db.query(AuditLog)
    if entity:
        q = q.filter(AuditLog.entity == entity)
    if action:
        q = q.filter(AuditLog.action == action)
    logs = q.order_by(AuditLog.at.desc()).limit(min(limit, 1000)).all()
    return [
        {
            "id": l.id, "actor_id": l.actor_id, "actor_role": l.actor_role,
            "entity": l.entity, "entity_id": l.entity_id, "action": l.action,
            "before": l.before, "after": l.after, "at": l.at.isoformat(),
        }
        for l in logs
    ]
