"""KNF public registers (URLs from the organiser's attachment 1): scrape -> snapshot -> AI service.

On any failure the previous snapshot is kept and a warning is logged, so the stack keeps
working offline.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from app import ai_client
from app.config import get_settings
from app.db import session_scope
from app.models import RegistrySnapshot, utcnow
from app.scraper import BlockedURL, Fetcher, FetchError
from app.scraper.extract import parse_html

log = logging.getLogger(__name__)

_BASE = "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/Firmy_inwestycyjne_i_Agenci_firm_inwestycyjnych"
UMBRELLA = "knf_investment_firms"
REGISTRIES: list[dict[str, str]] = [
    {"registry": UMBRELLA, "label": "Rejestr firm inwestycyjnych", "url": _BASE},
    {
        "registry": "knf_banks_brokerage",
        "label": "Banki prowadzące działalność maklerską",
        "url": f"{_BASE}/Banki_prowadzace_dzialalnosc_maklerska",
    },
    {"registry": "knf_brokerage_houses", "label": "Domy maklerskie", "url": f"{_BASE}/domy_maklerskie"},
    {
        "registry": "knf_foreign_branches",
        "label": "Oddziały zagranicznych firm inwestycyjnych",
        "url": f"{_BASE}/notyfikowane_firmy_inwestycyjne_oddzialy",
    },
    {
        "registry": "knf_foreign_cross_border",
        "label": "Zagraniczne firmy inwestycyjne bez otwierania oddziału",
        "url": f"{_BASE}/notyfikowane_zagraniczne_firmy_inwestycyjne",
    },
]
_NAME_LABELS = ("nazwa", "nazwa podmiotu", "firma")
_DETAIL_LABELS = ("państwo macierzyste", "data zezwolenia", "data wpływu zawiadomienia", "organ nadzoru")
_PAGE_RE = re.compile(r"[?&]page=(\d+)")
_WS = re.compile(r"\s+")


class RegistryError(Exception):
    pass


def parse_register_page(html: str) -> tuple[list[dict], int]:
    """Entries on one register page + the highest page number linked from its pagination.

    The KNF site renders one small table per entity inside #entityTable: rows of
    <th>label</th><td>value</td>; former names are struck through in the name cell.
    """
    soup = parse_html(html)
    container = soup.find(id="entityTable") or soup
    entries: list[dict] = []
    for table in container.find_all("table"):
        name, aliases, details = "", [], []
        for row in table.find_all("tr"):
            header, cell = row.find("th"), row.find("td")
            if header is None or cell is None:
                continue
            label = _WS.sub(" ", header.get_text(" ", strip=True)).lower()
            if label in _NAME_LABELS and not name:
                for struck in cell.find_all(["strike", "s", "del"]):
                    alias = _WS.sub(" ", struck.get_text(" ", strip=True))
                    if alias:
                        aliases.append(alias)
                    struck.decompose()
                lines = [_WS.sub(" ", line).strip() for line in cell.get_text("\n").split("\n")]
                lines = [line for line in lines if line]
                if lines:
                    name, aliases = lines[0], aliases + lines[1:]
            elif label in _DETAIL_LABELS:
                value = _WS.sub(" ", cell.get_text(" ", strip=True))
                if value and value != "-":
                    details.append(f"{header.get_text(' ', strip=True)}: {value[:120]}")
        if name:
            entry: dict = {"name": name[:300], "status": "listed"}
            if aliases:
                entry["aliases"] = [a[:300] for a in aliases[:10]]
            if details:
                entry["detail"] = "; ".join(details)[:500]
            entries.append(entry)
    pages = [int(n) for n in _PAGE_RE.findall(" ".join(a.get("href", "") for a in soup.find_all("a")))]
    return entries, max(pages, default=1)


def scrape_registry(fetcher: Fetcher, url: str, max_pages: int) -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()
    page_number, last_page = 1, 1
    while page_number <= min(last_page, max_pages):
        page_url = url if page_number == 1 else f"{url}?page={page_number}"
        try:
            page = fetcher.fetch(page_url)
        except (FetchError, BlockedURL) as exc:
            raise RegistryError(f"page {page_number}: {exc}") from exc
        if page.status != 200:
            raise RegistryError(f"page {page_number}: http status {page.status}")
        found, linked_last = parse_register_page(page.body)
        last_page = max(last_page, linked_last)
        for entry in found:
            if entry["name"] not in seen:
                seen.add(entry["name"])
                entries.append(entry)
        page_number += 1
    return entries


def _store_snapshot(spec: dict[str, str], entries: list[dict], snapshot_date: str) -> None:
    with session_scope() as db:
        db.merge(
            RegistrySnapshot(
                name=spec["registry"],
                label=spec["label"],
                url=spec["url"],
                snapshot_date=snapshot_date,
                entries=entries,
                pushed_to_ai=False,
                updated_at=utcnow(),
            )
        )


def push_pending() -> list[str]:
    """Send snapshots the AI service has not received yet. Failures are logged and retried next run."""
    pushed: list[str] = []
    with session_scope() as db:
        pending = [
            (s.name, s.snapshot_date, s.entries)
            for s in db.query(RegistrySnapshot).filter_by(pushed_to_ai=False)
        ]
    for registry, snapshot_date, entries in pending:
        try:
            ai_client.put_registry(registry, snapshot_date, entries)
        except (ai_client.AIUnavailable, ai_client.AIRejected) as exc:
            log.warning("registry not pushed to AI service", extra={"registry": registry, "error": str(exc)})
            continue
        with session_scope() as db:
            snapshot = db.get(RegistrySnapshot, registry)
            if snapshot:
                snapshot.pushed_to_ai = True
        pushed.append(registry)
    return pushed


def refresh_all(fetcher: Fetcher | None = None) -> dict:
    """Scrape all registers. Returns {"updated": [...], "kept": [...], "pushed": [...]}."""
    settings = get_settings()
    fetcher = fetcher or Fetcher(settings)
    today = datetime.now(UTC).date().isoformat()
    updated: list[str] = []
    kept: list[str] = []
    scraped: dict[str, list[dict]] = {}
    for spec in REGISTRIES:
        try:
            entries = scrape_registry(fetcher, spec["url"], settings.registry_max_pages)
        except RegistryError as exc:
            log.warning(
                "registry refresh failed, keeping previous snapshot",
                extra={"registry": spec["registry"], "error": str(exc)},
            )
            if spec["registry"] != UMBRELLA:
                kept.append(spec["registry"])
            continue
        scraped[spec["registry"]] = entries

    # The umbrella page is an index: the register of investment firms is the union of the four lists.
    parts = [s for s in REGISTRIES if s["registry"] != UMBRELLA]
    if all(len(scraped.get(s["registry"], [])) >= settings.registry_min_entries for s in parts):
        union = list(scraped.get(UMBRELLA, []))
        names = {e["name"] for e in union}
        for spec in parts:
            for entry in scraped[spec["registry"]]:
                if entry["name"] not in names:
                    names.add(entry["name"])
                    detail = f"{spec['label']}; {entry['detail']}" if entry.get("detail") else spec["label"]
                    union.append({**entry, "detail": detail[:500]})
        scraped[UMBRELLA] = union
    else:
        scraped.pop(UMBRELLA, None)
        kept.append(UMBRELLA)

    for spec in REGISTRIES:
        entries = scraped.get(spec["registry"])
        if entries is None:
            continue
        if len(entries) < settings.registry_min_entries:
            log.warning(
                "registry page had too few entries, keeping previous snapshot",
                extra={"registry": spec["registry"], "entries": len(entries)},
            )
            kept.append(spec["registry"])
            continue
        _store_snapshot(spec, entries, today)
        updated.append(spec["registry"])
    pushed = push_pending()
    log.info(
        "registry refresh done", extra={"updated": len(updated), "kept": len(kept), "pushed": len(pushed)}
    )
    return {"updated": updated, "kept": sorted(set(kept)), "pushed": pushed}


def local_registry_list() -> list[dict]:
    """Fallback for GET /api/registries when the AI service is unreachable."""
    with session_scope() as db:
        snapshots = {s.name: s for s in db.query(RegistrySnapshot).all()}
    items = []
    for spec in REGISTRIES:
        snapshot = snapshots.get(spec["registry"])
        items.append(
            {
                **spec,
                "entries": len(snapshot.entries) if snapshot else 0,
                "snapshot_date": snapshot.snapshot_date if snapshot else None,
            }
        )
    return items
