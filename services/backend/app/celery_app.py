"""Celery application: worker (`celery -A app.celery_app worker`) and beat (`... beat`)."""

from __future__ import annotations

import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging as celery_setup_logging
from celery.signals import worker_init, worker_process_init

from app.config import get_settings
from app.log import setup_logging

log = logging.getLogger(__name__)
settings = get_settings()


def parse_cron(expression: str, default: str) -> crontab:
    """Five-field cron string -> celery crontab; falls back to `default` when invalid."""
    for candidate in (expression, default):
        fields = candidate.split()
        if len(fields) == 5:
            try:
                return crontab(
                    minute=fields[0],
                    hour=fields[1],
                    day_of_month=fields[2],
                    month_of_year=fields[3],
                    day_of_week=fields[4],
                )
            except Exception:  # noqa: BLE001, S110
                pass
        log.warning("invalid cron expression, using default", extra={"expression": candidate})
    raise ValueError("invalid default cron expression")


celery = Celery("investwatch", broker=settings.redis_url or "memory://", backend=settings.redis_url or None)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_ignore_result=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_always_eager=settings.task_mode != "celery",
    task_time_limit=int(settings.ai_timeout_seconds + settings.scrape_timeout_seconds * 4 + 120),
    imports=("app.tasks",),
    beat_schedule={
        "rescan-sources": {
            "task": "investwatch.rescan_sources",
            "schedule": parse_cron(settings.rescan_cron, "0 */6 * * *"),
        },
        "refresh-registries": {
            "task": "investwatch.refresh_registries",
            "schedule": parse_cron(settings.registry_refresh_cron, "30 3 * * *"),
        },
    },
)


@celery_setup_logging.connect
def _logging(**_: object) -> None:
    setup_logging(settings.log_level)


@worker_init.connect
def _worker_init(**_: object) -> None:
    from app.db import init_db

    init_db()


@worker_process_init.connect
def _worker_process_init(**_: object) -> None:
    from app.db import reset_engine

    reset_engine()  # never share connections across fork
