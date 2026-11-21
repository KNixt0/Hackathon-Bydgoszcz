"""Optional local LLM layer: a thin Ollama client over plain HTTP.

Disabled unless `LLM_ENABLED=true` and `OLLAMA_MODEL` is set. Every call has a short
timeout and failures are swallowed: the deterministic engine never depends on the model.
"""

from __future__ import annotations

import logging
import time

import httpx

from ..config import Settings

log = logging.getLogger(__name__)
AVAILABILITY_TTL_S = 30.0


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.llm_enabled and bool(settings.ollama_model)
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model
        self.timeout_s = settings.llm_timeout_s
        self._available: bool | None = None
        self._checked_at = 0.0

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
                names = {m.get("name", "") for m in resp.json().get("models", [])}
                ok = any(n == self.model or n.split(":")[0] == self.model for n in names)
        except (httpx.HTTPError, ValueError) as exc:
            log.info("ollama not reachable: %s", exc)
        self._available, self._checked_at = ok, time.monotonic()
        return ok

    async def generate(self, prompt: str, system: str, json_mode: bool = False) -> str | None:
        """One completion, or None on any failure or timeout."""
        if not await self.available():
            return None
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500},
        }
        if json_mode:
            payload["format"] = "json"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                return (resp.json().get("response") or "").strip() or None
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("ollama generate failed, falling back to deterministic output: %s", exc)
            return None
