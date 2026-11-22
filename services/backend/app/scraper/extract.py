"""HTML -> title, visible text and metadata (OpenGraph, JSON-LD, meta tags, language)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment

_DROP_TAGS = ("script", "style", "noscript", "template", "svg", "iframe", "head", "canvas", "object")
_BLOCK_TAGS = (
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "main",
    "aside",
    "nav",
    "li",
    "ul",
    "ol",
    "tr",
    "table",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "pre",
    "br",
    "hr",
    "figcaption",
    "dd",
    "dt",
    "form",
    "td",
    "th",
)
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
_WS = re.compile(r"[ \t\r\f\v ]+")
_PL_CHARS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
_PL_WORDS = {"i", "w", "na", "z", "do", "się", "nie", "że", "jest", "to", "oraz", "dla", "jak", "od", "po"}
_EN_WORDS = {"the", "and", "of", "to", "in", "is", "for", "that", "with", "on", "you", "this", "are"}
_DE_WORDS = {"der", "die", "und", "das", "ist", "nicht", "mit", "für", "auf", "ein", "eine", "den"}


@dataclass
class Extracted:
    title: str = ""
    text: str = ""
    description: str = ""
    language: str | None = None
    published_at: str | None = None
    author: dict[str, str] | None = None
    og: dict[str, str] = field(default_factory=dict)
    jsonld: list[dict[str, Any]] = field(default_factory=list)
    site_name: str | None = None


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "html.parser")


def _meta_map(soup: BeautifulSoup) -> dict[str, str]:
    values: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name") or tag.get("itemprop")
        content = tag.get("content")
        if key and isinstance(content, str) and content.strip():
            values.setdefault(str(key).strip().lower(), content.strip())
    return values


def _jsonld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(node: Any, depth: int = 0) -> None:
        if depth > 6:
            return
        if isinstance(node, list):
            for item in node:
                walk(item, depth + 1)
        elif isinstance(node, dict):
            found.append(node)
            if "@graph" in node:
                walk(node["@graph"], depth + 1)

    for tag in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            walk(json.loads(raw))
        except (ValueError, RecursionError):
            continue
    return found


def _types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {str(v) for v in value}
    return set()


_CONTENT_TYPES = {
    "Article",
    "NewsArticle",
    "BlogPosting",
    "VideoObject",
    "SocialMediaPosting",
    "WebPage",
    "Product",
    "Report",
    "AdvertiserContentArticle",
    "FinancialProduct",
    "Review",
    "CreativeWork",
}


def _metadata_host(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
        return parts.hostname if parts.scheme in ("http", "https") else None
    except ValueError:
        return None


def _author_from(value: Any) -> dict[str, str] | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, str) and value.strip():
        return {"name": value.strip()}
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            author = {"name": name.strip()}
            url = value.get("url") or value.get("sameAs")
            if isinstance(url, list):
                url = url[0] if url else None
            if isinstance(url, str) and url.startswith("http"):
                author["url"] = url
            handle = value.get("alternateName") or value.get("identifier")
            if isinstance(handle, str) and handle.startswith("@"):
                author["handle"] = handle
            return author
    return None


def visible_text(soup: BeautifulSoup) -> str:
    """Text a reader would see: no scripts/styles/hidden nodes, blocks separated by newlines."""
    body = soup.body or soup
    for comment in body.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    for tag in body.find_all(_DROP_TAGS):
        tag.decompose()
    for tag in body.find_all(True):
        if tag.attrs is None:
            continue
        if tag.has_attr("hidden") or _HIDDEN_STYLE.search(str(tag.get("style") or "")):
            tag.decompose()
    for tag in body.find_all(_BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")
    lines = (_WS.sub(" ", line).strip() for line in body.get_text().split("\n"))
    return "\n".join(line for line in lines if line)


def guess_language(text: str) -> str | None:
    sample = text[:4000]
    if not sample.strip():
        return None
    words = re.findall(r"[^\W\d_]+", sample.lower())
    if not words:
        return None
    scores = {
        "pl": sum(w in _PL_WORDS for w in words) + 2 * sum(c in _PL_CHARS for c in sample),
        "en": sum(w in _EN_WORDS for w in words),
        "de": sum(w in _DE_WORDS for w in words) + sum(c in "äöüßÄÖÜ" for c in sample),
    }
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else None


def _normalise_lang(value: str | None) -> str | None:
    if not value:
        return None
    code = re.split(r"[-_]", value.strip())[0].lower()
    return code if 2 <= len(code) <= 3 and code.isalpha() else None


def extract(html: str) -> Extracted:
    soup = parse_html(html)
    meta = _meta_map(soup)
    jsonld = _jsonld(soup)
    content_nodes = [n for n in jsonld if _types(n) & _CONTENT_TYPES]
    og = {k[3:]: v for k, v in meta.items() if k.startswith("og:")}

    def ld(*keys: str) -> Any:
        for node in content_nodes:
            for key in keys:
                if node.get(key):
                    return node[key]
        return None

    title_tag = soup.title.get_text(strip=True) if soup.title else ""
    h1 = soup.find("h1")
    ld_title = ld("headline", "name")
    title = (
        og.get("title")
        or meta.get("twitter:title")
        or (ld_title if isinstance(ld_title, str) else "")
        or title_tag
        or (h1.get_text(" ", strip=True) if h1 else "")
    )

    ld_description = ld("description")
    description = (
        og.get("description")
        or meta.get("description")
        or meta.get("twitter:description")
        or (ld_description if isinstance(ld_description, str) else "")
    )

    published = (
        meta.get("article:published_time")
        or meta.get("og:article:published_time")
        or ld("datePublished", "uploadDate", "dateCreated")
        or meta.get("datepublished")
        or meta.get("date")
        or meta.get("dc.date")
        or meta.get("pubdate")
    )
    if not published:
        time_tag = soup.find("time", attrs={"datetime": True})
        published = time_tag.get("datetime") if time_tag else None

    author = _author_from(ld("author", "creator"))
    if author is None:
        for node in jsonld:
            if _types(node) & {"Person", "Organization"} and node.get("name") and len(jsonld) == 1:
                author = _author_from(node)
    if author is None:
        name = meta.get("author") or meta.get("article:author") or meta.get("dc.creator")
        if name and not name.startswith("http"):
            author = {"name": name}
    if author is None:
        # A page-level organization paired with its own WebSite identifies the publisher.
        # Do not promote a social handle to a different legal person when this exists.
        organizations = [node for node in jsonld if "Organization" in _types(node) and node.get("name")]
        websites = [node for node in jsonld if "WebSite" in _types(node)]
        if len(organizations) == 1:
            organization = organizations[0]
            organization_url = organization.get("url")
            if isinstance(organization_url, str):
                host = _metadata_host(organization_url)
                if host and any(_metadata_host(site.get("url")) == host for site in websites):
                    author = _author_from(organization)
    handle = meta.get("twitter:creator") or meta.get("twitter:site")
    if handle and handle.startswith("@"):
        author = {**(author or {"name": handle.lstrip("@")}), "handle": handle}

    html_tag = soup.find("html")
    ld_language = ld("inLanguage")
    language = (
        _normalise_lang(html_tag.get("lang") if html_tag else None)
        or _normalise_lang(og.get("locale"))
        or _normalise_lang(ld_language if isinstance(ld_language, str) else None)
        or _normalise_lang(meta.get("content-language") or meta.get("language"))
    )

    text = visible_text(soup)  # mutates the soup: keep last
    if language is None:
        language = guess_language(text or description)

    return Extracted(
        title=_WS.sub(" ", str(title)).strip()[:500],
        text=text,
        description=str(description).strip(),
        language=language,
        published_at=str(published).strip() if published else None,
        author=author,
        og=og,
        jsonld=jsonld,
        site_name=og.get("site_name"),
    )


def looks_js_empty(html: str, text: str) -> bool:
    """True when a page is a JS shell: (almost) no visible text but scripts / an app root."""
    if len(text) >= 200:
        return False
    lowered = html.lower()
    if "<script" not in lowered:
        return False
    markers = (
        'id="root"',
        'id="app"',
        'id="__next"',
        "enable javascript",
        "włącz javascript",
        "data-reactroot",
    )
    return len(text) < 60 or any(marker in lowered for marker in markers)
