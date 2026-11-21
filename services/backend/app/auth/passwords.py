"""argon2id password hashing (argon2-cffi defaults, RFC 9106 low-memory profile)."""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

hasher = PasswordHasher()  # tests swap in cheaper parameters
_dummy: dict[int, str] = {}


def hash_password(password: str) -> str:
    return hasher.hash(password)


def unusable_hash() -> str:
    """For accounts without a configured password (demo login only): nobody knows the input."""
    return hasher.hash(secrets.token_urlsafe(32))


def verify_password(stored_hash: str | None, password: str) -> bool:
    """Constant-ish time: an unknown user is checked against a dummy hash with the same cost."""
    target = stored_hash
    if target is None:
        key = id(hasher)
        if key not in _dummy:
            _dummy[key] = hasher.hash(secrets.token_urlsafe(16))
        target = _dummy[key]
    try:
        ok = hasher.verify(target, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        ok = False
    return ok and stored_hash is not None


def needs_rehash(stored_hash: str) -> bool:
    try:
        return hasher.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return True
