"""Discovery ("wyszukiwanie"): find new material to analyse instead of waiting for a pasted URL.

A discovery source is a seed page per module: a search-result page, an ad-library page, a
channel or listing page, optionally with keywords. Each run fetches the page through the
normal scraper (User-Agent/proxy rotation, robots.txt, politeness, SSRF guard), collects the
links, keeps those whose anchor text or URL matches a keyword, and queues a scan for every
link that was not seen before (capped per source and run).
"""

from __future__ import annotations

import logging
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db import session_scope
from app.incidents import url_hash
from app.jobs import create_job, create_sample_job, dispatch
from app.models import DiscoveredLink, DiscoverySource, Incident, ScanJob, utcnow
from app.samples import DISCOVERY_DIR, Sample, discover, samples_root
from app.scraper import BlockedURL, FetchError, check_url
from app.scraper.extract import parse_html
from app.scraper.ssrf import is_fixture_url

log = logging.getLogger(__name__)

_SKIP_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".pdf",
    ".zip",
    ".mp4",
    ".mp3",
    ".woff",
    ".woff2",
    ".xml",
    ".json",
)


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """(absolute url, anchor text) for every http(s) link on the page, in page order, de-duplicated."""
    soup = parse_html(html)
    base_tag = soup.find("base", href=True)
    base = urljoin(base_url, base_tag["href"]) if base_tag else base_url
    own = urldefrag(base_url)[0]
    links: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        try:
            url = urldefrag(urljoin(base, href))[0]
            parts = urlsplit(url)
        except ValueError:
            continue
        if parts.scheme not in ("http", "https") or not parts.hostname or url == own or len(url) > 2048:
            continue
        if parts.path.lower().endswith(_SKIP_EXTENSIONS):
            continue
        text = " ".join(anchor.get_text(" ", strip=True).split())
        title = str(anchor.get("title") or anchor.get("aria-label") or "")
        links.setdefault(url, f"{text} {title}".strip())
    return list(links.items())


def matches_keywords(url: str, text: str, keywords: list[str]) -> bool:
    """No keywords = every link is a candidate; otherwise any keyword in the anchor text or URL."""
    wanted = [k.casefold().strip() for k in keywords if isinstance(k, str) and k.strip()]
    if not wanted:
        return True
    haystack = f"{text} {unquote(url)}".casefold()
    return any(keyword in haystack for keyword in wanted)


def _sample_index() -> dict[str, Sample]:
    """fixture url -> sample, so a discovered offline page keeps its context (and seed flag)."""
    return {sample.fixture_url: sample for sample in discover()}


def _seen(db, url: str) -> bool:  # type: ignore[no-untyped-def]
    digest = url_hash(url)
    if db.get(DiscoveredLink, digest) is not None:
        return True
    if db.query(Incident.id).filter(Incident.source_url_hash == digest).first():
        return True
    return db.query(ScanJob.id).filter(ScanJob.url == url).first() is not None


def run_source(source_id: str) -> list[str]:
    """Fetch one source and queue scans for its new links. Returns the job ids."""
    from app.pipeline import get_fetcher

    settings = get_settings()
    with session_scope() as db:
        source = db.get(DiscoverySource, source_id)
        if source is None:
            return []
        db.expunge(source)

    error: str | None = None
    candidates: list[tuple[str, str]] = []
    try:
        page = get_fetcher().fetch(source.url, render=source.render)
        if page.status >= 400:
            error = f"http status {page.status}"
        elif page.is_html:
            candidates = extract_links(page.body, page.url)
    except (FetchError, BlockedURL) as exc:
        error = str(exc)

    samples = _sample_index() if candidates and is_fixture_url(source.url) else {}
    cap = source.max_links or settings.discovery_max_links
    queued: list[tuple[str, Sample | None]] = []
    with session_scope() as db:
        for url, text in candidates:
            if len(queued) >= cap:
                break
            if not matches_keywords(url, text, source.keywords or []):
                continue
            try:
                check_url(url, settings)
            except BlockedURL:
                continue
            sample = samples.get(url)
            if sample is not None and not sample.seed:
                continue  # reserved for the live demo trigger
            canonical = sample.url if sample else url
            if _seen(db, canonical):
                continue
            db.add(DiscoveredLink(url_hash=url_hash(canonical), url=canonical, source_id=source.id))
            db.flush()
            queued.append((url, sample))
        stored = db.get(DiscoverySource, source_id)
        if stored is not None:
            stored.last_run_at, stored.last_found, stored.last_error = utcnow(), len(queued), error

    job_ids: list[str] = []
    for url, sample in queued:
        if sample is not None:
            job_ids.append(create_sample_job(sample, backdate=False))
        else:
            offline = is_fixture_url(url)  # demo material served by this backend: always synthetic
            job_ids.append(
                create_job(
                    url,
                    origin="sample" if offline else "discovery",
                    module_hint=source.module_hint,
                    context={"synthetic": True} if offline else None,
                )
            )
    for job_id in job_ids:
        dispatch(job_id)
    if error:
        log.warning("discovery source failed", extra={"source_id": source_id, "error": error})
    else:
        log.info(
            "discovery source done",
            extra={"source_id": source_id, "links": len(candidates), "queued": len(job_ids)},
        )
    return job_ids


def run_discovery() -> dict:
    """Run every source. One failing source never stops the others."""
    with session_scope() as db:
        source_ids = [s.id for s in db.query(DiscoverySource).order_by(DiscoverySource.created_at).all()]
    job_ids: list[str] = []
    for source_id in source_ids:
        try:
            job_ids.extend(run_source(source_id))
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "discovery source crashed", extra={"source_id": source_id, "error": type(exc).__name__}
            )
    return {"sources": len(source_ids), "queued": len(job_ids), "job_ids": job_ids}


def add_source(
    url: str,
    *,
    module_hint: int | None = None,
    keywords: list[str] | None = None,
    max_links: int | None = None,
    render: bool = False,
) -> DiscoverySource:
    """Insert or update (same url) a source."""
    digest = url_hash(url)
    for _ in range(2):
        try:
            with session_scope() as db:
                source = db.query(DiscoverySource).filter(DiscoverySource.url_hash == digest).first()
                if source is None:
                    source = DiscoverySource(url=url, url_hash=digest)
                    db.add(source)
                source.module_hint, source.render = module_hint, render
                source.keywords = [k.strip() for k in keywords or [] if k.strip()]
                source.max_links = max_links or get_settings().discovery_max_links
                db.flush()
                db.expunge(source)
                return source
        except IntegrityError:  # another container inserted it at the same moment
            continue
    raise RuntimeError("could not store discovery source")


def register_fixture_source() -> bool:
    """Offline demo: SAMPLES_DIR/discovery/index.html (if present) becomes a discovery source."""
    try:
        if not (samples_root() / DISCOVERY_DIR / "index.html").is_file():
            return False
        url = f"{get_settings().fixture_base_url}/fixtures/{DISCOVERY_DIR}/index.html"
        with session_scope() as db:
            if db.query(DiscoverySource.id).filter(DiscoverySource.url_hash == url_hash(url)).first():
                return False
        add_source(url, keywords=get_settings().discovery_keyword_list)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("fixture discovery source not registered", extra={"error": type(exc).__name__})
        return False
