"""Socket.IO: the API hosts the server; every process emits through a Valkey-backed manager.

With REDIS_URL set, the API uses AsyncRedisManager (listens + fans out) and any process (API
request threads, Celery workers) publishes through a write-only RedisManager. Without Valkey
(local dev) events are emitted directly on the in-process server.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlsplit

import socketio

from app.config import get_settings

log = logging.getLogger(__name__)

_sio: socketio.AsyncServer | None = None
_loop: asyncio.AbstractEventLoop | None = None
_writer: Any = None


def origin_allowed(origin: str | None, environ: dict | None = None) -> bool:
    """Socket.IO origin check: same host as the request (the port is ignored, because nginx behind
    a published port forwards `Host` without it), or an origin listed in CORS_ORIGINS."""
    if not origin:
        return True  # non-browser client
    configured = get_settings().cors_origin_list
    if "*" in configured or origin in configured:
        return True
    origin_host = (urlsplit(origin).hostname or "").lower()
    environ = environ or {}
    for header in ("HTTP_HOST", "HTTP_X_FORWARDED_HOST"):
        for value in str(environ.get(header) or "").split(","):
            host = (urlsplit("//" + value.strip()).hostname or "").lower() if value.strip() else ""
            if host and host == origin_host:
                return True
    return False


def create_server() -> socketio.AsyncServer:
    """Called once by the API process."""
    global _sio
    settings = get_settings()
    manager = socketio.AsyncRedisManager(settings.redis_url) if settings.redis_url else None
    _sio = socketio.AsyncServer(
        async_mode="asgi",
        client_manager=manager,
        cors_allowed_origins=origin_allowed,
        logger=False,
        engineio_logger=False,
    )
    return _sio


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def _get_writer() -> Any:
    global _writer
    if _writer is None:
        _writer = socketio.RedisManager(get_settings().redis_url, write_only=True)
    return _writer


def emit(event: str, payload: dict) -> None:
    """Fire-and-forget emit from sync code. Never raises: a lost UI event must not fail a scan."""
    try:
        if get_settings().redis_url:
            _get_writer().emit(event, payload)
        elif _sio is not None and _loop is not None and _loop.is_running():
            asyncio.run_coroutine_threadsafe(_sio.emit(event, payload), _loop)
    except Exception as exc:  # noqa: BLE001
        log.warning("socket emit failed", extra={"event": event, "error": type(exc).__name__})
