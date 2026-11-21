"""Queue tasks."""

from __future__ import annotations

import logging

from app.celery_app import celery
from app.config import get_settings
from app.db import session_scope
from app.models import Incident, WatchlistItem, utcnow

log = logging.getLogger(__name__)


@celery.task(name="investwatch.scrape", bind=True, max_retries=None)
def scrape(self, job_id: str) -> None:  # type: ignore[no-untyped-def]
    from app.pipeline import process_job

    delay = process_job(job_id)
    if delay is not None:
        raise self.retry(countdown=delay)


def enqueue_rescan() -> list[str]:
    """Queue a re-scan of every stored non-synthetic source and every watchlist url."""
    from app.jobs import create_job, dispatch

    targets: dict[str, dict] = {}
    with session_scope() as db:
        rows = db.query(Incident).filter(Incident.synthetic.is_(False), Incident.origin != "sample").all()
        for row in rows:
            targets[row.source_url] = {
                "fetch_url": row.fetch_url or row.source_url,
                "origin": row.origin,
                "render": row.render,
                "module_hint": row.module_hint,
            }
        for item in db.query(WatchlistItem).all():
            targets.setdefault(
                item.url,
                {
                    "fetch_url": item.url,
                    "origin": "watchlist",
                    "render": item.render,
                    "module_hint": item.module_hint,
                },
            )
            item.last_scanned_at = utcnow()
    job_ids = [create_job(url, **options) for url, options in targets.items()]
    for job_id in job_ids:
        dispatch(job_id)
    log.info("rescan queued", extra={"jobs": len(job_ids)})
    return job_ids


@celery.task(name="investwatch.rescan_sources")
def rescan_sources() -> int:
    return len(enqueue_rescan())


@celery.task(name="investwatch.refresh_registries")
def refresh_registries() -> dict:
    from app.registries import refresh_all

    get_settings()
    return refresh_all()
