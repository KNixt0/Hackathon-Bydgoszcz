"""Socket.IO: the API hosts the server; every process emits through a Valkey-backed manager.

With REDIS_URL set, the API uses AsyncRedisManager (listens + fans out) and any process (API
request threads, Celery workers) publishes through a write-only RedisManager. Without Valkey
(local dev) events are emitted directly on the in-process server.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import socketio

from app.config import get_settings

log = logging.getLogger(__name__)

_sio: socketio.AsyncServer | None = None
_loop: asyncio.AbstractEventLoop | None = None
_writer: Any = None


def create_server() -> socketio.AsyncServer:
    """Called once by the API process."""
    global _sio
    settings = get_settings()
    manager = socketio.AsyncRedisManager(settings.redis_url) if settings.redis_url else None
    origins = settings.cors_origin_list
    _sio = socketio.AsyncServer(
        async_mode="asgi",
        client_manager=manager,
        # None = engine.io default: same origin only (honours X-Forwarded-Host/Proto from nginx)
        cors_allowed_origins=("*" if origins == ["*"] else origins) if origins else None,
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
