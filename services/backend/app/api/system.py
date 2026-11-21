"""Health, evidence archive, registries and the /fixtures sample origin."""

from __future__ import annotations

import logging
import mimetypes

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from app import ai_client
from app.config import get_settings
from app.registries import local_registry_list
from app.samples import UnsafePath, safe_join, samples_root
from app.storage import get_store, valid_key

log = logging.getLogger(__name__)
router = APIRouter(tags=["system"])

_FIXTURE_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
}
_SAFE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "sandbox; default-src 'none'",
}


def _queue_ok() -> bool:
    settings = get_settings()
    if settings.task_mode != "celery":
        return True  # in-process executor
    if not settings.redis_url:
        return False
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        try:
            return bool(client.ping())
        finally:
            client.close()
    except Exception:  # noqa: BLE001
        return False


@router.get("/api/health")
def health() -> dict:
    ai = ai_client.health()
    try:
        storage = get_store().healthy()
    except Exception:  # noqa: BLE001
        storage = False
    return {
        "status": "ok",
        "ai": {
            "reachable": ai is not None,
            "llm_available": bool(ai and ai.get("llm_available")),
            "model": (ai or {}).get("model"),
        },
        "queue": _queue_ok(),
        "storage": storage,
    }


@router.get("/api/evidence/{key:path}")
def evidence(key: str) -> Response:
    if not valid_key(key):
        raise HTTPException(404, "evidence not found")
    try:
        found = get_store().get(key)
    except Exception as exc:  # noqa: BLE001
        log.warning("evidence read failed", extra={"error": type(exc).__name__})
        raise HTTPException(503, "evidence storage is not available") from exc
    if found is None:
        raise HTTPException(404, "evidence not found")
    data, content_type = found
    # archived pages are untrusted: never serve them as HTML
    media_type = "image/png" if content_type.startswith("image/png") else "text/plain; charset=utf-8"
    return Response(data, media_type=media_type, headers=_SAFE_HEADERS)


@router.get("/api/registries")
def registries() -> dict:
    items = ai_client.registries()
    if items is None:
        items = local_registry_list()
    return {
        "items": [
            {
                "registry": item.get("registry"),
                "label": item.get("label") or item.get("registry"),
                "url": item.get("url") or "",
                "entries": int(item.get("entries") or 0),
                "snapshot_date": item.get("snapshot_date"),
            }
            for item in items
            if isinstance(item, dict)
        ]
    }


@router.get("/fixtures/{path:path}", include_in_schema=False)
def fixture(path: str) -> Response:
    """Read-only sample files; the scraper fetches them over HTTP like any other site."""
    try:
        target = safe_join(samples_root(), path)
    except UnsafePath as exc:
        raise HTTPException(404, "fixture not found") from exc
    if not target.is_file() or any(part.startswith(".") for part in target.relative_to(samples_root()).parts):
        raise HTTPException(404, "fixture not found")
    media_type = _FIXTURE_TYPES.get(target.suffix.lower()) or mimetypes.guess_type(target.name)[0]
    return FileResponse(target, media_type=media_type or "application/octet-stream", headers=_SAFE_HEADERS)
