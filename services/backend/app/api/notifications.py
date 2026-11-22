"""Durable calibration notifications, with independent read state for each user."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import Actor
from app.db import get_db
from app.models import Notification, utcnow
from app.schemas import iso

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
Db = Annotated[Session, Depends(get_db)]


@router.get("")
def notifications(db: Db, user: Actor) -> dict:
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(100)
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "created_at": iso(row.created_at),
                "read_at": iso(row.read_at),
                "message": row.message,
                "details": row.details,
            }
            for row in rows
        ]
    }


@router.post("/{notification_id}/read")
def read_notification(notification_id: int, db: Db, user: Actor) -> dict:
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Nie znaleziono powiadomienia.")
    row.read_at = row.read_at or utcnow()
    return {"id": row.id, "read_at": iso(row.read_at)}
