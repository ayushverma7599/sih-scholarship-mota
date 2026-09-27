"""In-app notifications panel (email/SMS are mocked/logged)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models import Notification, User

router = APIRouter()


@router.get("")
def my_notifications(unread_only: bool = False, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        q = q.filter(Notification.read == False)  # noqa: E712
    items = q.order_by(Notification.created_at.desc()).limit(100).all()
    return {
        "unread": db.query(Notification).filter(
            Notification.user_id == user.id, Notification.read == False).count(),  # noqa: E712
        "items": [
            {"id": n.id, "title": n.title, "message": n.message, "channel": n.channel,
             "read": n.read, "created_at": n.created_at.isoformat()}
            for n in items
        ],
    }


@router.post("/{nid}/read")
def mark_read(nid: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    n = db.get(Notification, nid)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    n.read = True
    db.commit()
    return {"id": n.id, "read": True}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    (db.query(Notification).filter(Notification.user_id == user.id,
                                   Notification.read == False)  # noqa: E712
     .update({Notification.read: True}))
    db.commit()
    return {"ok": True}
