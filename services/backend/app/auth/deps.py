"""FastAPI dependencies: the app-wide session guard and the current user."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.auth.tokens import COOKIE_NAME, decode
from app.db import session_scope
from app.models import User

# /fixtures/* (scraper origin) and everything outside /api are not guarded either.
PUBLIC_PREFIXES = ("/api/auth/", "/api/public/")
PUBLIC_PATHS = {"/api/health"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class Principal:
    id: str
    email: str
    name: str
    role: str

    @property
    def is_supervisor(self) -> bool:
        return self.role == "SUPERVISOR"

    def as_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "name": self.name, "role": self.role}


def is_public(path: str) -> bool:
    return not path.startswith("/api/") or path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def resolve_user(request: Request) -> Principal | None:
    """The user behind the request's cookie (cached on request.state), or None."""
    if hasattr(request.state, "principal"):
        return request.state.principal
    principal = None
    claims = decode(request.cookies.get(COOKIE_NAME))
    if claims is not None:
        with session_scope() as db:
            user = db.get(User, str(claims["sub"]))
            if user is not None and user.role == claims.get("role"):
                principal = Principal(user.id, user.email, user.name, user.role)
    request.state.principal = principal
    request.state.claims = claims if principal else None
    return principal


def _same_origin(request: Request) -> bool:
    """Defence in depth next to SameSite=Strict: a browser's cross-site write is refused."""
    from app.events import origin_allowed

    origin = request.headers.get("origin")
    environ = {
        "HTTP_HOST": request.headers.get("host"),
        "HTTP_X_FORWARDED_HOST": request.headers.get("x-forwarded-host"),
    }
    return origin_allowed(origin, environ)


def session_guard(request: Request) -> None:
    """App-level dependency: every /api route needs a session unless it is public."""
    if request.method not in SAFE_METHODS and not _same_origin(request):
        raise HTTPException(403, "cross-origin request refused")
    if is_public(request.url.path):
        return
    if resolve_user(request) is None:
        raise HTTPException(401, "authentication required")


def current_user(request: Request) -> Principal:
    principal = resolve_user(request)
    if principal is None:
        raise HTTPException(401, "authentication required")
    return principal


def require_supervisor(user: Annotated[Principal, Depends(current_user)]) -> Principal:
    if not user.is_supervisor:
        raise HTTPException(403, "supervisor role required")
    return user


Actor = Annotated[Principal, Depends(current_user)]
Supervisor = Annotated[Principal, Depends(require_supervisor)]
