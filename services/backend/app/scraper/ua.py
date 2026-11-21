"""User-Agent rotation: a pool of current, realistic desktop and mobile browsers."""

from __future__ import annotations

import random

DESKTOP_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/26.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
)

MOBILE_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 26_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/26.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 16; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 15; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Mobile Safari/537.36",
)


class UserAgentRotator:
    """Hands out user agents without repeating the previous one. Desktop by default: mobile UAs
    often get redirected to app-install interstitials."""

    def __init__(self, pool: tuple[str, ...] | None = None, rng: random.Random | None = None) -> None:
        self.pool = pool or DESKTOP_USER_AGENTS
        self._rng = rng or random.Random()  # noqa: S311 (not security relevant)
        self._last: str | None = None

    def next(self) -> str:
        choices = [ua for ua in self.pool if ua != self._last] or list(self.pool)
        self._last = self._rng.choice(choices)
        return self._last


class ProxyRotator:
    """Round-robin over PROXY_URLS; empty pool = direct connection."""

    def __init__(self, proxies: list[str]) -> None:
        self.proxies = list(proxies)
        self._index = 0

    def next(self) -> str | None:
        if not self.proxies:
            return None
        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        return proxy


def redact_proxy(proxy: str | None) -> str | None:
    """Proxy URL without credentials (safe to store in Document.fetch.proxy and logs)."""
    if not proxy:
        return None
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(proxy)
    host = parts.hostname or ""
    netloc = f"{host}:{parts.port}" if parts.port else host
    return urlunsplit((parts.scheme, netloc, "", "", ""))
