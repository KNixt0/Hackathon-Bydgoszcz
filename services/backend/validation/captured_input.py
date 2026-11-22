"""Replay only the three previously fetched documents; no network fallback is allowed."""

from app.scraper.engine import FetchedPage, FetchError


class CapturedFetcher:
    def __init__(self, documents):
        self.documents = {document["url"]: document for document in documents}

    def fetch(self, url, render=False):
        if url not in self.documents:
            raise FetchError("URL is absent from the bounded capture")
        document = self.documents[url]
        return FetchedPage(
            requested_url=url,
            url=url,
            status=200,
            content_type="text/html; charset=utf-8",
            body=document["html"],
            engine="httpx",
            user_agent="Watchit offline capture replay",
            proxy=None,
            fetched_at=document["fetched_at"],
        )

    def get_text(self, url):
        return None
