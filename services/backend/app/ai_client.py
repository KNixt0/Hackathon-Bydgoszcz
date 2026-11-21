"""HTTP client for the AI service (contract: coord/contracts/api.md)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

# tests swap this for an httpx.MockTransport
transport: httpx.BaseTransport | None = None


class AIUnavailable(Exception):
    """Connection problem or 5xx: worth retrying."""


class AIRejected(Exception):
    """The AI service answered with a client error or an unusable body."""


def _client(timeout: float) -> httpx.Client:
    return httpx.Client(base_url=get_settings().ai_url, timeout=timeout, transport=transport)


def _request(method: str, path: str, timeout: float, **kwargs: Any) -> Any:
    try:
        with _client(timeout) as client:
            response = client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise AIUnavailable(f"AI service unreachable ({type(exc).__name__})") from exc
    if response.status_code >= 500:
        raise AIUnavailable(f"AI service error {response.status_code}")
    if response.status_code >= 400:
        raise AIRejected(f"AI service rejected the request ({response.status_code})")
    try:
        return response.json()
    except ValueError as exc:
        raise AIRejected("AI service returned invalid JSON") from exc


def analyze(document: dict, context: dict | None) -> dict:
    body: dict[str, Any] = {"document": document}
    if context:
        body["context"] = context
    result = _request("POST", "/analyze", get_settings().ai_timeout_seconds, json=body)
    if not isinstance(result, dict):
        raise AIRejected("AI service returned an unexpected body")
    return result


def health(timeout: float = 2.0) -> dict | None:
    try:
        result = _request("GET", "/health", timeout)
    except (AIUnavailable, AIRejected):
        return None
    return result if isinstance(result, dict) else None


def registries(timeout: float = 3.0) -> list[dict] | None:
    try:
        result = _request("GET", "/registries", timeout)
    except (AIUnavailable, AIRejected):
        return None
    items = result.get("items") if isinstance(result, dict) else result
    return items if isinstance(items, list) else None


def put_registry(registry: str, snapshot_date: str, entries: list[dict]) -> int:
    result = _request(
        "PUT", f"/registries/{registry}", 60.0, json={"snapshot_date": snapshot_date, "entries": entries}
    )
    return int(result.get("entries", len(entries))) if isinstance(result, dict) else len(entries)
