"""Parser registry. Add a platform by appending a PlatformParser subclass to PARSERS."""

from __future__ import annotations

from urllib.parse import urlsplit

from app.scraper.parsers.base import AuxFetch, ParsedDocument, PlatformParser
from app.scraper.parsers.generic import GenericParser
from app.scraper.parsers.meta import FacebookParser, InstagramParser
from app.scraper.parsers.tiktok import TikTokParser
from app.scraper.parsers.x import XParser
from app.scraper.parsers.youtube import YouTubeParser

GENERIC = GenericParser()
PARSERS: list[PlatformParser] = [
    YouTubeParser(),
    InstagramParser(),
    FacebookParser(),
    TikTokParser(),
    XParser(),
]


def select_parser(url: str) -> PlatformParser:
    for parser in PARSERS:
        if parser.matches(url):
            return parser
    return GENERIC


def detect_platform(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host == "adstransparency.google.com":
        return "google_ads"
    return select_parser(url).platform


__all__ = [
    "GENERIC",
    "PARSERS",
    "AuxFetch",
    "ParsedDocument",
    "PlatformParser",
    "detect_platform",
    "select_parser",
]
