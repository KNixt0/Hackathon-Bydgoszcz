"""HTTP API: endpoints from coord/contracts/api.md and schema conformance of /analyze."""

from __future__ import annotations

import pytest
from conftest import SAMPLES
from fastapi.testclient import TestClient
from run_eval import load_sample

from app.registries import REGISTRIES
from app.schemas import Analysis

ANALYSIS_KEYS = {
    "title",
    "summary",
    "modules",
    "primary_module",
    "risk_score",
    "compliance_score",
    "risk_level",
    "synthetic",
    "ground_truth",
    "demo_case",
    "source",
    "entities",
    "module_results",
    "rules",
    "registry_checks",
    "graph",
    "forensics",
    "financials",
    "debate",
    "evidence",
    "recommendation",
    "engine",
    "scope",  # contract v4
}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import os

    os.environ["AI_DATA_DIR"] = str(tmp_path_factory.mktemp("ai-data"))
    from app.main import app

    with TestClient(app) as c:
        yield c
    os.environ.pop("AI_DATA_DIR")


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["llm_available"] is False and body["model"] is None
    assert body["llm_enabled"] is False
    assert body["embeddings"] == {"requested": "hash", "backend": "hash-ngram", "model": None}
    assert body["plugins"] == [
        "m1_finfluencer",
        "m2_risk_disclosure",
        "m3_shadow_advisory",
        "graph_intel",
        "opinion_forensics",
    ]
    assert [r["registry"] for r in body["registries"]] == list(REGISTRIES)
    assert all(set(r) == {"registry", "entries", "snapshot_date"} for r in body["registries"])


def test_plugins_and_registries(client):
    plugins = client.get("/plugins").json()["items"]
    assert all(set(p) == {"id", "module", "description"} for p in plugins)
    assert [p["module"] for p in plugins] == [1, 2, 3, None, None]
    regs = client.get("/registries").json()["items"]
    assert all(set(r) == {"registry", "label", "url", "entries", "snapshot_date"} for r in regs)
    assert next(r for r in regs if r["registry"] == "knf_brokerage_houses")["url"].endswith("/domy_maklerskie")


@pytest.mark.parametrize("case", sorted((SAMPLES / "cases").glob("*.json")), ids=lambda p: p.stem)
def test_analyze_conforms_to_contract(client, case):
    resp = client.post("/analyze", json=load_sample(case))
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == ANALYSIS_KEYS
    Analysis.model_validate(body)  # strict mirror of the contract: unknown or missing keys fail
    assert set(body["source"]) - {"published_at"} == {"platform", "url", "fetched_at", "language", "content_hash", "text", "archive"}
    assert set(body["graph"]) == {"nodes", "edges", "flagged_paths"}
    assert set(body["debate"]) == {"rounds", "claims", "arguments_for", "arguments_against", "arbiter_rationale"}
    assert set(body["engine"]) == {"version", "plugins", "llm_used", "model", "duration_ms"}
    for ev in body["evidence"]:
        assert None not in ev.values()  # optional evidence keys are omitted, not null
        if ev["kind"] == "quote":
            assert body["source"]["text"][ev["span"]["start"] : ev["span"]["end"]] == ev["quote"]
    assert body["engine"]["duration_ms"] < 1000


def test_analyze_minimal_document_without_context(client):
    resp = client.post(
        "/analyze",
        json={
            "document": {
                "url": "https://test.example/a",
                "platform": "sample",
                "fetched_at": "2026-11-21T12:00:00Z",
                "http_status": 200,
                "title": "",
                "html": "",
                "text": "Dzień dobry, to zwykły tekst.",
                "fetch": {"engine": "file", "user_agent": "t", "proxy": None},
                "archive": {"html_key": "html/abc.html", "screenshot_key": None},
            }
        },
    )
    body = resp.json()
    assert resp.status_code == 200 and len(body["rules"]) == 19
    assert body["graph"] == {"nodes": [], "edges": [], "flagged_paths": []}
    assert body["forensics"] is None and body["financials"] is None and body["ground_truth"] is None
    assert body["synthetic"] is False and body["risk_score"] == 0 and body["modules"] == [2]
    assert any(e["kind"] == "archive" and e["storage_key"] == "html/abc.html" for e in body["evidence"])
    assert body["source"]["archive"]["html_key"] == "html/abc.html"


def test_analyze_rejects_bad_input(client):
    assert client.post("/analyze", json={"document": {"platform": "web"}}).status_code == 422
    assert client.post("/analyze", json={}).status_code == 422


def test_put_registry_changes_the_next_analysis(client):
    doc = {
        "document": {
            "url": "https://test.example/b",
            "platform": "web",
            "fetched_at": "2026-11-21T12:00:00Z",
            "text": "Zupełnie Nowa Testowa Firma Ltd wskaże Ci, które akcje kupić, a które sprzedać.",
        }
    }

    def status():
        checks = client.post("/analyze", json=doc).json()["registry_checks"]
        return next(c for c in checks if c["registry"] == "knf_foreign_cross_border")

    assert status()["status"] == "not_listed"
    resp = client.put(
        "/registries/knf_foreign_cross_border",
        json={
            "snapshot_date": "2026-12-24",
            "entries": [{"name": "Zupełnie Nowa Testowa Firma Ltd", "status": "listed"}],
        },
    )
    assert resp.status_code == 200 and resp.json() == {"entries": 1}
    after = status()
    assert after["status"] == "listed" and after["snapshot_date"] == "2026-12-24"
    row = next(r for r in client.get("/registries").json()["items"] if r["registry"] == "knf_foreign_cross_border")
    assert row["entries"] == 1 and row["snapshot_date"] == "2026-12-24"


def test_put_registry_errors(client):
    payload = {"snapshot_date": "2026-12-24", "entries": []}
    assert client.put("/registries/nope", json=payload).status_code == 404
    assert client.put("/registries/uknf_cooperation_notice", json=payload).status_code == 422
    assert client.put("/registries/knf_public_warnings", json={"entries": []}).status_code == 422


def test_health_reports_models_truthfully(client, monkeypatch):
    from app.main import app
    from app.preprocess import OllamaEmbedder

    engine = app.state.engine

    class Up:
        enabled, model = True, "gen-test"

        async def available(self):
            return True

    class Down(Up):
        async def available(self):
            return False

    emb = OllamaEmbedder("http://x:11434", "emb-test")
    monkeypatch.setattr(emb, "_request", lambda text: [1.0, 0.0])
    monkeypatch.setattr(engine, "embedder", emb)
    monkeypatch.setattr(engine, "llm", Up())
    body = client.get("/health").json()
    assert body["llm_available"] is True and body["model"] == "gen-test"
    assert body["embeddings"]["backend"] == "ollama" and body["embeddings"]["model"] == "emb-test"

    monkeypatch.setattr(engine, "llm", Down())
    monkeypatch.setattr(emb, "_request", lambda text: (_ for _ in ()).throw(ValueError("down")))
    body = client.get("/health").json()
    assert body["llm_available"] is False and body["model"] is None
    assert body["embeddings"]["backend"] == "hash-ngram" and body["embeddings"]["model"] is None
