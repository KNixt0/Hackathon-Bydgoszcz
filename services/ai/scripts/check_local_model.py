"""Require a real answer from the configured local Ollama before starting native AI."""

from __future__ import annotations

import os
import sys

import httpx


def check(base_url: str, model: str, timeout: float = 180) -> dict:
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        tags = client.get("/api/tags", timeout=5)
        tags.raise_for_status()
        body = tags.json()
        models = body.get("models") if isinstance(body, dict) else None
        if not isinstance(models, list):
            raise RuntimeError("Ollama zwróciła nieprawidłową listę modeli.")
        names = {item.get("name") for item in models if isinstance(item, dict)}
        if model not in names and f"{model}:latest" not in names:
            raise RuntimeError(f"Model {model} nie jest zainstalowany. Uruchom: ollama pull {model}")
        payload = {
            "model": model,
            "prompt": "Odpowiedz tylko: OK",
            "stream": False,
            "think": False,
            "options": {"num_predict": 8},
        }
        response = client.post("/api/generate", json=payload)
        if response.status_code == 400:
            payload.pop("think")
            response = client.post("/api/generate", json=payload)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get("response"), str) or not body["response"].strip():
            raise RuntimeError("Model jest widoczny, ale nie zwrócił odpowiedzi. Usługa AI nie została uruchomiona.")
        return {"model": body.get("model", model), "tokens": body.get("eval_count")}


if __name__ == "__main__":
    try:
        result = check(
            os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
            os.environ.get("OLLAMA_MODEL", "gemma4:e4b"),
            float(os.environ.get("LLM_TIMEOUT_S", "180")),
        )
    except (httpx.HTTPError, ValueError, RuntimeError) as error:
        sys.exit(f"Nie udało się potwierdzić działania lokalnego modelu ({type(error).__name__}): {error}")
    print(f"Lokalny model odpowiada: {result['model']} ({result['tokens']} tokenów).")
