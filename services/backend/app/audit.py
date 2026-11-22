"""Append-only audit trail. `record` adds the row to the caller's session, so it commits (or rolls
back) together with the change it describes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, utcnow
from app.schemas import iso

ACTIONS = (
    "login",
    "assign",
    "transition",
    "label",
    "thresholds",
    "calibration_preview",  # WatchIt: a user changed the thresholds for their own view
    "export",
    "rescan",
    "public_report",  # kept so that old audit rows stay valid
)
# what the case page and the PDFs call "decision history"
DECISION_ACTIONS = ("assign", "transition", "label")


def record(
    db: Session,
    actor: Any,
    action: str,
    *,
    incident_id: str | None = None,
    previous: Any = None,
    new: Any = None,
    reason: str | None = None,
) -> AuditLog:
    """`actor` is anything with `email` and `role` (Principal, User)."""
    if action not in ACTIONS:
        raise ValueError(f"unknown audit action {action}")
    entry = AuditLog(
        at=utcnow(),
        actor_email=actor.email,
        actor_role=actor.role,
        action=action,
        incident_id=incident_id,
        previous=previous,
        new=new,
        reason=reason or None,
    )
    db.add(entry)
    return entry


def entry_dict(entry: AuditLog) -> dict:
    return {
        "id": entry.id,
        "at": iso(entry.at),
        "actor_email": entry.actor_email,
        "actor_role": entry.actor_role,
        "action": entry.action,
        "incident_id": entry.incident_id,
        "previous": entry.previous,
        "new": entry.new,
        "reason": entry.reason,
    }


def incident_history(db: Session, incident_id: str, actions: tuple[str, ...] | None = None) -> list[dict]:
    """Oldest first."""
    query = db.query(AuditLog).filter(AuditLog.incident_id == incident_id)
    if actions:
        query = query.filter(AuditLog.action.in_(actions))
    return [entry_dict(e) for e in query.order_by(AuditLog.at, AuditLog.id).all()]
