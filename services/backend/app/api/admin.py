"""Global settings (thresholds) and the audit log (contract v3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Text, cast
from sqlalchemy.orm import Session

from app import audit, events
from app.auth import Supervisor
from app.db import get_db
from app.models import AuditLog, Notification, User
from app.monitoring import monitoring_start, validate_bound
from app.schemas import ThresholdsRequest
from app.thresholds import get_thresholds, set_thresholds

router = APIRouter(prefix="/api", tags=["settings"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/settings/thresholds")
def read_thresholds(db: Db) -> dict:
    return get_thresholds(db)


@router.put("/settings/thresholds")
def write_thresholds(body: ThresholdsRequest, db: Db, user: Supervisor) -> dict:
    if body.flag > body.critical:
        raise HTTPException(422, "flag must not be higher than critical")
    before = get_thresholds(db)
    set_thresholds(db, body.flag, body.critical, user.email)
    after = get_thresholds(db)
    audit.record(
        db,
        user,
        "thresholds",
        previous={"flag": before["flag"], "critical": before["critical"]},
        new={"flag": after["flag"], "critical": after["critical"]},
    )
    if (before["flag"], before["critical"]) != (after["flag"], after["critical"]):
        for recipient in db.query(User).all():
            db.add(
                Notification(
                    user_id=recipient.id,
                    message=(
                        f"{user.name} zmienił(a) kalibrację: próg oznaczenia "
                        f"{before['flag']} → {after['flag']}, próg krytyczny "
                        f"{before['critical']} → {after['critical']}."
                    ),
                    details={"actor": user.email, "previous": before, "new": after},
                )
            )
    db.commit()
    events.emit("settings:thresholds", after)
    return after


@router.get("/audit")
def audit_log(
    db: Db,
    _: Supervisor,
    incident_id: Annotated[str | None, Query(max_length=36)] = None,
    actor: Annotated[str | None, Query(max_length=255)] = None,
    action: Annotated[str | None, Query(max_length=32)] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
    from_: Annotated[str | None, Query(alias="from", max_length=40)] = None,
    to: Annotated[str | None, Query(max_length=40)] = None,
    sort: Annotated[str, Query(max_length=32)] = "at",
    order: Annotated[str, Query(max_length=4)] = "desc",
) -> dict:
    """Newest first. There is deliberately no endpoint that updates or deletes audit rows."""
    columns = {
        "at": AuditLog.at,
        "actor": AuditLog.actor_email,
        "action": AuditLog.action,
        "incident_id": AuditLog.incident_id,
        "reason": AuditLog.reason,
        "details": cast(AuditLog.new, Text),
    }
    if sort not in columns or order not in ("asc", "desc"):
        raise HTTPException(422, "Nieprawidłowe sortowanie.")
    from app.api.incidents import _parse_bound

    start = monitoring_start(db)
    validate_bound(from_, "od", start)
    validate_bound(to, "do", start)
    lower, upper = _parse_bound(from_, "od", False), _parse_bound(to, "do", True)
    query = db.query(AuditLog)
    if lower:
        query = query.filter(AuditLog.at >= lower)
    if upper:
        query = query.filter(AuditLog.at < upper)
    if incident_id:
        query = query.filter(AuditLog.incident_id == incident_id)
    if actor:
        query = query.filter(AuditLog.actor_email == actor.strip().lower())
    if action and action not in audit.ACTIONS:
        raise HTTPException(422, "Nieznane zdarzenie.")
    if action:
        query = query.filter(AuditLog.action == action)
    total = query.count()
    column = columns[sort]
    ordered = column.asc().nulls_last() if order == "asc" else column.desc().nulls_last()
    rows = query.order_by(ordered, AuditLog.id.desc()).offset(offset).limit(limit).all()
    return {"items": [audit.entry_dict(row) for row in rows], "total": total}
