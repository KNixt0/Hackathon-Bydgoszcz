"""The optional LLM layer: never required, never trusted without grounding, never faked."""

from __future__ import annotations

import asyncio
import itertools
import json

from app.config import load_settings
from app.engine import Engine
from app.llm import OllamaClient, propose_claims, rewrite_rationale
from app.schemas import Context, Document

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


def test_llm_output_does_not_change_the_score(engine, registries):
    baseline = asyncio.run(engine.analyze(DOC, Context()))
    eng = Engine(load_settings(), registries)
    eng.llm = FakeLLM(
        json.dumps({"claims": [{"text": "Presja czasu", "quote": "zanim będzie za późno"}]}),
        "Materiał obiecuje zysk bez ryzyka i nie zawiera ostrzeżenia, dlatego wymaga reakcji nadzoru.",
    )
    with_llm = asyncio.run(eng.analyze(DOC, Context()))
    assert with_llm.engine.llm_used is True and with_llm.engine.model == "fake-model"
    assert with_llm.risk_score == baseline.risk_score
    assert with_llm.debate.arbiter_rationale.startswith("Materiał obiecuje")
    llm_claims = [c for c in with_llm.debate.claims if c.text == "Presja czasu"]
    assert len(llm_claims) == 1 and llm_claims[0].verdict == "weakened"
    assert any(r.agent == "Model językowy (Ollama)" for r in with_llm.debate.rounds)
