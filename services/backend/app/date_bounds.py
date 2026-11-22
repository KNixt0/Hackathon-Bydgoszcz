"""Date filters reach only from the system start date to the present moment (ported from #33).

A date in the future, or an end date before the system existed, cannot match anything real, so it
is rejected with a plain message instead of silently returning an empty list. A start date before
the system existed simply means "from the beginning": the quick ranges (7 / 30 days) send one.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.config import get_settings
from app.models import utcnow

WARSAW = ZoneInfo("Europe/Warsaw")


def window() -> dict:
    start = get_settings().system_start
    return {
        "earliest": start.isoformat().replace("+00:00", "Z"),
        "latest": utcnow().isoformat().replace("+00:00", "Z"),
        "timezone": "Europe/Warsaw",
    }


def check_bound(value: str | None, moment: datetime | None, *, lower: bool) -> None:
    """422 when a parsed bound lies after now, or when an upper bound (`to`) lies before the start."""
    if not value or moment is None:
        return
    start, now = get_settings().system_start, utcnow()
    if len(value) <= 10:  # a bare day: compare calendar days in Polish time
        day = datetime.fromisoformat(value).date()
        valid = (lower or start.astimezone(WARSAW).date() <= day) and day <= now.astimezone(WARSAW).date()
    else:
        valid = (lower or start <= moment) and moment <= now
    if not valid:
        first = start.astimezone(WARSAW).strftime("%d.%m.%Y %H:%M")
        raise HTTPException(422, f"Wybierz datę od uruchomienia systemu ({first}) do bieżącej chwili.")
