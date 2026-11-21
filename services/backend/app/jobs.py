"""Scan jobs: creation, state changes (with scan:progress) and dispatch to the queue."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app import events
from app.config import get_settings
from app.db import session_scope
from app.models import ScanJob, utcnow
from app.samples import Sample
from app.schemas import iso

log = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None


def job_dict(job: ScanJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "url": job.url,
        "state": job.state,
        "incident_id": job.incident_id,
        "error": job.error,
        "created_at": iso(job.created_at),
        "finished_at": iso(job.finished_at),
    }


def create_job(
    url: str,
    *,
    fetch_url: str | None = None,
    origin: str = "scan",
    render: bool = False,
    module_hint: int | None = None,
    meta: dict | None = None,
    context: dict | None = None,
) -> str:
    """Insert a queued job in its own transaction (so workers can see it) and announce it."""
    with session_scope() as db:
        job = ScanJob(
            url=url,
            fetch_url=fetch_url or url,
            origin=origin,
            render=render,
            module_hint=module_hint,
            meta=meta or {},
            context=context or {},
            state="queued",
        )
        db.add(job)
        db.flush()
        payload = job_dict(job)
    log.info("job state", extra={"job_id": payload["id"], "state": "queued", "origin": origin})
    events.emit("scan:progress", payload)
    return payload["id"]


def create_sample_job(sample: Sample, backdate: bool = True) -> str:
    meta = dict(sample.meta)
    if not backdate:
        meta.pop("detected_days_ago", None)
    hint = sample.context.get("module_hint")
    return create_job(
        sample.url,
        fetch_url=sample.fixture_url,
        origin="sample",
        module_hint=hint if hint in (1, 2, 3) else None,
        meta=meta,
        context=sample.context,
    )


def set_state(job_id: str, state: str, *, error: str | None = None, incident_id: str | None = None) -> None:
    with session_scope() as db:
        job = db.get(ScanJob, job_id)
        if job is None:
            return
        job.state = state
        job.error = error[:500] if error else None
        if incident_id:
            job.incident_id = incident_id
        job.finished_at = utcnow() if state in ("done", "failed") else None
        db.flush()
        payload = job_dict(job)
    log.info(
        "job state",
        extra={"job_id": job_id, "state": state, **({"error": payload["error"]} if error else {})},
    )
    events.emit("scan:progress", payload)


def _run_with_retries(job_id: str, sleep: bool) -> None:
    from app.pipeline import process_job

    try:
        while True:
            delay = process_job(job_id)
            if delay is None:
                return
            if sleep:
                time.sleep(delay)
    except Exception:  # noqa: BLE001
        log.exception("scan job crashed", extra={"job_id": job_id})


def dispatch(job_id: str) -> None:
    mode = get_settings().task_mode
    if mode == "celery":
        from app.tasks import scrape

        scrape.delay(job_id)
    elif mode == "thread":
        global _executor
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="scan")
        _executor.submit(_run_with_retries, job_id, True)
    else:  # eager (tests)
        _run_with_retries(job_id, False)
