"""Immutable audit log writer.

Records who did what, when, and the before/after state — for every status change,
AI-flag override, and configuration change. Append-only by convention (no update
or delete endpoints are exposed).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    *,
    actor: User | None,
    entity: str,
    action: str,
    entity_id: int | None = None,
    before: dict | None = None,
    after: dict | None = None,
    commit: bool = True,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor.id if actor else None,
        actor_role=actor.role.name if actor and actor.role else "system",
        entity=entity,
        entity_id=entity_id,
        action=action,
        before=before,
        after=after,
    )
    db.add(log)
    if commit:
        db.commit()
    return log
