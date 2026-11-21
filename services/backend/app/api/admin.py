"""Global settings (thresholds) and the audit log (contract v3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import audit
from app.auth import Supervisor
from app.db import get_db
from app.models import AuditLog
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
    db.commit()
    return after


@router.get("/audit")
def audit_log(
    db: Db,
    _: Supervisor,
    incident_id: Annotated[str | None, Query(max_length=36)] = None,
    actor: Annotated[str | None, Query(max_length=255)] = None,
    action: Annotated[str | None, Query(max_length=32)] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> dict:
    """Newest first. There is deliberately no endpoint that updates or deletes audit rows."""
    query = db.query(AuditLog)
    if incident_id:
        query = query.filter(AuditLog.incident_id == incident_id)
    if actor:
        query = query.filter(AuditLog.actor_email == actor.strip().lower())
    if action:
        query = query.filter(AuditLog.action == action)
    rows = query.order_by(AuditLog.at.desc(), AuditLog.id.desc()).limit(limit).all()
    return {"items": [audit.entry_dict(row) for row in rows]}
