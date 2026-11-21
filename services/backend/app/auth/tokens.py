"""Session tokens: JWT HS256 signed with JWT_SECRET, carried in the `iw_session` cookie."""

from __future__ import annotations

import logging
import secrets
import threading
import time
import uuid
from typing import Any

import jwt

from app.config import Settings, get_settings

log = logging.getLogger(__name__)

COOKIE_NAME = "iw_session"
ALGORITHM = "HS256"
_PLACEHOLDER_MARKERS = ("change-me", "changeme", "change_me", "placeholder", "example", "your-secret")
_PLACEHOLDER_VALUES = {"secret", "password", "jwt-secret", "jwt_secret", "test", "dev"}

_secret: str | None = None
_lock = threading.Lock()
_revoked: dict[str, float] = {}  # jti -> exp (logout, this process only)


class AuthConfigError(RuntimeError):
    """The service must not start with this configuration."""


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or lowered in _PLACEHOLDER_VALUES or any(m in lowered for m in _PLACEHOLDER_MARKERS)


def resolve_secret(settings: Settings | None = None) -> str:
    """Production: a real secret (>= 32 chars) is mandatory. Otherwise a placeholder is only
    tolerated with DEMO_LOGIN=true, and then replaced by a random per-process secret."""
    settings = settings or get_settings()
    value = settings.jwt_secret.strip()
    if settings.app_env == "production":
        if is_placeholder(value) or len(value) < 32:
            raise AuthConfigError("JWT_SECRET must be set to a random value of at least 32 characters")
        return value
    if is_placeholder(value):
        if not settings.demo_login:
            raise AuthConfigError(
                "JWT_SECRET is empty or a placeholder (set it, or DEMO_LOGIN=true for a demo)"
            )
        log.warning("JWT_SECRET not set: using a random secret, sessions end when the backend restarts")
        return secrets.token_urlsafe(48)
    if len(value) < 32:
        log.warning("JWT_SECRET is shorter than 32 characters")
    return value


def get_secret() -> str:
    global _secret
    if _secret is None:
        with _lock:
            if _secret is None:
                _secret = resolve_secret()
    return _secret


def reset_secret() -> None:
    global _secret
    _secret = None
    _revoked.clear()


def issue(user_id: str, email: str, role: str) -> tuple[str, int]:
    """Returns (token, max_age_seconds)."""
    max_age = max(60, int(get_settings().jwt_expire_hours * 3600))
    now = int(time.time())
    claims = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + max_age,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, get_secret(), algorithm=ALGORITHM), max_age


def decode(token: str | None) -> dict[str, Any] | None:
    """Claims of a valid, unexpired, not logged-out token; None otherwise. Never raises."""
    if not token or len(token) > 4096:
        return None
    try:
        claims = jwt.decode(
            token, get_secret(), algorithms=[ALGORITHM], options={"require": ["sub", "exp", "iat", "jti"]}
        )
    except jwt.PyJWTError:
        return None
    if claims.get("jti") in _revoked:
        return None
    return claims


def revoke(claims: dict[str, Any]) -> None:
    now = time.time()
    for jti, exp in list(_revoked.items()):
        if exp < now:
            _revoked.pop(jti, None)
    _revoked[str(claims.get("jti"))] = float(claims.get("exp") or now)


def cookie_from_header(header: str | None) -> str | None:
    """`iw_session` from a raw Cookie header (Socket.IO handshake)."""
    from http.cookies import CookieError, SimpleCookie

    if not header:
        return None
    jar = SimpleCookie()
    try:
        jar.load(header)
    except CookieError:
        return None
    morsel = jar.get(COOKIE_NAME)
    return morsel.value if morsel else None
