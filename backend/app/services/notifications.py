"""Notification service.

In-app notifications are persisted. Email/SMS are MOCKED — messages are logged to
the console and stored so the demo can show the audit trail without real gateways.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import Notification

logger = logging.getLogger("notifications")


def notify(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    channels: tuple[str, ...] = ("in_app",),
    commit: bool = True,
) -> list[Notification]:
    created = []
    for channel in channels:
        n = Notification(user_id=user_id, channel=channel, title=title, message=message)
        db.add(n)
        created.append(n)
        if channel in ("email", "sms"):
            logger.info("[MOCK %s] to user %s | %s: %s", channel.upper(), user_id, title, message)
    if commit:
        db.commit()
    return created
