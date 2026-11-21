"""The optional LLM layer: never required, never trusted without grounding, never faked."""

from __future__ import annotations

import asyncio
import itertools
import json

import httpx

from app.config import load_settings
from app.engine import Engine
from app.llm import OllamaClient, propose_claims, rewrite_rationale
from app.preprocess import HashEmbedder, OllamaEmbedder, build_embedder
from app.schemas import Context, Document
from app.scoring import llm_adjustment
from app.scoring import weights as W

TEXT = "Zarabiaj 20% rocznie bez ryzyka. Załóż konto już dziś, zanim będzie za późno."
DOC = Document(url="https://test.example/x", platform="web", fetched_at="2026-11-21T12:00:00Z", text=TEXT)


class FakeLLM(OllamaClient):
    """Stands in for a running Ollama; answers are scripted."""

    def __init__(self, claims_json: str, rewrite: str | None) -> None:
        self.enabled, self.model = True, "fake-model"
        self._claims, self._rewrite = claims_json, rewrite

    async def available(self) -> bool:
        return True

    async def generate(self, prompt: str, system: str, json_mode: bool = False) -> str | None:
        return self._claims if json_mode else self._rewrite


def test_disabled_by_default_and_reported_truthfully(engine):
    analysis = asyncio.run(engine.analyze(DOC, Context()))
    assert analysis.engine.llm_used is False and analysis.engine.model is None
    assert asyncio.run(engine.llm.available()) is False


def test_unreachable_ollama_falls_back(monkeypatch, registries):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma-test")
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9")  # nothing listens here
    eng = Engine(load_settings(), registries)
    assert eng.llm.enabled
    analysis = asyncio.run(eng.analyze(DOC, Context()))
    assert analysis.engine.llm_used is False and analysis.engine.model is None
    assert analysis.risk_score > 0 and analysis.debate.arbiter_rationale


def test_llm_claims_must_be_grounded(make_ctx):
    ctx = make_ctx(text=TEXT)
    answer = json.dumps(
        {
            "claims": [
                {"text": "Presja czasu", "quote": "zanim będzie za późno"},
                {"text": "Zmyślona teza", "quote": "gwarantujemy 500% zysku w tydzień"},
                {"text": "Bez cytatu", "quote": ""},
            ]
        }
    )
    claims = asyncio.run(propose_claims(FakeLLM(answer, None), ctx, [], itertools.count(50)))
    assert [c.text for c in claims] == ["Presja czasu"]
    quote = ctx.evidence.get(claims[0].evidence_ids[0])
    assert quote.quote == "zanim będzie za późno" and ctx.page.text[quote.span.start : quote.span.end] == quote.quote
    assert claims[0].code == "LLM_CLAIM" and claims[0].origin == "llm"


def test_llm_garbage_is_ignored(make_ctx):
    ctx = make_ctx(text=TEXT)
    for answer in ("to nie jest json", '{"claims": "x"}', "[]", None):
        assert asyncio.run(propose_claims(FakeLLM(answer, None), ctx, [], itertools.count(1))) == []


def test_rewrite_rejects_new_numbers():
    rationale = "Ryzyko wysokie: 78/100 (zgodność 22/100). Rekomendacja: eskalacja. " + "Uzasadnienie. " * 3
    ok = "Ryzyko jest wysokie i wynosi 78/100, dlatego rekomendujemy eskalację sprawy do właściwego departamentu."
    bad = "Ryzyko jest wysokie i wynosi 95/100, dlatego rekomendujemy eskalację sprawy do właściwego departamentu."
    assert asyncio.run(rewrite_rationale(FakeLLM("{}", ok), rationale)) == ok
    assert asyncio.run(rewrite_rationale(FakeLLM("{}", bad), rationale)) is None
    assert asyncio.run(rewrite_rationale(FakeLLM("{}", None), rationale)) is None


def _llm_engine(registries, claims_json: str, rewrite: str | None) -> Engine:
    eng = Engine(load_settings(), registries)
    eng.llm = FakeLLM(claims_json, rewrite)
    return eng


GROUNDED = json.dumps({"claims": [{"text": "Presja czasu", "quote": "zanim będzie za późno"}]})
REWRITE = "Materiał obiecuje zysk bez ryzyka i nie zawiera ostrzeżenia, dlatego wymaga reakcji nadzoru."


def test_grounded_llm_claims_add_a_small_capped_score(engine, registries):
    baseline = asyncio.run(engine.analyze(DOC, Context()))
    with_llm = asyncio.run(_llm_engine(registries, GROUNDED, REWRITE).analyze(DOC, Context()))
    assert with_llm.engine.llm_used is True and with_llm.engine.model == "fake-model"
    delta = round(with_llm.risk_score - baseline.risk_score, 1)
    assert 0 < delta <= W.LLM_MAX_POINTS
    assert delta == llm_adjustment([0.5])
    assert with_llm.debate.arbiter_rationale.startswith("Materiał obiecuje")
    llm_claims = [c for c in with_llm.debate.claims if c.text == "Presja czasu"]
    assert len(llm_claims) == 1 and llm_claims[0].verdict == "weakened"
    assert llm_claims[0].id in with_llm.debate.arguments_for
    assert any(r.agent == "Model językowy (fake-model)" for r in with_llm.debate.rounds)
    arbiter = with_llm.debate.rounds[-1]
    assert "fake-model" in arbiter.role


def test_ungrounded_llm_claims_do_not_move_the_score(engine, registries):
    baseline = asyncio.run(engine.analyze(DOC, Context()))
    fake = json.dumps({"claims": [{"text": "Zmyślona teza", "quote": "gwarantujemy 500% zysku w tydzień"}]})
    out = asyncio.run(_llm_engine(registries, fake, None).analyze(DOC, Context()))
    assert out.risk_score == baseline.risk_score and out.engine.llm_used is False and out.engine.model is None


def test_llm_adjustment_is_capped_and_never_negative():
    assert llm_adjustment([]) == 0.0
    assert llm_adjustment([1.0] * 10) == W.LLM_MAX_POINTS == 5.0
    assert llm_adjustment([0.0, -1.0]) == 0.0
    assert llm_adjustment([0.5]) == 1.5


def test_rule_based_roles_are_labelled_and_no_model_is_claimed_without_one(engine):
    a = asyncio.run(engine.analyze(DOC, Context()))
    assert a.engine.llm_used is False and a.engine.model is None
    assert all(r.role.startswith("agent regułowy") for r in a.debate.rounds)
    blob = " ".join(f"{r.agent} {r.role} {r.summary}" for r in a.debate.rounds) + a.debate.arbiter_rationale
    assert "model" not in blob.lower() and "ollama" not in blob.lower() and "LLM" not in blob


# ---------------------------------------------------------------- embeddings backend
class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("x", request=None, response=None)

    def json(self):
        return self._payload


def test_ollama_embedder_uses_model_vectors_and_falls_back(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        vec = [1.0, 0.0, 0.0] if "polecam" in json["input"] else [0.0, 1.0, 0.0]
        return _Resp({"embeddings": [vec]})

    monkeypatch.setattr(httpx, "post", fake_post)
    emb = build_embedder("ollama", "http://x:11434", "emb-test")
    assert isinstance(emb, OllamaEmbedder) and emb.active == "ollama" and emb.probe()
    assert emb.similarity("Polecam!", "polecam to") == 1.0 and emb.similarity("Polecam!", "opłaty") == 0.0
    assert calls and calls[0][0].endswith("/api/embed") and calls[0][1]["model"] == "emb-test"
    assert emb.similar_threshold == 0.72

    def broken(url, json=None, timeout=None):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", broken)
    assert emb.embed("zupełnie nowy tekst")  # hash fallback answers
    assert emb.active == "hash-ngram" and emb.probe() is False
    assert emb.similar_threshold == HashEmbedder().similar_threshold


def test_hash_backend_is_default_and_ollama_needs_a_model():
    assert isinstance(build_embedder("hash", "http://x", None), HashEmbedder)
    assert isinstance(build_embedder("ollama", "http://x", None), HashEmbedder)
