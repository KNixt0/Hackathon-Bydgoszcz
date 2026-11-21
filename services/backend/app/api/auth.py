"""Authentication endpoints (contract v3): login, demo login, session, logout."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from app import audit
from app.auth.deps import Principal, resolve_user
from app.auth.passwords import hash_password, needs_rehash, verify_password
from app.auth.throttle import throttle
from app.auth.tokens import COOKIE_NAME, issue, revoke
from app.auth.users import demo_accounts, find_by_email, normalise_email, user_dict
from app.config import get_settings
from app.db import session_scope
from app.models import User
from app.schemas import DemoLoginRequest, LoginRequest

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

LOGIN_FAILED = "invalid email or password"


def client_ip(request: Request) -> str:
    # nginx sets X-Real-IP; a client talking to the backend port directly could forge it, which is why
    # the per-e-mail limit does not depend on it
    return (request.headers.get("x-real-ip") or (request.client.host if request.client else "") or "unknown")[
        :64
    ]


def _secure(request: Request) -> bool:
    mode = get_settings().cookie_secure
    if mode != "auto":
        return mode == "true"
    forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    return request.url.scheme == "https" or forwarded == "https"


def _start_session(request: Request, response: Response, user: User, method: str) -> dict:
    token, max_age = issue(user.id, user.email, user.role)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        path="/",
        httponly=True,
        samesite="strict",
        secure=_secure(request),
    )
    with session_scope() as db:
        audit.record(db, user, "login", new={"method": method})
    return {"user": user_dict(user)}


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    email, ip = normalise_email(body.email), client_ip(request)
    wait = throttle.retry_after(email, ip)
    if wait:
        raise HTTPException(
            429, "too many failed login attempts, try again later", headers={"Retry-After": str(wait)}
        )
    with session_scope() as db:
        user = find_by_email(db, email)
        ok = verify_password(
            user.password_hash if user else None, body.password
        )  # same cost for unknown users
        if ok and user is not None and needs_rehash(user.password_hash):
            user.password_hash = hash_password(body.password)
        if ok and user is not None:
            db.expunge(user)
    if not ok or user is None:
        throttle.failure(email, ip)
        log.warning("login failed", extra={"ip": ip})
        raise HTTPException(401, LOGIN_FAILED)
    throttle.success(email)
    return _start_session(request, response, user, "password")


@router.post("/demo")
def demo_login(body: DemoLoginRequest, request: Request, response: Response) -> dict:
    if not get_settings().demo_login:
        raise HTTPException(404, "Not Found")
    email, _ = demo_accounts()[body.role]
    with session_scope() as db:
        user = find_by_email(db, email)
        if user is not None:
            db.expunge(user)
    if user is None or user.role != body.role:
        raise HTTPException(404, "demo account is not available")
    return _start_session(request, response, user, "demo")


@router.get("/config")
def auth_config(request: Request) -> dict:
    """`authenticated` (additive to the contract) lets the UI skip a /me call that would 401."""
    return {"demo_login": get_settings().demo_login, "authenticated": resolve_user(request) is not None}


@router.get("/me")
def me(request: Request) -> dict:
    principal: Principal | None = resolve_user(request)
    if principal is None:
        raise HTTPException(401, "authentication required")
    return {"user": principal.as_dict()}


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    if resolve_user(request) is not None and request.state.claims:
        revoke(request.state.claims)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict", secure=_secure(request))
    return response
