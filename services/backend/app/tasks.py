"""Queue tasks."""

from __future__ import annotations

import logging
from datetime import UTC, timedelta

from app.celery_app import celery
from app.config import get_settings
from app.db import session_scope
from app.incidents import rescan_options, url_hash
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
    now = utcnow()
    with session_scope() as db:
        query = db.query(Incident)
        if not get_settings().rescan_samples:  # offline material never changes: skipped unless asked for
            query = query.filter(Incident.synthetic.is_(False), Incident.origin != "sample")
        for row in query.all():
            targets[row.source_url] = rescan_options(row)
        for item in db.query(WatchlistItem).all():
            last = item.last_scanned_at
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            # enhanced monitoring sets a minimum interval; a few minutes of slack absorb cron jitter
            if item.interval_hours and last and now - last < timedelta(hours=item.interval_hours, minutes=-5):
                continue
            if item.url not in targets:
                # a monitored case is fetched exactly like the first time (e.g. a sample's fixture)
                case = db.query(Incident).filter(Incident.source_url_hash == url_hash(item.url)).first()
                targets[item.url] = (
                    rescan_options(case)
                    if case is not None and case.source_url == item.url
                    else {
                        "fetch_url": item.url,
                        "origin": "watchlist",
                        "render": item.render,
                        "module_hint": item.module_hint,
                    }
                )
            item.last_scanned_at = now
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


@celery.task(name="investwatch.run_discovery")
def run_discovery_task() -> dict:
    from app.discovery import run_discovery

    return run_discovery()
