"""CSV exports: UTF-8 with BOM (Excel shows Polish characters), formula injection neutralised."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from typing import Any

from app.config import get_settings

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
BOM = "﻿"


def safe_cell(value: Any) -> Any:
    """Text starting with = + - @ (or tab/CR) would run as a formula in Excel: prefix an apostrophe."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "tak" if value else "nie"
    if isinstance(value, int | float):
        return value
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def render_csv(header: list[str], rows: Iterable[Iterable[Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=get_settings().csv_delimiter[:1] or ";", lineterminator="\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([safe_cell(cell) for cell in row])
    return (BOM + buffer.getvalue()).encode("utf-8")


LIST_HEADER = [
    "id",
    "tytul",
    "risk_score",
    "compliance_score",
    "poziom_ryzyka",
    "modul_glowny",
    "moduly",
    "status",
    "platforma",
    "url",
    "reklamodawca",
    "firma_inwestycyjna",
    "naruszone_reguly",
    "etykieta",
    "dane_syntetyczne",
    "wykryto",
    "zaktualizowano",
    "podsumowanie",
]


def incidents_csv(summaries: Iterable[dict]) -> bytes:
    def rows() -> Iterable[list[Any]]:
        for s in summaries:
            yield [
                s["id"],
                s["title"],
                s["risk_score"],
                s["compliance_score"],
                s["risk_level"],
                s["primary_module"],
                ",".join(str(m) for m in s["modules"]),
                s["status"],
                s["source"]["platform"],
                s["source"]["url"],
                s["advertiser"],
                s["firm"],
                ",".join(s["failed_rules"]),
                s["ground_truth"],
                s["synthetic"],
                s["created_at"],
                s["updated_at"],
                s["summary"],
            ]

    return render_csv(LIST_HEADER, rows())


DETAIL_HEADER = [
    "sekcja",
    "id",
    "nazwa",
    "status",
    "pewnosc",
    "podstawa_prawna",
    "opis",
    "cytat",
    "powiazane_dowody",
    "url",
]


CATEGORY_NAMES = {1: "moduł 1", 2: "moduł 2", 3: "moduł 3"}


def incident_csv(incident: dict, reports: list[dict] | None = None) -> bytes:
    """One incident: a header row, then the 19 rules and the evidence list."""
    source = incident.get("source") or {}
    rows: list[list[Any]] = [
        [
            "incydent",
            incident["id"],
            incident.get("title"),
            incident.get("status"),
            incident.get("risk_score"),
            "",
            incident.get("summary"),
            "",
            source.get("content_hash"),
            source.get("url"),
        ]
    ]
    for rule in incident.get("rules") or []:
        rows.append(
            [
                "regula",
                rule.get("id"),
                rule.get("name"),
                rule.get("status"),
                rule.get("confidence"),
                rule.get("legal_basis"),
                rule.get("explanation"),
                "",
                ",".join(rule.get("evidence_ids") or []),
                "",
            ]
        )
    for item in incident.get("evidence") or []:
        rows.append(
            [
                "dowod",
                item.get("id"),
                item.get("label"),
                item.get("kind"),
                "",
                item.get("legal_ref"),
                item.get("attachment"),
                item.get("quote"),
                item.get("storage_key"),
                item.get("url"),
            ]
        )
    for report in reports or []:  # citizens' free text: safe_cell neutralises formulas
        rows.append(
            [
                "zgloszenie",
                "",
                CATEGORY_NAMES.get(report.get("category_hint"), "nie wiem"),
                "",
                "",
                "",
                report.get("comment"),
                "",
                "",
                report.get("created_at"),
            ]
        )
    return render_csv(DETAIL_HEADER, rows)
