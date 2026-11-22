"""Native startup requires working inference, not just an installed-model entry."""

import httpx
import pytest
from check_local_model import check


def transport(monkeypatch, models, answer):
    calls = []

    def handle(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"models": models} if request.url.path == "/api/tags" else answer)

    original = httpx.Client
    monkeypatch.setattr(
        "check_local_model.httpx.Client", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs)
    )
    return calls


def test_startup_requires_a_real_generated_answer(monkeypatch):
    calls = transport(monkeypatch, [{"name": "gemma4:e4b"}], {"model": "gemma4:e4b", "response": "OK", "eval_count": 2})
    assert check("http://local.test", "gemma4:e4b") == {"model": "gemma4:e4b", "tokens": 2}
    assert calls == ["/api/tags", "/api/generate"]


@pytest.mark.parametrize("answer", [{"response": ""}, {"response": None}, {"response": []}])
def test_an_installed_model_without_a_reply_does_not_pass(monkeypatch, answer):
    transport(monkeypatch, [{"name": "gemma4:e4b"}], answer)
    with pytest.raises(RuntimeError, match="nie zwrócił odpowiedzi"):
        check("http://local.test", "gemma4:e4b")


def test_missing_model_does_not_attempt_inference(monkeypatch):
    calls = transport(monkeypatch, [], {})
    with pytest.raises(RuntimeError, match="nie jest zainstalowany"):
        check("http://local.test", "gemma4:e4b")
    assert calls == ["/api/tags"]
