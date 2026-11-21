"""Refresh the four public KNF investment-firm registers into data/registries/*.json.

Usage:  python scripts/fetch_knf_registers.py [--cache raw.json] [--out data/registries]

Standard library only. The pages are server-rendered tables: one table per entity, first
row = name (further lines in that cell are former / trading names, kept as aliases).
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/Firmy_inwestycyjne_i_Agenci_firm_inwestycyjnych"
SOURCES = {
    "knf_banks_brokerage": (
        "Banki prowadzące działalność maklerską (KNF)",
        BASE + "/Banki_prowadzace_dzialalnosc_maklerska",
    ),
    "knf_brokerage_houses": ("Domy maklerskie (KNF)", BASE + "/domy_maklerskie"),
    "knf_foreign_branches": (
        "Oddziały zagranicznych firm inwestycyjnych (KNF)",
        BASE + "/notyfikowane_firmy_inwestycyjne_oddzialy",
    ),
    "knf_foreign_cross_border": (
        "Zagraniczne firmy inwestycyjne bez otwierania oddziału (KNF)",
        BASE + "/notyfikowane_zagraniczne_firmy_inwestycyjne",
    ),
}
DETAIL_ROWS = ("Data zezwolenia", "Państwo macierzyste", "Organ nadzoru", "Data wpływu zawiadomienia")


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (register-snapshot-client)"})
    last: Exception | None = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return resp.read().decode("utf-8", "replace")
        except OSError as exc:
            last = exc
            time.sleep(2)
    raise RuntimeError(f"cannot fetch {url}: {last}")


def cell_lines(cell: str) -> list[str]:
    cell = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", cell)
    cell = html.unescape(re.sub(r"<[^>]+>", "", cell)).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", line).strip() for line in cell.split("\n") if line.strip()]


def parse_tables(page: str) -> list[list[list[list[str]]]]:
    tables = []
    for table in re.findall(r"<table.*?</table>", page, re.S):
        rows = []
        for tr in re.findall(r"<tr.*?</tr>", table, re.S):
            rows.append([cell_lines(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)])
        tables.append(rows)
    return tables


def fetch_all() -> dict:
    raw = {}
    for registry, (_, url) in SOURCES.items():
        first = get(url)
        pages = [first]
        last = max([int(n) for n in re.findall(r"\?page=(\d+)", first)] or [1])
        for page_no in range(2, last + 1):
            time.sleep(0.4)
            pages.append(get(f"{url}?page={page_no}"))
        raw[registry] = {"pages": last, "tables": [t for p in pages for t in parse_tables(p)]}
        print(registry, "pages:", last, "entities:", len(raw[registry]["tables"]), file=sys.stderr)
    return raw


def to_entries(tables: list) -> list[dict]:
    entries = []
    for rows in tables:
        if not rows or len(rows[0]) < 2 or not rows[0][1]:
            continue
        names = rows[0][1]
        details = []
        for row in rows[1:]:
            if len(row) >= 2 and row[0] and row[0][0] in DETAIL_ROWS and row[1]:
                details.append(f"{row[0][0]}: {' '.join(row[1])}")
        entries.append(
            {
                "name": names[0],
                "aliases": names[1:],
                "status": "listed",
                "detail": "; ".join(details),
            }
        )
    return entries


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, help="raw table dump to reuse / create")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "registries")
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="snapshot date (day of fetch)")
    args = ap.parse_args()
    if args.cache and args.cache.is_file():
        raw = json.loads(args.cache.read_text(encoding="utf-8"))
    else:
        raw = fetch_all()
        if args.cache:
            args.cache.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    args.out.mkdir(parents=True, exist_ok=True)
    for registry, (label, url) in SOURCES.items():
        entries = to_entries(raw[registry]["tables"])
        payload = {
            "registry": registry,
            "label": label,
            "url": url,
            "snapshot_date": args.date,
            "source": "official KNF page, fetched by scripts/fetch_knf_registers.py",
            "partial": False,
            "synthetic_sample": False,
            "entries": entries,
        }
        (args.out / f"{registry}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(registry, len(entries), file=sys.stderr)


if __name__ == "__main__":
    main()
