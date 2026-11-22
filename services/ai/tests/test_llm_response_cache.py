"""Identical local-model work is reused briefly; failures and output modes stay separate."""

import asyncio
from dataclasses import replace

import httpx

from app.config import load_settings
from app.llm.ollama import RESPONSE_TTL_S, OllamaClient


def configured(monkeypatch, responses):
    calls = []

    def handler(request):
        calls.append(request)
        response = responses[min(len(calls) - 1, len(responses) - 1)]
        return httpx.Response(200, json=response)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        "app.llm.ollama.httpx.AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    client = OllamaClient(replace(load_settings(), llm_enabled=True, ollama_model="local-test"))
    client._available = True
    import time

    client._checked_at = time.monotonic()
    return client, calls


def test_identical_successful_requests_are_reused(monkeypatch):
    client, calls = configured(monkeypatch, [{"response": "Wynik lokalnego modelu"}])
    assert asyncio.run(client.generate("ten sam materiał", "instrukcja")) == "Wynik lokalnego modelu"
    assert asyncio.run(client.generate("ten sam materiał", "instrukcja")) == "Wynik lokalnego modelu"
    assert len(calls) == 1
    asyncio.run(client.generate("zmieniony materiał", "instrukcja"))
    asyncio.run(client.generate("ten sam materiał", "inna instrukcja"))
    asyncio.run(client.generate("ten sam materiał", "instrukcja", json_mode=True))
    assert len(calls) == 4


def test_expired_results_are_generated_again(monkeypatch):
    client, calls = configured(monkeypatch, [{"response": "pierwszy"}, {"response": "świeży"}])
    asyncio.run(client.generate("materiał", "instrukcja"))
    key = ("materiał", "instrukcja", False)
    at, value = client._responses[key]
    client._responses[key] = (at - RESPONSE_TTL_S - 1, value)
    assert asyncio.run(client.generate("materiał", "instrukcja")) == "świeży"
    assert len(calls) == 2


def test_empty_and_malformed_answers_do_not_poison_later_requests(monkeypatch):
    client, calls = configured(monkeypatch, [{"response": []}, {"response": ""}, [], {"response": "poprawny"}])
    for _ in range(3):
        assert asyncio.run(client.generate("materiał", "instrukcja")) is None
    assert asyncio.run(client.generate("materiał", "instrukcja")) == "poprawny"
    assert len(calls) == 4


def test_concurrent_identical_requests_share_one_model_completion(monkeypatch):
    client, calls = configured(monkeypatch, [{"response": "odpowiedź"}])

    async def run():
        return await asyncio.gather(
            client.generate("materiał", "instrukcja"), client.generate("materiał", "instrukcja")
        )

    assert asyncio.run(run()) == ["odpowiedź", "odpowiedź"]
    assert len(calls) == 1


def test_different_requests_do_not_compete_inside_the_model_server(monkeypatch):
    active, peak = 0, 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, json={"response": "odpowiedź"})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        "app.llm.ollama.httpx.AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    client = OllamaClient(replace(load_settings(), llm_enabled=True, ollama_model="local-test"))
    import time

    client._available, client._checked_at = True, time.monotonic()

    async def run():
        return await asyncio.gather(client.generate("pierwszy", "instrukcja"), client.generate("drugi", "instrukcja"))

    assert asyncio.run(run()) == ["odpowiedź", "odpowiedź"]
    assert peak == 1
