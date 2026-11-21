"""TikTok: OpenGraph + the public oEmbed endpoint (caption and author)."""

from __future__ import annotations

import json
import re
from urllib.parse import quote, urlsplit

from app.scraper.engine import FetchedPage
from app.scraper.parsers.base import AuxFetch, ParsedDocument, PlatformParser, compose_text


class TikTokParser(PlatformParser):
    platform = "tiktok"
    hosts = ("tiktok.com",)
    prefers_render = True

    def parse(self, page: FetchedPage, aux: AuxFetch | None = None) -> ParsedDocument:
        data = self.base(page)
        title, caption, author = data.title, data.description, data.author
        if aux is not None:
            raw = aux(f"https://www.tiktok.com/oembed?url={quote(page.url, safe='')}")
            try:
                oembed = json.loads(raw) if raw else {}
            except ValueError:
                oembed = {}
            caption = oembed.get("title") or caption
            if oembed.get("author_name"):
                author = {"name": oembed["author_name"]}
                if oembed.get("author_url"):
                    author["url"] = oembed["author_url"]
                if oembed.get("author_unique_id"):
                    author["handle"] = "@" + oembed["author_unique_id"]
        if author is None:
            handle = re.search(r"/(@[\w.]+)", urlsplit(page.url).path)
            if handle:
                author = {"name": handle.group(1).lstrip("@"), "handle": handle.group(1)}
        return ParsedDocument(
            platform=self.platform,
            title=title or (caption or "")[:120],
            text=compose_text(caption, data.text),
            language=data.language,
            published_at=data.published_at,
            author=author,
        )
