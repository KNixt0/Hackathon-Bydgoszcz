"""Optional local LLM layer: a thin Ollama client over plain HTTP.

Disabled unless `LLM_ENABLED=true` and `OLLAMA_MODEL` is set. Every call has a short
timeout and failures are swallowed: the deterministic engine never depends on the model.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict

import httpx

from ..config import Settings

log = logging.getLogger(__name__)
AVAILABILITY_TTL_S = 30.0
RESPONSE_TTL_S = 300.0
RESPONSE_CACHE_SIZE = 64


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.llm_enabled and bool(settings.ollama_model)
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model
        self.timeout_s = settings.llm_timeout_s
        self._available: bool | None = None
        self._checked_at = 0.0
        self._generation_lock = asyncio.Semaphore(1)
        self._responses: OrderedDict[tuple[str, str, bool], tuple[float, str]] = OrderedDict()

    async def available(self) -> bool:
        """True when the configured model is served by the local Ollama (cached briefly)."""
        if not self.enabled:
            return False
        if self._available is not None and time.monotonic() - self._checked_at < AVAILABILITY_TTL_S:
            return self._available
        ok = False
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                body = resp.json()
                models = body.get("models", []) if isinstance(body, dict) else []
                names = (
                    {
                        model["name"]
                        for model in models
                        if isinstance(model, dict) and isinstance(model.get("name"), str)
                    }
                    if isinstance(models, list)
                    else set()
                )
                ok = any(n == self.model or n.split(":")[0] == self.model for n in names)
        except (httpx.HTTPError, ValueError) as exc:
            log.info("ollama not reachable: %s", exc)
        self._available, self._checked_at = ok, time.monotonic()
        return ok

    async def generate(self, prompt: str, system: str, json_mode: bool = False) -> str | None:
        """Bound local inference concurrency; queued calls do not spend their HTTP timeout waiting."""
        async with self._generation_lock:
            return await self._generate(prompt, system, json_mode)

    async def _generate(self, prompt: str, system: str, json_mode: bool) -> str | None:
        """One completion, or None on any failure or timeout."""
        if not await self.available():
            return None
        key = (prompt, system, json_mode)
        cached = self._responses.get(key)
        if cached and time.monotonic() - cached[0] < RESPONSE_TTL_S:
            self._responses.move_to_end(key)
            log.info("ollama response cache hit")
            return cached[1]
        self._responses.pop(key, None)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500},
        }
        if json_mode:
            payload["format"] = "json"
        # Reasoning models (Gemma 4, Qwen 3) spend the whole token budget on hidden thinking and return
        # an empty answer; these are short rewrite/extract tasks, so thinking is switched off.
        payload["think"] = False
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 400:  # model without a thinking switch
                    payload.pop("think")
                    resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                body = resp.json()
                value = body.get("response") if isinstance(body, dict) else None
                answer = value.strip() if isinstance(value, str) else None
                if answer:
                    self._responses[key] = (time.monotonic(), answer)
                    self._responses.move_to_end(key)
                    while len(self._responses) > RESPONSE_CACHE_SIZE:
                        self._responses.popitem(last=False)
                return answer or None
        except (httpx.HTTPError, ValueError) as exc:
            log.warning(
                "ollama generate failed (%s), falling back to deterministic output: %s", type(exc).__name__, exc
            )
            return None
