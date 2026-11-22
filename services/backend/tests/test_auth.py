"""Authentication (contract v3): login, cookie, throttle, demo login, the session guard, Socket.IO."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.auth import tokens
from app.auth.tokens import AuthConfigError, resolve_secret
from app.config import Settings, get_settings
from app.main import api
from tests.conftest import ANALYST, SUPERVISOR

PUBLIC = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/demo",
    "/api/auth/config",
    "/api/auth/me",
    "/api/auth/logout",
}


def set_cookie(response) -> str:
    return response.headers["set-cookie"]


def test_login_success_user_and_cookie_flags(anon):
    response = anon.post(
        "/api/auth/login", json={"email": " Kierownik@UKNF.local ", "password": SUPERVISOR[1]}
    )
    assert response.status_code == 200
    user = response.json()["user"]
    assert set(user) == {"id", "email", "name", "role"}
    assert user["email"] == SUPERVISOR[0] and user["role"] == "SUPERVISOR"
    cookie = set_cookie(response)
    assert cookie.startswith("iw_session=")
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
    assert "Max-Age=28800" in cookie
    assert "Secure" not in cookie  # plain http in tests
    assert anon.get("/api/auth/me").json() == {"user": user}
    assert anon.get("/api/auth/config").json() == {"demo_login": True, "authenticated": True}


def test_cookie_secure_on_https_and_override(client, monkeypatch):
    https = TestClient(api, base_url="https://testserver")
    response = https.post("/api/auth/login", json={"email": ANALYST[0], "password": ANALYST[1]})
    assert "Secure" in set_cookie(response)
    proxied = TestClient(api).post(
        "/api/auth/login",
        json={"email": ANALYST[0], "password": ANALYST[1]},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert "Secure" in set_cookie(proxied)
    monkeypatch.setattr(get_settings(), "cookie_secure", "true")
    forced = TestClient(api).post("/api/auth/login", json={"email": ANALYST[0], "password": ANALYST[1]})
    assert "Secure" in set_cookie(forced)


def test_login_failure_is_uniform(anon):
    wrong = anon.post("/api/auth/login", json={"email": ANALYST[0], "password": "nope"})
    unknown = anon.post("/api/auth/login", json={"email": "ghost@uknf.local", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "invalid email or password"}
    assert "set-cookie" not in wrong.headers
    assert anon.get("/api/auth/me").status_code == 401
    assert anon.get("/api/auth/config").json() == {"demo_login": True, "authenticated": False}
    for body in (
        {},
        {"email": ANALYST[0]},
        {"email": "", "password": "x"},
        {"email": "a", "password": "b", "x": 1},
    ):
        assert anon.post("/api/auth/login", json=body).status_code == 422


def test_login_throttle_per_email_and_reset_on_success(anon, monkeypatch):
    for _ in range(5):
        assert anon.post("/api/auth/login", json={"email": ANALYST[0], "password": "bad"}).status_code == 401
    blocked = anon.post("/api/auth/login", json={"email": ANALYST[0], "password": ANALYST[1]})
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0
    # another account from the same address is still allowed
    assert (
        anon.post("/api/auth/login", json={"email": SUPERVISOR[0], "password": SUPERVISOR[1]}).status_code
        == 200
    )


def test_login_throttle_per_ip(anon, monkeypatch):
    monkeypatch.setattr(get_settings(), "login_max_failures_per_ip", 3)
    for n in range(3):
        anon.post("/api/auth/login", json={"email": f"x{n}@uknf.local", "password": "bad"})
    assert anon.post("/api/auth/login", json={"email": "y@uknf.local", "password": "bad"}).status_code == 429
    other_ip = {"X-Real-IP": "10.9.9.9"}
    response = anon.post(
        "/api/auth/login", json={"email": ANALYST[0], "password": ANALYST[1]}, headers=other_ip
    )
    assert response.status_code == 200


def test_demo_login_on_and_off(anon, monkeypatch):
    response = anon.post("/api/auth/demo", json={"role": "ANALYST"})
    assert response.status_code == 200 and response.json()["user"]["email"] == ANALYST[0]
    assert anon.get("/api/auth/me").json()["user"]["role"] == "ANALYST"
    assert anon.post("/api/auth/demo", json={"role": "ADMIN"}).status_code == 422
    monkeypatch.setattr(get_settings(), "demo_login", False)
    assert anon.get("/api/auth/config").json()["demo_login"] is False
    off = TestClient(api).post("/api/auth/demo", json={"role": "SUPERVISOR"})
    assert off.status_code == 404 and "set-cookie" not in off.headers


def test_logout_clears_cookie_and_revokes_token(client):
    token = client.cookies["iw_session"]
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    assert 'iw_session=""' in set_cookie(response) or "Max-Age=0" in set_cookie(response)
    replay = TestClient(api, cookies={"iw_session": token})
    assert replay.get("/api/incidents").status_code == 401  # the old token no longer works


def test_login_is_audited(client):
    entries = client.get("/api/audit").json()["items"]
    logins = [e for e in entries if e["action"] == "login"]
    assert logins[0]["actor_email"] == SUPERVISOR[0] and logins[0]["new"] == {"method": "password"}


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", path)


def protected_routes() -> list[tuple[str, str]]:
    """Every documented /api operation (routers are mounted lazily, so read the OpenAPI schema)."""
    found = []
    for path, operations in api.openapi()["paths"].items():
        if path.startswith("/api/") and path not in PUBLIC and not path.startswith("/api/public/"):
            found.extend((method.upper(), _concrete(path)) for method in sorted(operations))
    return found


def test_route_inventory_is_complete():
    paths = {path for _, path in protected_routes()}
    for expected in (
        "/api/incidents",
        "/api/audit",
        "/api/settings/thresholds",
        "/api/incidents/x/transition",
        "/api/incidents/x/history",
        "/api/incidents/x/versions/x",
        "/api/evidence/x",
        "/api/calibration",
        "/api/scans",
        "/api/watchlist",
        "/api/discovery/sources",
    ):
        assert expected in paths, expected


@pytest.mark.parametrize(("method", "path"), protected_routes())
def test_every_protected_route_needs_a_session(anon, method, path):
    response = anon.request(method, path, json={})
    assert response.status_code == 401, (method, path, response.status_code)
    assert response.json() == {"detail": "authentication required"}


def test_public_routes_stay_open(anon, samples_dir):
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/api/auth/config").status_code == 200
    assert anon.get("/fixtures/green.html").status_code == 200  # the scraper's sample origin
    assert anon.get("/api/public/anything").status_code == 404  # not guarded (no such route)


def test_forged_or_expired_tokens_are_rejected(client, monkeypatch):
    import jwt

    claims = tokens.decode(client.cookies["iw_session"])
    assert claims is not None
    forged = jwt.encode(
        {**claims, "role": "SUPERVISOR"}, "another-secret-0123456789abcdef0123", algorithm="HS256"
    )
    expired = jwt.encode({**claims, "exp": 1, "iat": 0}, tokens.get_secret(), algorithm="HS256")
    none_alg = jwt.encode({**claims}, None, algorithm="none")
    for token in (forged, expired, none_alg, "garbage", "x" * 5000):
        assert TestClient(api, cookies={"iw_session": token}).get("/api/incidents").status_code == 401


def test_cross_origin_writes_are_refused(client):
    evil = client.post("/api/incidents/x/assign", headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    same = client.post("/api/incidents/x/assign", headers={"Origin": "http://testserver"})
    assert same.status_code == 404  # passed the guard, then: no such incident


def test_socketio_requires_the_session_cookie(client):
    from app.main import app as asgi_app

    url = "/socket.io/?EIO=4&transport=polling"
    with TestClient(asgi_app) as sock:
        assert sock.get(url).status_code == 401
        sock.cookies.set("iw_session", "forged.token.value")
        assert sock.get(url).status_code == 401
        sock.cookies.set("iw_session", client.cookies["iw_session"])
        opened = sock.get(url)
        assert opened.status_code == 200 and opened.text.startswith("0{")


def test_socketio_websocket_rejected_without_cookie(client):
    from starlette.websockets import WebSocketDisconnect

    from app.main import app as asgi_app

    with TestClient(asgi_app) as sock, pytest.raises(WebSocketDisconnect):  # noqa: SIM117
        with sock.websocket_connect("/socket.io/?EIO=4&transport=websocket"):
            pass


def _settings(**values) -> Settings:
    return Settings(**{"jwt_secret": "", "demo_login": False, "app_env": "development", **values})


def test_secret_policy():
    good = "q" * 40
    with pytest.raises(AuthConfigError):
        resolve_secret(_settings(app_env="production"))
    with pytest.raises(AuthConfigError):
        resolve_secret(_settings(app_env="production", jwt_secret="change-me-jwt-secret-0123456789abcdef"))
    with pytest.raises(AuthConfigError):
        resolve_secret(_settings(app_env="production", jwt_secret="short-but-real"))
    with pytest.raises(AuthConfigError):  # production refuses even with the demo login on
        resolve_secret(_settings(app_env="production", demo_login=True))
    assert resolve_secret(_settings(app_env="production", jwt_secret=good)) == good
    with pytest.raises(AuthConfigError):  # no secret and no demo
        resolve_secret(_settings())
    first, second = resolve_secret(_settings(demo_login=True)), resolve_secret(_settings(demo_login=True))
    assert first != second and len(first) >= 32  # random per process


def test_production_refuses_placeholder_demo_passwords(client, monkeypatch):
    from app.auth.users import seed_users

    monkeypatch.setattr(get_settings(), "app_env", "production")
    monkeypatch.setattr(get_settings(), "demo_analyst_password", "change-me-analyst")
    with pytest.raises(AuthConfigError):
        seed_users()


def test_demo_account_without_password_is_demo_only(client, monkeypatch):
    from app.auth.users import seed_users
    from app.db import session_scope
    from app.models import User

    with session_scope() as db:
        db.query(User).delete()
    monkeypatch.setattr(get_settings(), "demo_analyst_password", "")
    seed_users()
    anon = TestClient(api)
    assert anon.post("/api/auth/login", json={"email": ANALYST[0], "password": ""}).status_code == 422
    assert anon.post("/api/auth/login", json={"email": ANALYST[0], "password": ANALYST[1]}).status_code == 401
    assert anon.post("/api/auth/demo", json={"role": "ANALYST"}).status_code == 200


def test_seed_updates_a_changed_password(client, monkeypatch):
    from app.auth.users import seed_users

    monkeypatch.setattr(get_settings(), "demo_analyst_password", "new-analyst-pass")
    seed_users()
    anon = TestClient(api)
    assert anon.post("/api/auth/login", json={"email": ANALYST[0], "password": ANALYST[1]}).status_code == 401
    assert (
        anon.post("/api/auth/login", json={"email": ANALYST[0], "password": "new-analyst-pass"}).status_code
        == 200
    )
