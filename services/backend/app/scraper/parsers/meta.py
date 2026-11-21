"""Meta properties: Facebook (incl. Ad Library) and Instagram. OpenGraph based; these pages
need JavaScript for anything beyond the preview tags, so they ask for rendering."""

from __future__ import annotations

import re

from app.scraper.engine import FetchedPage
from app.scraper.parsers.base import AuxFetch, ParsedDocument, PlatformParser, compose_text

# "1,234 likes, 56 comments - handle on November 1, 2026: "caption""
_IG_DESCRIPTION = re.compile(
    r"^.*?-\s*(?P<handle>[\w.]+)\s+(?:on|w dniu)\s+.*?:\s*[\"“](?P<caption>.*)[\"”]\s*\.?$", re.S
)


class _MetaParser(PlatformParser):
    prefers_render = True

    def parse(self, page: FetchedPage, aux: AuxFetch | None = None) -> ParsedDocument:
        data = self.base(page)
        author = data.author
        caption = data.description
        match = _IG_DESCRIPTION.match(caption or "")
        if match:
            caption = match.group("caption")
            author = author or {"name": match.group("handle"), "handle": "@" + match.group("handle")}
        if author is None and data.og.get("title"):
            # "Name (@handle) • Instagram photos and videos" / "Name | Facebook"
            name = re.split(r"\s[|•·]\s|\son Instagram", data.og["title"])[0].strip()
            handle = re.search(r"\(@([\w.]+)\)", name)
            if name:
                author = {"name": re.sub(r"\s*\(@[\w.]+\)", "", name) or name}
                if handle:
                    author["handle"] = "@" + handle.group(1)
        return ParsedDocument(
            platform=self.platform,
            title=data.title,
            text=compose_text(caption, data.text),
            language=data.language,
            published_at=data.published_at,
            author=author,
        )


class FacebookParser(_MetaParser):
    """facebook.com pages, posts and the Ad Library (facebook.com/ads/library)."""

    platform = "facebook"
    hosts = ("facebook.com", "fb.com", "fb.watch")


class InstagramParser(_MetaParser):
    platform = "instagram"
    hosts = ("instagram.com",)
