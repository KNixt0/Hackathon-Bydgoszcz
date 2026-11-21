"""Public endpoints (no session): citizen reports."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import events
from app.api.auth import client_ip
from app.config import get_settings
from app.db import get_db
from app.incidents import to_summary, url_hash
from app.jobs import create_job, dispatch
from app.models import UserReport, utcnow
from app.public_reports import (
    DAY_SECONDS,
    InvalidReportURL,
    active_pending_job,
    crossed_viral,
    find_incident,
    normalize_url,
    queued_report_scans,
    report_throttle,
    reporter_hash,
    set_count,
)
from app.schemas import PublicReportRequest
from app.scraper import BlockedURL, check_url
from app.thresholds import alert_threshold

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/public", tags=["public"])
Db = Annotated[Session, Depends(get_db)]
QUEUE_RETRY_AFTER = 300


@router.post("/reports", status_code=202)
def create_report(body: PublicReportRequest, request: Request, db: Db) -> dict:
    reporter = reporter_hash(client_ip(request))
    wait = report_throttle.hit(reporter)
    if wait:
        raise HTTPException(429, "too many reports, try again later", headers={"Retry-After": str(wait)})
    try:
        normalized = normalize_url(body.url)
    except InvalidReportURL as exc:
        raise HTTPException(422, f"url: {exc}") from exc
    if len(normalized) > 2048:
        raise HTTPException(422, "url: too long")
    hash_ = url_hash(normalized)
    existing = find_incident(db, hash_)
    known = existing is not None

    since = utcnow() - timedelta(seconds=DAY_SECONDS)
    if (
        db.query(UserReport.id)
        .filter(
            UserReport.reporter_hash == reporter, UserReport.url_hash == hash_, UserReport.created_at >= since
        )
        .first()
    ):  # repeat within 24 h: same answer, not counted
        return {"status": "accepted", "known": known}

    report = UserReport(
        url=body.url,
        normalized_url=normalized,
        url_hash=hash_,
        category_hint=body.category_hint,
        comment=body.comment or None,
        reporter_hash=reporter,
        source="user_report",
    )

    if existing is not None:
        report.incident_id = existing.id
        db.add(report)
        old = existing.user_reports_count or 0
        set_count(db, existing, old + 1)
        db.commit()
        summary = to_summary(existing)
        events.emit("incident:updated", summary)
        if crossed_viral(old, old + 1) and summary["risk_score"] >= alert_threshold():
            events.emit("alert:viral", summary)
        return {"status": "accepted", "known": True}

    job_id = active_pending_job(db, hash_)
    new_job = job_id is None
    if new_job:
        try:
            check_url(normalized)
        except BlockedURL as exc:
            raise HTTPException(422, "url: this address cannot be checked") from exc
        if queued_report_scans(db) >= get_settings().public_reports_max_queued:
            raise HTTPException(
                429,
                "the report queue is full, try again later",
                headers={"Retry-After": str(QUEUE_RETRY_AFTER)},
            )
        job_id = create_job(normalized, module_hint=body.category_hint)
    report.job_id = job_id
    db.add(report)
    db.commit()
    db.close()  # eager/thread queues run the scan right away and need the report to be visible
    if new_job:
        dispatch(job_id)
    return {"status": "accepted", "known": False}
