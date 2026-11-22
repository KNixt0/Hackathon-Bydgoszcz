"""Global settings (thresholds) and the audit log (contract v3)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.auth import Actor, Supervisor
from app.date_bounds import check_bound
from app.db import get_db
from app.models import AuditLog, Incident, Notification, User
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
        # Ported from #33: a global calibration change reaches every user, each with their own read state.
        message = (
            f"{user.name} zmienił(a) kalibrację: próg oznaczenia {before['flag']} → {after['flag']}, "
            f"próg krytyczny {before['critical']} → {after['critical']}."
        )
        details = {"actor": user.email, "previous": before, "new": after}
        for recipient_id in db.scalars(select(User.id)):
            db.add(Notification(user_id=recipient_id, message=message, details=details))
    db.commit()
    return after


CALIBRATION_ACTIONS = ("thresholds", "calibration_preview")


@router.post("/settings/thresholds/preview", status_code=204)
def record_preview(body: ThresholdsRequest, db: Db, user: Actor) -> Response:
    """WatchIt: any user who changes the thresholds for their own view leaves a trace (who and what).

    Nothing is shown to the user (no toast): the entry appears in the calibration history."""
    if body.flag > body.critical:
        raise HTTPException(422, "flag must not be higher than critical")
    last = (
        db.query(AuditLog)
        .filter(AuditLog.action == "calibration_preview", AuditLog.actor_email == user.email)
        .order_by(AuditLog.at.desc(), AuditLog.id.desc())
        .first()
    )
    previous = last.new if last is not None and isinstance(last.new, dict) else None
    new = {"flag": body.flag, "critical": body.critical}
    if previous != new:
        audit.record(db, user, "calibration_preview", previous=previous, new=new)
        db.commit()
    return Response(status_code=204)


@router.get("/settings/thresholds/history")
def thresholds_history(db: Db, _: Actor, limit: Annotated[int, Query(ge=1, le=500)] = 100) -> dict:
    """Calibration history for every logged-in user: global changes (supervisor) and personal previews."""
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.action.in_(CALIBRATION_ACTIONS))
        .order_by(AuditLog.at.desc(), AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return {"items": [audit.entry_dict(row) for row in rows]}


@router.get("/audit")
def audit_log(
    db: Db,
    user: Actor,
    incident_id: Annotated[str | None, Query(max_length=36)] = None,
    actor: Annotated[str | None, Query(max_length=255)] = None,
    action: Annotated[str | None, Query(max_length=400)] = None,
    role: Annotated[str | None, Query(pattern="^(ANALYST|SUPERVISOR)$")] = None,
    start: Annotated[str | None, Query(alias="from", max_length=40)] = None,
    end: Annotated[str | None, Query(alias="to", max_length=40)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> dict:
    """Newest first. There is deliberately no endpoint that updates or deletes audit rows.

    WatchIt: a supervisor sees every entry; an analyst sees only their own (the actor filter is forced).
    `incident_id` takes the full id or the 8-character case ID shown in the UI; `action` a comma list;
    `from` / `to` ISO dates or datetimes (a bare `to` date covers that whole day); `q` searches reasons."""
    query = db.query(AuditLog)
    if user.role != "SUPERVISOR":
        query = query.filter(AuditLog.actor_email == user.email)
    elif actor:
        query = query.filter(AuditLog.actor_email == actor.strip().lower())
    if incident_id:
        ref = incident_id.strip().lower()
        query = query.filter(
            AuditLog.incident_id == ref
            if len(ref) == 36
            else AuditLog.incident_id.like(f"%{ref.replace('-', '')}")
        )
    if action:
        actions = [a.strip() for a in action.split(",") if a.strip()]
        query = query.filter(AuditLog.action.in_(actions))
    if role:
        query = query.filter(AuditLog.actor_role == role)
    if start:
        query = query.filter(AuditLog.at >= _bound(start, end_of_day=False))
    if end:
        query = query.filter(AuditLog.at <= _bound(end, end_of_day=True))
    if q and q.strip():
        query = query.filter(AuditLog.reason.ilike(f"%{q.strip()}%"))
    rows = query.order_by(AuditLog.at.desc(), AuditLog.id.desc()).limit(limit).all()
    titles = dict(
        db.query(Incident.id, Incident.payload["title"].as_string())
        .filter(Incident.id.in_({r.incident_id for r in rows if r.incident_id}))
        .all()
    )
    return {
        "items": [{**audit.entry_dict(row), "incident_title": titles.get(row.incident_id)} for row in rows]
    }


def _bound(value: str, end_of_day: bool) -> datetime:
    try:
        if len(value) == 10:
            day = date.fromisoformat(value)
            check_bound(value, datetime.combine(day, time.min, tzinfo=UTC), lower=not end_of_day)
            return datetime.combine(day, time.max if end_of_day else time.min, tzinfo=UTC)
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        moment = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    except ValueError as exc:
        raise HTTPException(422, "from / to must be ISO dates") from exc
    check_bound(value, moment, lower=not end_of_day)
    return moment
