"""User accounts: the two demo accounts are created (or their password updated) from env at start."""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password, unusable_hash, verify_password
from app.auth.tokens import AuthConfigError, is_placeholder
from app.config import get_settings
from app.db import session_scope
from app.models import User

log = logging.getLogger(__name__)

ROLES = ("ANALYST", "SUPERVISOR")
DEMO_NAMES = {"ANALYST": "Analityk (demo)", "SUPERVISOR": "Kierownik zespołu (demo)"}


def normalise_email(email: str) -> str:
    return email.strip().lower()


def user_dict(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


def find_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == normalise_email(email)).first()


def demo_accounts() -> dict[str, tuple[str, str]]:
    """role -> (email, password from env)."""
    settings = get_settings()
    return {
        "ANALYST": (normalise_email(settings.demo_analyst_email), settings.demo_analyst_password),
        "SUPERVISOR": (normalise_email(settings.demo_supervisor_email), settings.demo_supervisor_password),
    }


def seed_users() -> None:
    """Idempotent. An empty password gives an account usable only through POST /api/auth/demo.
    In production a placeholder password is refused."""
    production = get_settings().app_env == "production"
    for role, (email, password) in demo_accounts().items():
        if not email:
            continue
        if password and is_placeholder(password) and production:
            raise AuthConfigError(f"the {role.lower()} demo password is a placeholder")
        try:
            with session_scope() as db:
                user = find_by_email(db, email)
                if user is None:
                    db.add(
                        User(
                            email=email,
                            name=DEMO_NAMES[role],
                            role=role,
                            password_hash=hash_password(password) if password else unusable_hash(),
                        )
                    )
                    log.info("demo account created", extra={"role": role})
                else:
                    user.role = role
                    if password and not verify_password(user.password_hash, password):
                        user.password_hash = hash_password(password)
                        log.info("demo account password updated", extra={"role": role})
        except IntegrityError:  # another API replica created it at the same moment
            continue
