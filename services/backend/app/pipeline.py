"""The scan pipeline: fetch -> Document -> archive -> AI /analyze -> Incident -> socket events."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError

from app import ai_client, events
from app.config import get_settings
from app.db import session_scope
from app.incidents import level_for, record_unavailable, store_observation, to_summary
from app.jobs import set_state
from app.models import ScanJob, utcnow
from app.public_reports import crossed_viral, link_pending
from app.schemas import PLATFORMS, AnalysisIn
from app.scraper import BlockedURL, FetchedPage, Fetcher, FetchError
from app.scraper.parsers import GENERIC, detect_platform, select_parser
from app.scraper.ssrf import is_fixture_url
from app.scraper.visual_audit import attach_visual
from app.storage import get_store
from app.thresholds import alert_threshold, get_thresholds

log = logging.getLogger(__name__)

_fetcher: Fetcher | None = None


def get_fetcher() -> Fetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = Fetcher()
    return _fetcher


def reset_fetcher() -> None:
    global _fetcher
    _fetcher = None


class _Retry(Exception):
    pass


class _Fail(Exception):
    pass


def build_document(job: ScanJob, page: FetchedPage, fetcher: Fetcher) -> dict[str, Any]:
    """Unified scraper output (`Document` in the API contract)."""
    meta = job.meta or {}
    is_sample = job.origin == "sample"
    html = page.body if page.is_html else ""
    sample_text: str | None = None
    if is_sample and not page.is_html and "json" in page.content_type.lower():
        try:
            sample_text = str(json.loads(page.body).get("text") or "")
        except (ValueError, AttributeError):
            sample_text = ""
        page.body, page.content_type = sample_text, "text/plain; charset=utf-8"  # archive the text itself

    if sample_text is not None:
        title, text, language, published, author = "", sample_text, None, None, None
    else:
        parser = select_parser(job.url) if page.is_html else GENERIC
        parsed = parser.parse(page, aux=None if is_sample else fetcher.get_text)
        title, text, language = parsed.title, parsed.text, parsed.language
        published, author = parsed.published_at, parsed.author

    platform = meta.get("platform") if meta.get("platform") in PLATFORMS else None
    if platform is None:
        platform = "sample" if is_sample and is_fixture_url(job.url) else detect_platform(job.url)
    meta_author = (
        meta.get("author") if isinstance(meta.get("author"), dict) and meta["author"].get("name") else None
    )
    if language is None:
        from app.scraper.extract import guess_language

        language = guess_language(text)

    document: dict[str, Any] = {
        "url": job.url,
        "platform": platform,
        "fetched_at": page.fetched_at,
        "http_status": page.status,
        "title": str(meta.get("title") or title or "")[:500],
        "html": html,
        "text": text,
        "fetch": {"engine": page.engine, "user_agent": page.user_agent, "proxy": page.proxy},
        "archive": {"html_key": None, "screenshot_key": None},
    }
    if language:
        document["language"] = language
    if meta.get("published_at") or published:
        document["published_at"] = str(meta.get("published_at") or published)
    if meta_author or author:
        document["author"] = {
            k: str(v) for k, v in (meta_author or author).items() if k in ("name", "handle", "url") and v
        }
    return document


def _archive(job_id: str, document: dict, page: FetchedPage) -> None:
    store = get_store()
    raw = page.body.encode("utf-8")
    if raw:
        key = f"evidence/{job_id}/page.html" if page.is_html else f"evidence/{job_id}/page.txt"
        store.put(key, raw, "text/html; charset=utf-8" if page.is_html else "text/plain; charset=utf-8")
        document["archive"]["html_key"] = key
    if page.screenshot:
        key = f"evidence/{job_id}/screenshot.png"
        store.put(key, page.screenshot, "image/png")
        document["archive"]["screenshot_key"] = key


def _normalise_analysis(analysis: dict, document: dict, context: dict) -> dict:
    """Validate what the backend relies on and fill backend-owned fields."""
    try:
        AnalysisIn.model_validate(analysis)
    except ValidationError as exc:
        fields = ", ".join(sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()}))[:200]
        raise _Fail(f"AI response does not match the contract ({fields})") from exc
    payload = dict(analysis)
    source = dict(payload.get("source") or {})
    source["archive"] = document["archive"]  # the backend owns storage keys
    source["url"] = source.get("url") or document["url"]
    if source.get("platform") not in PLATFORMS:
        source["platform"] = document["platform"]
    source.setdefault("fetched_at", document["fetched_at"])
    source.setdefault("language", document.get("language") or "")
    source.setdefault("text", document["text"])
    for key in ("final_url", "redirect_chain", "affiliate_params"):  # scraper-owned (contract v3)
        if key in document and key not in source:
            source[key] = document[key]
    if not source.get("content_hash"):
        source["content_hash"] = hashlib.sha256(" ".join(source["text"].split()).encode("utf-8")).hexdigest()
    payload["source"] = source
    score = float(payload["risk_score"])
    payload.setdefault("compliance_score", round(100 - score, 2))
    payload.setdefault("risk_level", level_for(score))
    payload.setdefault("summary", "")
    if not payload.get("modules"):
        payload["modules"] = [payload["primary_module"]]
    for key in ("synthetic", "ground_truth", "demo_case"):
        if key not in payload and key in context:
            payload[key] = context[key]
    payload.setdefault("synthetic", False)
    payload.setdefault("ground_truth", None)
    payload.setdefault("demo_case", None)
    return payload


def detection_time(days_ago: object) -> datetime | None:
    """When a sample is shown as detected. Never before the system existed (SYSTEM_START_DATE).

    Demo samples carry `detected_days_ago` (0-30). While the system is younger than 30 days these are
    scaled into the time since the start, one monotonic mapping for all samples, so the queue keeps its
    order without showing dates the system could not have produced."""
    if not isinstance(days_ago, int | float) or isinstance(days_ago, bool) or not 0 <= days_ago <= 3650:
        return None
    now = utcnow()
    window = now - get_settings().system_start
    if window <= timedelta(0):
        return now
    if window >= timedelta(days=30):
        return now - min(timedelta(days=float(days_ago)), window)
    return now - window * (min(float(days_ago), 30.0) / 30.0)


def _run(job_id: str) -> None:
    with session_scope() as db:
        job = db.get(ScanJob, job_id)
        if job is None or job.state in ("done", "failed"):
            return
        job.attempts += 1
        db.flush()
        db.expunge(job)

    set_state(job_id, "scraping")
    fetcher = get_fetcher()
    is_sample = job.origin == "sample"
    render = job.render or (not is_sample and select_parser(job.url).prefers_render)
    try:
        page = fetcher.fetch(job.fetch_url, render=render)
    except BlockedURL as exc:
        raise _Fail(f"url not allowed: {exc}") from exc
    except FetchError as exc:
        if exc.retryable:
            raise _Retry(str(exc)) from exc
        raise _Fail(str(exc)) from exc
    if page.status >= 400:
        if _observe_unavailable(job, job_id, page.status):
            return
        raise _Fail(f"source answered with http status {page.status}")

    document = build_document(job, page, fetcher)
    if not document["text"].strip():
        raise _Fail("no text could be extracted from the page")
    _archive(job_id, document, page)
    attach_visual(document, page, job_id, fixture=is_fixture_url(page.url), store=get_store())

    set_state(job_id, "analyzing")
    context = dict(job.context or {})
    if job.module_hint and "module_hint" not in context:
        context["module_hint"] = job.module_hint
    try:
        analysis = ai_client.analyze(document, context)
    except ai_client.AIUnavailable as exc:
        raise _Retry(str(exc)) from exc
    except ai_client.AIRejected as exc:
        raise _Fail(str(exc)) from exc
    payload = _normalise_analysis(analysis, document, context)

    created_at = detection_time((job.meta or {}).get("detected_days_ago"))

    with session_scope() as db:
        stored = store_observation(
            db,
            payload,
            created_at=created_at,
            meta=job.meta,
            context=job.context,
            origin=job.origin,
            fetch_url=job.fetch_url,
            render=job.render,
            module_hint=job.module_hint,
            job_id=job_id,
            flag_threshold=float(get_thresholds(db)["flag"]),
        )
        row, created = stored.row, stored.created
        linked = link_pending(db, row, job_id)  # reports that were waiting for this scan
        summary = to_summary(row)
        incident_id = row.id

    set_state(job_id, "done", incident_id=incident_id)
    events.emit("incident:new" if created else "incident:updated", summary)
    critical = alert_threshold()  # global "critical" threshold
    # alert on a detection: a new case, or a known source that only now reaches the threshold
    if (created or stored.detected) and summary["risk_score"] >= critical:
        events.emit("alert:high", summary)
    if linked and crossed_viral(*linked) and summary["risk_score"] >= critical:
        events.emit("alert:viral", summary)
    log.info(
        "incident stored",
        extra={
            "job_id": job_id,
            "incident_id": incident_id,
            "is_new": created,
            "risk_score": summary["risk_score"],
        },
    )


def _observe_unavailable(job: ScanJob, job_id: str, status: int) -> bool:
    """404/410 or another error page from a source that is already a case: record the observation
    (contract v4: `removed` / `unreachable`) and finish the job, instead of failing it."""
    with session_scope() as db:
        row = record_unavailable(db, job.url, status, job_id)
        if row is None:
            return False
        summary, incident_id = to_summary(row), row.id
    set_state(job_id, "done", incident_id=incident_id)
    events.emit("incident:updated", summary)
    log.info(
        "source unavailable", extra={"job_id": job_id, "incident_id": incident_id, "http_status": status}
    )
    return True


def process_job(job_id: str) -> float | None:
    """Run one attempt. Returns None when the job is finished (done or failed), or the number
    of seconds to wait before the next attempt (the job is back in `queued`)."""
    settings = get_settings()
    try:
        _run(job_id)
        return None
    except _Retry as exc:
        with session_scope() as db:
            job = db.get(ScanJob, job_id)
            attempts = job.attempts if job else settings.scan_max_retries + 1
        if attempts <= settings.scan_max_retries:
            set_state(job_id, "queued", error=f"retrying: {exc}")
            return settings.scan_retry_backoff_seconds * (2 ** (attempts - 1))
        message = str(exc)
    except _Fail as exc:
        message = str(exc)
    except Exception as exc:  # noqa: BLE001
        log.exception("scan failed unexpectedly", extra={"job_id": job_id})
        message = f"internal error ({type(exc).__name__})"
    set_state(job_id, "failed", error=message)
    return None
