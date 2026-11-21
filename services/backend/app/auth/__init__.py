"""Local authentication: argon2 password hashes, HS256 session cookie, two roles."""

from app.auth.deps import Actor, Principal, Supervisor, current_user, require_supervisor, session_guard

__all__ = ["Actor", "Principal", "Supervisor", "current_user", "require_supervisor", "session_guard"]
