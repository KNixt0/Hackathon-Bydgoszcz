"""Refresh the public KNF registers into data/registries/*.json: the four investment-firm
registers and the public warnings list ("Lista ostrzeżeń publicznych KNF").

Usage:  python scripts/fetch_knf_registers.py [--cache raw.json] [--out data/registries]
                                              [--only knf_public_warnings]

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
WARNINGS_ID = "knf_public_warnings"
WARNINGS_LABEL = "Lista ostrzeżeń publicznych KNF"
WARNINGS_URL = "https://www.knf.gov.pl/dla_konsumenta/ostrzezenia_publiczne"
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


def fetch_all(only: str | None = None) -> dict:
    raw = {}
    if only in (None, WARNINGS_ID):
        raw[WARNINGS_ID] = fetch_warnings()
    for registry, (_, url) in SOURCES.items():
        if only and registry != only:
            continue
        first = get(url)
        pages = [first]
        last = max([int(n) for n in re.findall(r"\?page=(\d+)", first)] or [1])
        for page_no in range(2, last + 1):
            time.sleep(0.4)
            pages.append(get(f"{url}?page={page_no}"))
        raw[registry] = {"pages": last, "tables": [t for p in pages for t in parse_tables(p)]}
        print(registry, "pages:", last, "entities:", len(raw[registry]["tables"]), file=sys.stderr)
    return raw


_DOMAIN = re.compile(r"(?:https?://)?((?:www\.)?[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.[a-z]{2,})(?:/\S*)?", re.I)
_NAME_TAIL = re.compile(
    r"\s+(?:z siedzibą\b|prowadząc\w+|działając\w+|administrator\b|wykorzystując\w*|za pośrednictwem\b|"
    r"poprzez\b|przez stronę\b|przy użyciu\b|działalność\b|wykonując\w*|podmiot zarejestrowany|z wykorzystaniem\b|"
    r"w zw\.|pod stroną\b|pod marką\b|with its\b)|\s*/\s*(?:prowadząc|działając)|\s+-\s*\(|,\s+\d",
    re.I,
)
_FORMER = re.compile(r"\(([^()]+)\)")
_NOT_ALIAS = re.compile(r"działając|prowadząc|www\.|https?:|strony|stron\b|platform|siedzib", re.I)
_NO_NUMBER = ("brak danych", "podmiot")
_LEAD_NO = re.compile(r"^\d+\.\s*")


def _warning_names(cell: list[str]) -> list[str]:
    """One table cell can list several entities ("1. A", "2. B"); otherwise it is one."""
    if len(cell) > 1 and all(re.match(r"\d+\.\s", c) for c in cell):
        return [re.sub(r"^\d+\.\s*", "", c) for c in cell]
    return [" ".join(cell)]


def warning_entries(tables: list) -> list[dict]:
    """Rows: Lp. | name | KRS/NIP/REGON | prosecutor | rulings | relevant info."""
    entries = []
    for rows in tables:
        for row in rows[1:]:
            if len(row) < 6 or not row[1]:
                continue
            ids = row[2]
            info = " ".join(row[5]).strip()
            prosecutor = " ".join(row[3]).strip()
            names = _warning_names(row[1])
            for i, raw_name in enumerate(names):
                core = _NAME_TAIL.split(raw_name, maxsplit=1)[0]
                core = re.sub(r"\s*\([^()]*(?:www\.|http|strony|stron\b|platform|działal|prowadz)[^()]*\)?", "", core)
                core = re.sub(r"\s*\($", "", core).strip(' ,;-–„”"/')
                aliases: list[str] = []
                for m in _FORMER.finditer(raw_name):
                    inner = m.group(1).strip()
                    if inner and not _NOT_ALIAS.search(inner):
                        aliases += [
                            x.strip(" /.")
                            for x in re.sub(r"^(?:obecnie|wcześniej|dawniej|poprzednio)\s+", "", inner).split(",")
                        ]
                        core = core.replace(m.group(0), "").strip()
                domains = []
                for m in _DOMAIN.finditer(raw_name):
                    host = m.group(1).lower().removeprefix("www.")
                    if host not in domains:
                        domains.append(host)
                aliases = [x for x in dict.fromkeys(aliases) if x] + domains
                if not core or core.lower() in ("podmiot", "podmioty") or _NOT_ALIAS.match(core):
                    core = domains[0] if domains else raw_name
                ident = ids[i] if len(ids) == len(names) and len(names) > 1 else "; ".join(ids)
                ident = _LEAD_NO.sub("", ident).strip()
                detail = "; ".join(
                    x for x in (info.rstrip("."), f"prokuratura: {prosecutor}" if prosecutor else "") if x
                )
                entry = {"name": core, "aliases": aliases, "status": "warning", "detail": detail}
                if ident and not ident.lower().startswith(_NO_NUMBER) and "nie jest zarejestrowany" not in ident:
                    entry["number"] = ident
                if raw_name != core:
                    entry["full_text"] = raw_name
                entries.append(entry)
    return entries


def fetch_warnings() -> dict:
    page = get(WARNINGS_URL)
    tables = parse_tables(page)
    print(WARNINGS_ID, "tables:", len(tables), "rows:", sum(len(t) - 1 for t in tables), file=sys.stderr)
    return {"pages": 1, "tables": tables}


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
    ap.add_argument("--only", help="refresh a single register, e.g. knf_public_warnings")
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="snapshot date (day of fetch)")
    args = ap.parse_args()
    if args.cache and args.cache.is_file():
        raw = json.loads(args.cache.read_text(encoding="utf-8"))
    else:
        raw = fetch_all(args.only)
        if args.cache:
            args.cache.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    args.out.mkdir(parents=True, exist_ok=True)
    for registry, (label, url) in {WARNINGS_ID: (WARNINGS_LABEL, WARNINGS_URL), **SOURCES}.items():
        if registry not in raw:
            continue
        if registry == WARNINGS_ID:
            entries = warning_entries(raw[registry]["tables"])
        else:
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
