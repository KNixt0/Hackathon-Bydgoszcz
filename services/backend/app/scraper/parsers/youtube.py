"""YouTube: embedded player JSON (description, channel, date) + public oEmbed, no API key."""

from __future__ import annotations

import json
import re
from urllib.parse import quote

from app.scraper.engine import FetchedPage
from app.scraper.parsers.base import AuxFetch, ParsedDocument, PlatformParser, compose_text

_PLAYER_RE = re.compile(r"ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;\s*(?:var\s|</script>)", re.S)


def _player_response(html: str) -> dict:
    match = _PLAYER_RE.search(html)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


class YouTubeParser(PlatformParser):
    platform = "youtube"
    hosts = ("youtube.com", "youtu.be", "youtube-nocookie.com")

    def parse(self, page: FetchedPage, aux: AuxFetch | None = None) -> ParsedDocument:
        data = self.base(page)
        player = _player_response(page.body) if page.is_html else {}
        details = player.get("videoDetails") or {}
        micro = (player.get("microformat") or {}).get("playerMicroformatRenderer") or {}

        title = details.get("title") or data.title
        description = details.get("shortDescription") or data.description
        author = data.author
        channel = details.get("author") or micro.get("ownerChannelName")
        if channel:
            author = {"name": channel}
            if micro.get("ownerProfileUrl"):
                author["url"] = micro["ownerProfileUrl"]
                handle = micro["ownerProfileUrl"].rstrip("/").rsplit("/", 1)[-1]
                if handle.startswith("@"):
                    author["handle"] = handle
        published = micro.get("publishDate") or micro.get("uploadDate") or data.published_at

        if aux is not None and (not title or author is None):
            raw = aux(f"https://www.youtube.com/oembed?format=json&url={quote(page.url, safe='')}")
            try:
                oembed = json.loads(raw) if raw else {}
            except ValueError:
                oembed = {}
            title = title or oembed.get("title") or ""
            if author is None and oembed.get("author_name"):
                author = {"name": oembed["author_name"]}
                if oembed.get("author_url"):
                    author["url"] = oembed["author_url"]

        title = re.sub(r"\s+-\s+YouTube$", "", title or "")
        return ParsedDocument(
            platform=self.platform,
            title=title,
            text=compose_text(title, description, data.text if not details else None),
            language=data.language,
            published_at=published,
            author=author,
        )
