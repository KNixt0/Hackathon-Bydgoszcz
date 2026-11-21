"""Parser strategy interface: one parser per platform, selected by URL."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.scraper.engine import FetchedPage
from app.scraper.extract import Extracted, extract

# Auxiliary GET used for oEmbed endpoints: url -> body, or None on any failure / when offline.
AuxFetch = Callable[[str], str | None]


@dataclass
class ParsedDocument:
    platform: str
    title: str
    text: str
    language: str | None = None
    published_at: str | None = None
    author: dict[str, str] | None = None


class PlatformParser(ABC):
    """Turn a fetched page into the platform-independent fields of a `Document`."""

    platform: str = "web"
    hosts: tuple[str, ...] = ()
    prefers_render: bool = False  # pages that are empty without JavaScript

    def matches(self, url: str) -> bool:
        host = (urlsplit(url).hostname or "").lower()
        return any(host == h or host.endswith("." + h) for h in self.hosts)

    @abstractmethod
    def parse(self, page: FetchedPage, aux: AuxFetch | None = None) -> ParsedDocument: ...

    # shared helper: generic extraction every parser starts from
    def base(self, page: FetchedPage) -> Extracted:
        if not page.is_html:
            return Extracted(text=page.body.strip())
        return extract(page.body)


def compose_text(*parts: str | None) -> str:
    """Join text fragments, dropping empties and fragments already contained in an earlier one."""
    kept: list[str] = []
    for part in parts:
        part = (part or "").strip()
        if part and not any(part in existing for existing in kept):
            kept.append(part)
    return "\n\n".join(kept)
