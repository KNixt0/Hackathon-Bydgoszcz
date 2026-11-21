"""Fetcher: httpx first, Playwright (Chromium) on request or when the page is a JS shell.

Every request goes through the SSRF guard (also on each redirect hop), gets a rotated
User-Agent and proxy, honours robots.txt and waits a per-host politeness delay.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.config import Settings, get_settings
from app.scraper.extract import extract, looks_js_empty
from app.scraper.ssrf import BlockedURL, check_url, is_fixture_url
from app.scraper.ua import ProxyRotator, UserAgentRotator, redact_proxy

log = logging.getLogger(__name__)

MAX_REDIRECTS = 5
RETRY_STATUSES = {429, 500, 502, 503, 504}
_CHARSET_RE = re.compile(rb"<meta[^>]+charset=[\"']?\s*([A-Za-z0-9_-]+)", re.I)

# tests swap this for an httpx.MockTransport
transport: httpx.BaseTransport | None = None


class FetchError(Exception):
    """The page could not be fetched; `retryable` tells the queue whether to try again."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass
class FetchedPage:
    requested_url: str
    url: str  # after redirects
    status: int
    content_type: str
    body: str
    engine: str  # httpx | playwright
    user_agent: str
    proxy: str | None  # credentials removed
    fetched_at: str
    screenshot: bytes | None = None
    redirect_chain: list[str] = field(default_factory=list)  # every URL requested, first = requested

    @property
    def is_html(self) -> bool:
        kind = self.content_type.lower()
        return "html" in kind or (not kind and "<html" in self.body[:2000].lower())


class HostThrottle:
    """Minimum delay between two requests to the same host (per process)."""

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self._next: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        if self.delay <= 0:
            return
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next.get(host, 0.0))
            self._next[host] = start + self.delay
        if start > now:
            time.sleep(start - now)


def _decode(response: httpx.Response, raw: bytes) -> str:
    encoding = response.charset_encoding
    if not encoding:
        match = _CHARSET_RE.search(raw[:4096])
        encoding = match.group(1).decode("ascii", "ignore") if match else "utf-8"
    try:
        return raw.decode(encoding, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


class Fetcher:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.user_agents = UserAgentRotator()
        self.proxies = ProxyRotator(self.settings.proxy_list)
        self.throttle = HostThrottle(self.settings.scrape_host_delay_seconds)
        self._robots: dict[str, RobotFileParser | None] = {}

    # ---- public -------------------------------------------------------------------------

    def fetch(self, url: str, render: bool = False) -> FetchedPage:
        """Fetch a page. `render=True` forces Chromium; otherwise it is used only for JS shells."""
        check_url(url, self.settings)
        self._check_robots(url)
        if render and self._can_render(url):
            try:
                return self._render(url)
            except FetchError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("render failed, falling back to httpx", extra={"error": type(exc).__name__})
        page = self._get(url)
        if page.is_html and self._can_render(url) and looks_js_empty(page.body, extract(page.body).text):
            try:
                return self._render(url)
            except Exception as exc:  # noqa: BLE001
                log.info("page looks JS-only but rendering failed", extra={"error": type(exc).__name__})
        return page

    def get_text(self, url: str) -> str | None:
        """Auxiliary GET for parsers (oEmbed etc.). Returns None on any problem."""
        try:
            check_url(url, self.settings)
            page = self._get(url, retries=0)
        except (FetchError, BlockedURL):
            return None
        return page.body if page.status == 200 else None

    # ---- httpx --------------------------------------------------------------------------

    def _client(self, proxy: str | None, user_agent: str) -> httpx.Client:
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.7",
        }
        kwargs: dict = {
            "headers": headers,
            "timeout": self.settings.scrape_timeout_seconds,
            "follow_redirects": False,
        }
        if transport is not None:
            kwargs["transport"] = transport
        elif proxy:
            kwargs["proxy"] = proxy
        return httpx.Client(**kwargs)

    def _get(self, url: str, retries: int | None = None) -> FetchedPage:
        attempts = (self.settings.scrape_retries if retries is None else retries) + 1
        last_error = "fetch failed"
        for attempt in range(attempts):
            fixture = is_fixture_url(url, self.settings)
            proxy = None if fixture else self.proxies.next()
            user_agent = self.user_agents.next()
            try:
                with self._client(proxy, user_agent) as client:
                    response, final_url, body, chain = self._follow(client, url)
            except BlockedURL as exc:
                raise FetchError(f"blocked: {exc}") from exc
            except httpx.HTTPError as exc:
                last_error = f"network error ({type(exc).__name__})"
            else:
                if response.status_code not in RETRY_STATUSES:
                    return FetchedPage(
                        requested_url=url,
                        url=final_url,
                        status=response.status_code,
                        content_type=response.headers.get("content-type", ""),
                        body=body,
                        engine="httpx",
                        user_agent=user_agent,
                        proxy=redact_proxy(proxy),
                        fetched_at=_now(),
                        redirect_chain=chain,
                    )
                last_error = f"http status {response.status_code}"
            if attempt + 1 < attempts:
                time.sleep(min(2.0**attempt, 8.0) if transport is None else 0)
        raise FetchError(last_error, retryable=True)

    def _follow(self, client: httpx.Client, url: str) -> tuple[httpx.Response, str, str, list[str]]:
        current = url
        chain: list[str] = []
        for _ in range(MAX_REDIRECTS + 1):
            check_url(current, self.settings)
            chain.append(current)
            if not is_fixture_url(current, self.settings):
                self.throttle.wait(urlsplit(current).hostname or "")
            with client.stream("GET", current) as response:
                if response.is_redirect and response.headers.get("location"):
                    current = urljoin(current, response.headers["location"])
                    continue
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > self.settings.scrape_max_bytes:
                        break
                raw = b"".join(chunks)[: self.settings.scrape_max_bytes]
                return response, current, _decode(response, raw), chain
        raise httpx.TooManyRedirects("too many redirects")

    # ---- robots.txt ---------------------------------------------------------------------

    def _check_robots(self, url: str) -> None:
        if not self.settings.respect_robots or is_fixture_url(url, self.settings):
            return
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser: RobotFileParser | None = None
            body = self.get_text(f"{origin}/robots.txt")
            if body is not None and "<html" not in body[:500].lower():
                parser = RobotFileParser()
                parser.parse(body.splitlines())
            self._robots[origin] = parser
        parser = self._robots[origin]
        if parser is not None and not parser.can_fetch("*", url):
            raise FetchError("robots.txt disallows fetching this url")

    # ---- playwright ---------------------------------------------------------------------

    def _can_render(self, url: str) -> bool:
        return self.settings.playwright_enabled and transport is None

    def _render(self, url: str) -> FetchedPage:
        from app.scraper.browser import render_page

        fixture = is_fixture_url(url, self.settings)
        proxy = None if fixture else self.proxies.next()
        user_agent = self.user_agents.next()
        if not fixture:
            self.throttle.wait(urlsplit(url).hostname or "")
        rendered = render_page(url, user_agent=user_agent, proxy=proxy, settings=self.settings)
        return FetchedPage(
            requested_url=url,
            url=rendered.url,
            status=rendered.status,
            content_type="text/html",
            body=rendered.html[: self.settings.scrape_max_bytes],
            engine="playwright",
            user_agent=user_agent,
            proxy=redact_proxy(proxy),
            fetched_at=_now(),
            screenshot=rendered.screenshot,
            redirect_chain=rendered.redirect_chain,
        )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
