"""Discovery sources (extra, not in the contract): seed pages searched for new material."""

from __future__ import annotations

import threading
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.discovery import add_source
from app.models import DiscoverySource
from app.schemas import DiscoverySourceRequest, iso
from app.scraper import BlockedURL, check_url

router = APIRouter(prefix="/api/discovery", tags=["discovery"])
Db = Annotated[Session, Depends(get_db)]


def _source_dict(source: DiscoverySource) -> dict:
    return {
        "id": source.id,
        "url": source.url,
        "module_hint": source.module_hint,
        "keywords": source.keywords or [],
        "max_links": source.max_links,
        "render": source.render,
        "created_at": iso(source.created_at),
        "last_run_at": iso(source.last_run_at),
        "last_found": source.last_found,
        "last_error": source.last_error,
    }


@router.get("/sources")
def list_sources(db: Db) -> dict:
    sources = db.query(DiscoverySource).order_by(DiscoverySource.created_at.desc()).all()
    return {"items": [_source_dict(source) for source in sources]}


@router.post("/sources", status_code=201)
def create_source(body: DiscoverySourceRequest) -> dict:
    url = str(body.url)
    try:
        check_url(url)
    except BlockedURL as exc:
        raise HTTPException(422, f"url not allowed: {exc}") from exc
    source = add_source(
        url,
        module_hint=body.module_hint,
        keywords=body.keywords,
        max_links=body.max_links,
        render=body.render,
    )
    return _source_dict(source)


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: str, db: Db) -> None:
    source = db.get(DiscoverySource, source_id) if len(source_id) <= 36 else None
    if source is None:
        raise HTTPException(404, "discovery source not found")
    db.delete(source)


@router.post("/run", status_code=202)
def run_now() -> dict:
    """Run all sources now, in the background (same task as the DISCOVERY_CRON schedule). Progress
    shows up as scan:progress events and in last_run_at / last_found of each source."""
    from app.tasks import run_discovery_task

    mode = get_settings().task_mode
    if mode == "celery":
        run_discovery_task.delay()
    elif mode == "thread":
        threading.Thread(target=run_discovery_task.run, daemon=True, name="discovery").start()
    else:
        run_discovery_task.run()
    return {"status": "queued"}
