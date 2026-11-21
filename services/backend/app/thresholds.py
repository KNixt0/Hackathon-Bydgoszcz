"""Global risk thresholds (contract v3 settings). `critical` is also the server's alert:high threshold."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import session_scope
from app.models import AppSetting
from app.schemas import iso

KEY = "thresholds"
DEFAULT_FLAG = 20.0


def _number(value: object, default: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if 0 <= number <= 100 else default


def _clean(number: float) -> float | int:
    return int(number) if float(number).is_integer() else number


def get_thresholds(db: Session) -> dict:
    row = db.get(AppSetting, KEY)
    critical_default = get_settings().alert_threshold
    value = row.value if row is not None and isinstance(row.value, dict) else {}
    critical = _number(value.get("critical"), critical_default)
    flag = min(_number(value.get("flag"), DEFAULT_FLAG), critical)
    return {
        "flag": _clean(flag),
        "critical": _clean(critical),
        "updated_by": row.updated_by if row is not None else None,
        "updated_at": iso(row.updated_at) if row is not None else None,
    }


def set_thresholds(db: Session, flag: float, critical: float, actor_email: str) -> AppSetting:
    from app.models import utcnow

    row = db.get(AppSetting, KEY)
    if row is None:
        row = AppSetting(key=KEY)
        db.add(row)
    row.value = {"flag": flag, "critical": critical}
    row.updated_by = actor_email
    row.updated_at = utcnow()
    db.flush()
    return row


def alert_threshold() -> float:
    """Read on every stored incident (workers are separate processes, so no in-memory cache)."""
    try:
        with session_scope() as db:
            return float(get_thresholds(db)["critical"])
    except Exception:  # noqa: BLE001 (never fail a scan over a settings read)
        return get_settings().alert_threshold
