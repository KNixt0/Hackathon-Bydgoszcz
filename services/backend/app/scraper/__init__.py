"""Scraper engine: polite HTTP fetching (httpx, optional Playwright) + per-platform parsers."""

from app.scraper.engine import FetchedPage, Fetcher, FetchError
from app.scraper.ssrf import BlockedURL, check_url

__all__ = ["BlockedURL", "FetchError", "FetchedPage", "Fetcher", "check_url"]
