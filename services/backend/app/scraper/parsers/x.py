"""X (Twitter): OpenGraph + the public publish.twitter.com oEmbed (post text and author)."""

from __future__ import annotations

import json
import re
from urllib.parse import quote, urlsplit

from app.scraper.engine import FetchedPage
from app.scraper.extract import parse_html
from app.scraper.parsers.base import AuxFetch, ParsedDocument, PlatformParser, compose_text


class XParser(PlatformParser):
    platform = "x"
    hosts = ("x.com", "twitter.com")
    prefers_render = True

    def parse(self, page: FetchedPage, aux: AuxFetch | None = None) -> ParsedDocument:
        data = self.base(page)
        post, author = data.description, data.author
        if aux is not None and "/status/" in page.url:
            raw = aux(
                f"https://publish.twitter.com/oembed?omit_script=1&dnt=1&url={quote(page.url, safe='')}"
            )
            try:
                oembed = json.loads(raw) if raw else {}
            except ValueError:
                oembed = {}
            if oembed.get("html"):
                paragraph = parse_html(oembed["html"]).find("p")
                if paragraph:
                    post = paragraph.get_text(" ", strip=True)
            if oembed.get("author_name"):
                author = {"name": oembed["author_name"]}
                if oembed.get("author_url"):
                    author["url"] = oembed["author_url"]
                    author["handle"] = "@" + oembed["author_url"].rstrip("/").rsplit("/", 1)[-1]
        if author is None:
            handle = re.match(r"/([A-Za-z0-9_]{1,15})(?:/|$)", urlsplit(page.url).path)
            if handle and handle.group(1) not in ("i", "home", "search", "hashtag"):
                author = {"name": handle.group(1), "handle": "@" + handle.group(1)}
        return ParsedDocument(
            platform=self.platform,
            title=data.title or (post or "")[:120],
            text=compose_text(post, data.text),
            language=data.language,
            published_at=data.published_at,
            author=author,
        )
