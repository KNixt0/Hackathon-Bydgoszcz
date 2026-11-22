"""Test harness: SQLite in memory, eager queue, fake object store, stub AI + fake web via httpx MockTransport."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

_SAMPLES = Path(tempfile.mkdtemp(prefix="iw-samples-"))
os.environ.update(
    {
        "TASK_MODE": "eager",
        "DATABASE_URL": "sqlite://",
        "REDIS_URL": "",
        "S3_ENDPOINT": "",
        "SAMPLES_DIR": str(_SAMPLES),
        "FIXTURE_BASE_URL": "http://backend:8000",
        "AI_URL": "http://ai:8001",
        "SCRAPE_HOST_DELAY_SECONDS": "0",
        "SCAN_MAX_RETRIES": "0",
        "SEED_ON_START": "false",
        "CORS_ORIGINS": "",
        "APP_ENV": "development",
        "JWT_SECRET": "test-only-jwt-secret-0123456789abcdef0123456789",
        "DEMO_LOGIN": "true",
        "DEMO_ANALYST_EMAIL": "analityk@uknf.local",
        "DEMO_ANALYST_PASSWORD": "analyst-pass-1",
        "DEMO_SUPERVISOR_EMAIL": "kierownik@uknf.local",
        "DEMO_SUPERVISOR_PASSWORD": "supervisor-pass-1",
        # filter tests back-date samples by days; the system start rule has its own tests
        "SYSTEM_START_DATE": "2000-01-01",
    }
)
ANALYST = ("analityk@uknf.local", "analyst-pass-1")
SUPERVISOR = ("kierownik@uknf.local", "supervisor-pass-1")

import logging  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ai_client, events, pipeline, storage  # noqa: E402
from app.auth import passwords, tokens  # noqa: E402
from app.auth.throttle import throttle  # noqa: E402
from app.auth.users import seed_users  # noqa: E402
from app.db import Base, get_engine  # noqa: E402
from app.main import api  # noqa: E402
from app.scraper import engine as scraper_engine  # noqa: E402
from app.scraper import ssrf  # noqa: E402

logging.getLogger().setLevel(logging.DEBUG)  # build every log record (catches bad `extra` keys)

RULE_IDS = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12a",
    "12b",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
]
PUBLIC_IP = "93.184.216.34"


def make_analysis(document: dict, context: dict | None = None) -> dict:
    """A contract-valid Analysis; the score depends on the text so re-scans can change it."""
    context = context or {}
    text = " ".join(document["text"].split())
    risky = "gwarantowany zysk" in text.lower()
    score = 88.0 if risky else 12.0
    quote = "gwarantowany zysk" if risky else None
    evidence = [{"id": "e1", "kind": "url", "label": "Źródło", "url": document["url"]}]
    if quote:
        start = text.lower().index(quote)
        evidence.append(
            {
                "id": "e2",
                "kind": "quote",
                "label": "Obietnica zysku",
                "quote": text[start : start + len(quote)],
                "span": {"start": start, "end": start + len(quote)},
                "legal_ref": "art. 44 ust. 2 rozp. del. 2017/565",
            }
        )
    module = context.get("module_hint", 2)
    out_of_scope = "POZA_ZAKRESEM" in text  # contract v4 scope, for WatchIt list tests
    return {
        **(
            {
                "scope": {
                    "in_scope": False,
                    "category": "consumer_credit",
                    "basis": "out_of_scope",
                    "reason": "Kredyt.",
                }
            }
            if out_of_scope
            else {}
        ),
        "title": document["title"] or "Materiał bez tytułu",
        "summary": "Materiał obiecuje gwarantowany zysk." if risky else "Nie stwierdzono naruszeń.",
        "modules": [module] if not risky else sorted({module, 1}),
        "primary_module": module,
        "risk_score": score,
        "compliance_score": 100 - score,
        "risk_level": "red" if risky else "green",
        "synthetic": bool(context.get("synthetic", False)),
        "ground_truth": context.get("ground_truth"),
        "demo_case": context.get("demo_case"),
        "source": {
            "platform": document["platform"],
            "url": document["url"],
            "fetched_at": document["fetched_at"],
            "language": document.get("language", "pl"),
            "content_hash": hashlib.sha256(text.encode()).hexdigest(),
            "text": text,
            "archive": document["archive"],
        },
        "entities": {
            "investment_firm": {"name": "Żółw Capital S.A.", "kind": "investment_firm"},
            "advertiser": {
                "name": (document.get("author") or {}).get("name", "=Anonim"),
                "kind": "advertiser",
            },
            "others": [],
        },
        "module_results": [
            {"module": module, "plugin": "stub", "score": score, "weight": 1.0, "findings": []}
        ],
        "rules": [
            {
                "id": rule,
                "name": f"Kryterium {rule}",
                "legal_basis": "art. 44 rozp. del. 2017/565",
                "status": "fail" if risky and rule in ("6", "12a") else "pass",
                "confidence": 0.9,
                "explanation": "Wyjaśnienie zażółć gęślą jaźń",
                "evidence_ids": ["e2"] if risky and rule == "6" else [],
            }
            for rule in RULE_IDS
        ],
        "registry_checks": [
            {
                "registry": "knf_brokerage_houses",
                "label": "Domy maklerskie",
                "url": "https://www.knf.gov.pl/",
                "subject": "Żółw Capital S.A.",
                "status": "not_listed",
                "detail": "Brak wpisu",
                "snapshot_date": "2026-11-01",
            }
        ],
        "graph": {"nodes": [], "edges": [], "flagged_paths": []},
        "forensics": None,
        "financials": None,
        "debate": {
            "rounds": [],
            "claims": [
                {
                    "id": "c1",
                    "stance": "for",
                    "text": "Obietnica zysku bez ryzyka",
                    "confidence": 0.8,
                    "evidence_ids": [],
                    "verdict": "upheld",
                    "critique": None,
                },
                {
                    "id": "c2",
                    "stance": "against",
                    "text": "Jest ostrzeżenie o ryzyku",
                    "confidence": 0.4,
                    "evidence_ids": [],
                    "verdict": "weakened",
                    "critique": "Zbyt mała czcionka",
                },
            ],
            "arguments_for": ["c1"],
            "arguments_against": ["c2"],
            "arbiter_rationale": "Przeważają argumenty za.",
        },
        "evidence": evidence,
        "recommendation": {
            "action": "escalate" if risky else "none",
            "label": "Eskalować",
            "next_step": "Wezwać",
        },
        "engine": {
            "version": "stub-1",
            "plugins": ["stub"],
            "llm_used": False,
            "model": None,
            "duration_ms": 5,
        },
    }


class World:
    """Everything outside the backend: the AI service and the internet."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.pages: dict[str, httpx.Response | str] = {}
        self.ai_calls: list[dict] = []
        self.ai_down = False
        self.ai_response: dict | None = None  # override
        self.registries_put: dict[str, dict] = {}
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.url.host
        if host == "ai":
            return self._ai(request)
        if host == "backend":
            inner = self.client.get(request.url.raw_path.decode())
            return httpx.Response(
                inner.status_code,
                content=inner.content,
                headers={"content-type": inner.headers.get("content-type", "")},
            )
        page = self.pages.get(str(request.url))
        if page is None:
            return httpx.Response(404, text="not found")
        if isinstance(page, str):
            return httpx.Response(200, text=page, headers={"content-type": "text/html; charset=utf-8"})
        return page

    def _ai(self, request: httpx.Request) -> httpx.Response:
        if self.ai_down:
            raise httpx.ConnectError("refused")
        path = request.url.path
        if path == "/health":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "llm_available": True,
                    "model": "gemma",
                    "plugins": [],
                    "registries": [],
                },
            )
        if path == "/registries" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "registry": "knf_brokerage_houses",
                            "label": "Domy maklerskie",
                            "url": "https://www.knf.gov.pl/dm",
                            "entries": 37,
                            "snapshot_date": "2026-11-01",
                        }
                    ]
                },
            )
        if path.startswith("/registries/") and request.method == "PUT":
            body = json.loads(request.content)
            self.registries_put[path.rsplit("/", 1)[-1]] = body
            return httpx.Response(200, json={"entries": len(body["entries"])})
        if path == "/analyze":
            body = json.loads(request.content)
            self.ai_calls.append(body)
            if self.ai_response is not None:
                return httpx.Response(200, json=self.ai_response)
            return httpx.Response(200, json=make_analysis(body["document"], body.get("context")))
        return httpx.Response(404)


class MemoryStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def get(self, key: str) -> tuple[bytes, str] | None:
        return self.objects.get(key)

    def healthy(self) -> bool:
        return True


GREEN_HTML = """<!doctype html><html lang="pl"><head><title>Fundusz Spokojny</title>
<meta property="og:title" content="Fundusz Spokojny – rzetelna informacja"></head>
<body><h1>Fundusz Spokojny</h1><p>Inwestowanie wiąże się z ryzykiem utraty kapitału. Zażółć gęślą jaźń.</p></body></html>"""
RED_TEXT = "Tylko dziś! Gwarantowany zysk 30% miesięcznie, zero ryzyka. Napisz do mnie na priv."
CASE3_HTML = """<html lang="pl"><head><title>Sygnały premium</title></head><body>
<p>Dołącz do grupy VIP – gwarantowany zysk i indywidualne rekomendacje co kupić.</p></body></html>"""


def write_samples(root: Path) -> None:
    for child in root.rglob("*"):
        if child.is_file():
            child.unlink()
    (root / "sub").mkdir(exist_ok=True)
    (root / "green.html").write_text(GREEN_HTML, encoding="utf-8")
    (root / "green.json").write_text(
        json.dumps(
            {
                "meta": {
                    "url": "https://www.youtube.com/watch?v=green",
                    "platform": "youtube",
                    "title": "Spokojny film",
                    "published_at": "2026-11-01",
                    "author": {"name": "Kanał Spokojny", "handle": "@spokojny"},
                    "seed": True,
                    "detected_days_ago": 3,
                },
                "html_file": "green.html",
                "context": {"synthetic": True, "ground_truth": "ok", "module_hint": 1},
            }
        ),
        encoding="utf-8",
    )
    (root / "red.json").write_text(
        json.dumps(
            {
                "meta": {
                    "url": "https://www.instagram.com/p/red/",
                    "platform": "instagram",
                    "title": "Szybki zysk",
                    "detected_days_ago": 10,
                },
                "text": RED_TEXT,
                "context": {"synthetic": True, "ground_truth": "violation", "module_hint": 3},
            }
        ),
        encoding="utf-8",
    )
    (root / "case3.html").write_text(CASE3_HTML, encoding="utf-8")
    (root / "case3.json").write_text(
        json.dumps(
            {
                "meta": {
                    "url": "https://t.example/vip",
                    "platform": "web",
                    "title": "VIP",
                    "seed": False,
                    "detected_days_ago": 5,
                },
                "html_file": "case3.html",
                "context": {"synthetic": True, "demo_case": "case3", "module_hint": 3},
            }
        ),
        encoding="utf-8",
    )
    (root / "sub" / "pendrive.html").write_text(
        "<html><body><p>Materiał z pendrive'a, neutralny opis oferty.</p></body></html>", encoding="utf-8"
    )
    (root / "sub" / "note.txt").write_text("Notatka: gwarantowany zysk bez ryzyka!", encoding="utf-8")
    (root / "notes.json").write_text(json.dumps({"unrelated": True}), encoding="utf-8")


@pytest.fixture
def samples_dir() -> Path:
    write_samples(_SAMPLES)
    return _SAMPLES


def login(test_client: TestClient, account: tuple[str, str]) -> TestClient:
    response = test_client.post("/api/auth/login", json={"email": account[0], "password": account[1]})
    assert response.status_code == 200, response.text
    return test_client


@pytest.fixture
def anon(client):
    """A second browser without a session, sharing the database of `client`."""
    return TestClient(api, raise_server_exceptions=False)


@pytest.fixture
def analyst(client):
    return login(TestClient(api, raise_server_exceptions=False), ANALYST)


@pytest.fixture
def client(samples_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Logged in as the supervisor (every role check passes); see `analyst` and `anon`."""
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    monkeypatch.setattr(passwords, "hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
    tokens.reset_secret()
    throttle.reset()
    seed_users()
    test_client = login(TestClient(api, raise_server_exceptions=False), SUPERVISOR)
    world = World(TestClient(api))
    transport = httpx.MockTransport(world.handler)
    monkeypatch.setattr(ai_client, "transport", transport)
    monkeypatch.setattr(scraper_engine, "transport", transport)
    hosts = {
        "backend": ["172.18.0.5"],
        "localhost": ["127.0.0.1"],
        "0x7f.1": ["127.0.0.1"],
        "internal.test": ["10.0.0.5"],
        "mixed.test": [PUBLIC_IP, "127.0.0.1"],
    }
    monkeypatch.setattr(ssrf, "resolver", lambda host, port: hosts.get(host, [PUBLIC_IP]))
    emitted: list[tuple[str, dict]] = []
    monkeypatch.setattr(events, "emit", lambda event, payload: emitted.append((event, payload)))
    store = MemoryStore()
    storage.set_store(store)
    pipeline.reset_fetcher()
    test_client.world = world  # type: ignore[attr-defined]
    test_client.emitted = emitted  # type: ignore[attr-defined]
    test_client.store = store  # type: ignore[attr-defined]
    yield test_client
    storage.set_store(None)


def events_named(client: TestClient, name: str) -> list[dict]:
    return [payload for event, payload in client.emitted if event == name]
