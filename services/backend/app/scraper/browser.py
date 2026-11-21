"""Headless Chromium via Playwright: JS rendering + screenshot, and HTML -> PDF for exports."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlsplit

from app.config import Settings, get_settings
from app.scraper.ssrf import BlockedURL, check_url

log = logging.getLogger(__name__)


class BrowserUnavailable(RuntimeError):
    pass


@dataclass
class Rendered:
    url: str
    status: int
    html: str
    screenshot: bytes | None
    redirect_chain: list[str] = field(default_factory=list)


def _launch_args(settings: Settings) -> list[str]:
    args = ["--disable-dev-shm-usage", "--disable-gpu"]
    if settings.chromium_no_sandbox:
        args.append("--no-sandbox")
    return args


def _proxy_option(proxy: str | None) -> dict | None:
    if not proxy:
        return None
    parts = urlsplit(proxy)
    host = parts.hostname or ""
    option = {"server": f"{parts.scheme}://{host}:{parts.port}" if parts.port else f"{parts.scheme}://{host}"}
    if parts.username:
        option["username"] = parts.username
        option["password"] = parts.password or ""
    return option


def render_page(
    url: str, *, user_agent: str, proxy: str | None, settings: Settings | None = None
) -> Rendered:
    settings = settings or get_settings()
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserUnavailable("playwright is not installed") from exc

    timeout_ms = int(settings.scrape_timeout_seconds * 1000)

    @lru_cache(maxsize=256)
    def allowed(origin_url: str) -> bool:
        try:
            check_url(origin_url, settings)
            return True
        except BlockedURL:
            return False

    def guard(route) -> None:  # type: ignore[no-untyped-def]
        request_url = route.request.url
        if request_url.startswith(("data:", "blob:", "about:")):
            route.continue_()
            return
        parts = urlsplit(request_url)
        if allowed(f"{parts.scheme}://{parts.netloc}/"):
            route.continue_()
        else:
            route.abort()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True, args=_launch_args(settings), proxy=_proxy_option(proxy)
            )
            try:
                context = browser.new_context(
                    user_agent=user_agent,
                    locale="pl-PL",
                    viewport={"width": 1366, "height": 900},
                    service_workers="block",
                )
                page = context.new_page()
                page.route("**/*", guard)
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                with contextlib.suppress(PlaywrightError):  # long-polling pages never go idle
                    page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 8000))
                html = page.content()
                screenshot: bytes | None
                try:
                    screenshot = page.screenshot(full_page=True, type="png", timeout=timeout_ms)
                except PlaywrightError:
                    screenshot = None
                chain: list[str] = []
                request = response.request if response else None
                while request is not None:
                    chain.insert(0, request.url)
                    request = request.redirected_from
                if page.url and (not chain or chain[-1] != page.url):
                    chain.append(page.url)  # JS / meta-refresh navigation after load
                return Rendered(
                    url=page.url,
                    status=response.status if response else 0,
                    html=html,
                    screenshot=screenshot,
                    redirect_chain=chain,
                )
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise BrowserUnavailable(f"browser error: {str(exc).splitlines()[0][:200]}") from exc


def html_to_pdf(html: str, settings: Settings | None = None) -> bytes:
    """Render a self-contained HTML document to an A4 PDF. Network access is blocked."""
    settings = settings or get_settings()
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserUnavailable("playwright is not installed") from exc
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=_launch_args(settings))
            try:
                context = browser.new_context(java_script_enabled=False, offline=True)
                page = context.new_page()
                page.route("**/*", lambda route: route.abort())
                page.set_content(html, wait_until="load")
                return page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
                    display_header_footer=True,
                    header_template="<span></span>",
                    footer_template=(
                        '<div style="font-size:8px;width:100%;text-align:center;color:#666;'
                        "font-family:'DejaVu Sans',sans-serif\">"
                        '#InvestWatch · strona <span class="pageNumber"></span> z '
                        '<span class="totalPages"></span>'
                        "</div>"
                    ),
                )
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise BrowserUnavailable(f"browser error: {str(exc).splitlines()[0][:200]}") from exc
