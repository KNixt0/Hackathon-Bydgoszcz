"""Date filters reach only from the system start date to the present moment (ported from #33).

A date before the system existed or in the future cannot match anything real, so it is rejected
with a plain message instead of silently returning an empty list.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.config import get_settings
from app.models import utcnow

WARSAW = ZoneInfo("Europe/Warsaw")
CLOCK_SKEW = timedelta(minutes=2)  # a browser clock slightly ahead of the server is not "the future"


def window() -> dict:
    start = get_settings().system_start
    return {
        "earliest": start.isoformat().replace("+00:00", "Z"),
        "latest": utcnow().isoformat().replace("+00:00", "Z"),
        "timezone": "Europe/Warsaw",
    }


def check_bound(value: str | None, moment: datetime | None) -> None:
    """422 when a parsed `from` / `to` lies before the system start or after now."""
    if not value or moment is None:
        return
    start, now = get_settings().system_start, utcnow()
    if len(value) <= 10:  # a bare day: compare calendar days in Polish time
        day = datetime.fromisoformat(value).date()
        valid = start.astimezone(WARSAW).date() <= day <= now.astimezone(WARSAW).date()
    else:
        valid = start <= moment <= now + CLOCK_SKEW
    if not valid:
        first = start.astimezone(WARSAW).strftime("%d.%m.%Y")
        raise HTTPException(422, f"Wybierz datę od uruchomienia systemu ({first}) do bieżącej chwili.")
