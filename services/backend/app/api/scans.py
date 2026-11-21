"""Scans, sample import, demo trigger and the watchlist."""

from __future__ import annotations

import threading
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, session_scope
from app.incidents import delete_incident, url_hash
from app.jobs import create_job, create_sample_job, dispatch, job_dict
from app.models import Incident, ScanJob, WatchlistItem
from app.samples import UnsafePath, find_demo_case
from app.schemas import DemoTriggerRequest, ImportRequest, ScanRequest, WatchlistRequest, iso
from app.scraper import BlockedURL, check_url
from app.seed import import_samples

router = APIRouter(prefix="/api", tags=["scans"])
Db = Annotated[Session, Depends(get_db)]


def _checked_url(url: str) -> str:
    try:
        check_url(url)
    except BlockedURL as exc:
        raise HTTPException(422, f"url not allowed: {exc}") from exc
    return url


@router.post("/scans", status_code=202)
def create_scan(body: ScanRequest) -> dict:
    url = _checked_url(str(body.url))
    job_id = create_job(url, render=body.render, module_hint=body.module_hint)
    dispatch(job_id)
    return {"job_id": job_id}


@router.get("/scans")
def list_scans(db: Db) -> dict:
    jobs = db.query(ScanJob).order_by(ScanJob.created_at.desc(), ScanJob.id).limit(50).all()
    return {"items": [job_dict(job) for job in jobs]}


@router.post("/samples/import", status_code=202)
def import_samples_endpoint(body: Annotated[ImportRequest | None, Body()] = None) -> dict:
    try:
        job_ids = import_samples(body.path if body else None)
    except UnsafePath as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"job_ids": job_ids}


@router.post("/demo/trigger", status_code=202)
def demo_trigger(body: DemoTriggerRequest) -> dict:
    sample = find_demo_case(body.case)
    if sample is None:
        raise HTTPException(404, f"no sample with demo_case '{body.case}'")
    with session_scope() as db:  # repeatable demo: drop the previous run of this case
        for row in db.query(Incident).filter(Incident.demo_case == body.case).all():
            delete_incident(db, row)
    job_id = create_sample_job(sample, backdate=False)
    dispatch(job_id)
    return {"job_id": job_id}


# ---- watchlist (extra, not in the contract): urls re-scanned by the RESCAN_CRON schedule ----


def _watch_dict(item: WatchlistItem) -> dict:
    return {
        "id": item.id,
        "url": item.url,
        "module_hint": item.module_hint,
        "render": item.render,
        "created_at": iso(item.created_at),
        "last_scanned_at": iso(item.last_scanned_at),
    }


@router.get("/watchlist")
def list_watchlist(db: Db) -> dict:
    items = db.query(WatchlistItem).order_by(WatchlistItem.created_at.desc()).all()
    return {"items": [_watch_dict(item) for item in items]}


@router.post("/watchlist", status_code=201)
def add_watchlist(body: WatchlistRequest, db: Db) -> dict:
    url = _checked_url(str(body.url))
    item = db.query(WatchlistItem).filter(WatchlistItem.url_hash == url_hash(url)).first()
    if item is None:
        item = WatchlistItem(url=url, url_hash=url_hash(url))
        db.add(item)
    item.module_hint, item.render = body.module_hint, body.render
    db.flush()
    return _watch_dict(item)


@router.delete("/watchlist/{item_id}", status_code=204)
def delete_watchlist(item_id: str, db: Db) -> None:
    item = db.get(WatchlistItem, item_id) if len(item_id) <= 36 else None
    if item is None:
        raise HTTPException(404, "watchlist item not found")
    db.delete(item)


@router.post("/watchlist/rescan", status_code=202)
def rescan_now() -> dict:
    """Extra: run the periodic re-scan (RESCAN_CRON) right now."""
    from app.tasks import enqueue_rescan

    return {"job_ids": enqueue_rescan()}


@router.post("/registries/refresh", status_code=202)
def refresh_registries_now() -> dict:
    """Extra: run the KNF register refresh (REGISTRY_REFRESH_CRON) right now, in the background."""
    from app.tasks import refresh_registries

    if get_settings().task_mode == "celery":
        refresh_registries.delay()
    else:
        threading.Thread(target=refresh_registries.run, daemon=True, name="registry-refresh").start()
    return {"status": "queued"}
