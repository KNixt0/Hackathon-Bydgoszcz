"""ASGI entrypoint: `uvicorn app.main:app` (FastAPI + Socket.IO at /socket.io)."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import socketio
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__, events
from app.api import admin, auth, discovery, incidents, public, scans, system
from app.auth import session_guard
from app.auth.socket import SocketAuthGate
from app.auth.tokens import get_secret
from app.auth.users import seed_users
from app.config import get_settings
from app.db import init_db
from app.log import setup_logging

log = logging.getLogger(__name__)


def _seed() -> None:
    from app.discovery import register_fixture_source
    from app.seed import seed_if_empty

    try:
        register_fixture_source()
        seed_if_empty()
    except Exception:  # noqa: BLE001
        log.exception("startup seed failed")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.log_level)
    get_secret()  # refuses to start without a usable JWT_SECRET (see app.auth.tokens)
    await asyncio.to_thread(init_db)
    await asyncio.to_thread(seed_users)
    events.bind_loop(asyncio.get_running_loop())
    if settings.seed_on_start:
        # after startup: the pipeline fetches the samples from this very server
        timer = threading.Timer(1.0, _seed)
        timer.daemon = True
        timer.start()
    log.info("backend started", extra={"version": __version__, "task_mode": settings.task_mode})
    yield


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for error in exc.errors()[:5]:
        location = ".".join(str(p) for p in error.get("loc", ()) if p not in ("body", "query", "path"))
        parts.append(
            f"{location}: {error.get('msg', 'invalid')}" if location else str(error.get("msg", "invalid"))
        )
    return "; ".join(parts) or "invalid request"


def create_api() -> FastAPI:
    settings = get_settings()
    # every /api route needs a session except /api/health, /api/auth/*, /api/public/* (app.auth.deps)
    api = FastAPI(
        title="#InvestWatch backend",
        version=__version__,
        lifespan=lifespan,
        dependencies=[Depends(session_guard)],
    )

    if settings.cors_origin_list:  # off by default: the browser reaches us same-origin through nginx
        from fastapi.middleware.cors import CORSMiddleware

        api.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["Content-Type"],
            allow_credentials=True,
        )

    @api.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": _validation_message(exc)}, status_code=422)

    @api.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "error"
        return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=exc.headers)

    @api.exception_handler(SQLAlchemyTimeoutError)
    async def _busy(request: Request, exc: SQLAlchemyTimeoutError) -> JSONResponse:
        # every database connection is busy: shed load quickly instead of queueing until the proxy times out
        log.warning("database pool exhausted", extra={"path": request.url.path})
        return JSONResponse(
            {"detail": "service busy, retry shortly"}, status_code=503, headers={"Retry-After": "2"}
        )

    @api.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error(
            "unhandled error", extra={"path": request.url.path, "error": type(exc).__name__}, exc_info=exc
        )
        return JSONResponse({"detail": "internal server error"}, status_code=500)

    api.include_router(auth.router)
    api.include_router(admin.router)
    api.include_router(public.router)
    api.include_router(incidents.router)
    api.include_router(scans.router)
    api.include_router(discovery.router)
    api.include_router(system.router)
    return api


api = create_api()
sio = events.create_server()
app = SocketAuthGate(socketio.ASGIApp(sio, other_asgi_app=api, socketio_path="socket.io"))
