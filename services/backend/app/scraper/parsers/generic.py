"""Generic web page parser: visible text + OpenGraph / JSON-LD / meta tags."""

from __future__ import annotations

from app.scraper.engine import FetchedPage
from app.scraper.parsers.base import AuxFetch, ParsedDocument, PlatformParser, compose_text


class GenericParser(PlatformParser):
    platform = "web"

    def matches(self, url: str) -> bool:
        return True

    def parse(self, page: FetchedPage, aux: AuxFetch | None = None) -> ParsedDocument:
        data = self.base(page)
        text = data.text
        if len(text) < 200:  # thin page: the description is most of the content
            text = compose_text(data.description, text)
        title = data.title or (text.splitlines()[0][:120] if text else "")
        return ParsedDocument(
            platform=self.platform,
            title=title,
            text=text,
            language=data.language,
            published_at=data.published_at,
            author=data.author,
        )
