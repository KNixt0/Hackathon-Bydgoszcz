"""The monitoring window is anchored once, in Warsaw time, rather than moving every day."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AppSetting, Incident, utcnow
from app.schemas import iso

WARSAW = ZoneInfo("Europe/Warsaw")
KEY = "monitoring_started_at"


def aware(moment: datetime) -> datetime:
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment


def monitoring_start(db: Session) -> datetime:
    setting = db.get(AppSetting, KEY)
    if setting is not None:
        return datetime.fromisoformat(setting.value["at"])
    # Synthetic samples may be backdated; they must not set the real system's start date.
    first = (
        db.query(func.min(Incident.created_at))
        .filter(Incident.synthetic.is_(False), Incident.origin != "sample")
        .scalar()
    )
    anchor = aware(first or utcnow()).astimezone(WARSAW)
    start = datetime.combine(anchor.date(), time(20, 50), tzinfo=WARSAW)
    if start > anchor:
        start -= timedelta(days=1)
    start = start.astimezone(UTC)
    # The nested transaction also handles two API processes initialising concurrently.
    from sqlalchemy.exc import IntegrityError

    try:
        with db.begin_nested():
            db.add(AppSetting(key=KEY, value={"at": start.isoformat()}))
            db.flush()
    except IntegrityError:
        setting = db.get(AppSetting, KEY)
        if setting is not None:
            return datetime.fromisoformat(setting.value["at"])
    return start


def date_bounds(db: Session) -> dict:
    return {"earliest": iso(monitoring_start(db)), "latest": iso(utcnow()), "timezone": "Europe/Warsaw"}


def validate_bound(value: str | None, name: str, start: datetime) -> None:
    if not value:
        return
    try:
        if len(value) <= 10:
            day = datetime.fromisoformat(value).date()
            valid = start.astimezone(WARSAW).date() <= day <= utcnow().astimezone(WARSAW).date()
        else:
            moment = aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
            valid = start <= moment <= utcnow()
    except ValueError as exc:
        raise HTTPException(422, f"Nieprawidłowa data: {name}") from exc
    if not valid:
        raise HTTPException(422, "Wybierz datę od rozpoczęcia monitorowania do bieżącej chwili.")
