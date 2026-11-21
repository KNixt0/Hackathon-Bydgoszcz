"""Evidence package: Jinja2 HTML (autoescaped) rendered to A4 PDF by headless Chromium."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import __version__
from app.config import get_settings
from app.scraper.browser import html_to_pdf

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(default=True, default_for_string=True),
    trim_blocks=True,
    lstrip_blocks=True,
)

MODULES = {
    1: "Moduł 1 · Finfluencerzy",
    2: "Moduł 2 · Zgodność informacji o ryzyku",
    3: "Moduł 3 · Doradztwo w szarej strefie",
}
LEVELS = {"red": "WYSOKIE RYZYKO", "orange": "PODWYŻSZONE RYZYKO", "green": "NISKIE RYZYKO"}
STATUSES = {
    "new": "Nowy",
    "in_review": "W analizie",
    "escalated": "Eskalowany",
    "closed_violation": "Zamknięty – naruszenie",
    "closed_ok": "Zamknięty – brak naruszenia",
}
RULE_STATUS = {"pass": "spełniona", "fail": "naruszona", "na": "nie dotyczy", "unknown": "do weryfikacji"}
REGISTRY_STATUS = {
    "listed": "figuruje",
    "not_listed": "nie figuruje",
    "warning_listed": "lista ostrzeżeń",
    "inactive": "nieaktywny",
    "not_checked": "nie sprawdzono",
}
EVIDENCE_KIND = {
    "quote": "Cytat",
    "legal": "Podstawa prawna",
    "registry": "Rejestr",
    "archive": "Archiwum",
    "account": "Konto",
    "url": "URL",
    "krs": "KRS",
}
VERDICTS = {"upheld": "utrzymany", "weakened": "osłabiony", "rejected": "odrzucony"}


def _level(score: float, threshold: float) -> str:
    return "red" if score >= threshold else "orange" if score >= threshold / 2 else "green"


def render_html(incident: dict) -> str:
    """The evidence package as a self-contained HTML document (no external resources)."""
    settings = get_settings()
    debate = incident.get("debate") or {}
    claims = {c.get("id"): c for c in debate.get("claims") or [] if isinstance(c, dict)}
    score = float(incident.get("risk_score") or 0)
    level = incident.get("risk_level") or _level(score, settings.alert_threshold)
    return _env.get_template("evidence.html").render(
        i=incident,
        source=incident.get("source") or {},
        entities=incident.get("entities") or {},
        recommendation=incident.get("recommendation") or {},
        engine=incident.get("engine") or {},
        rules=incident.get("rules") or [],
        evidence=incident.get("evidence") or [],
        registry_checks=incident.get("registry_checks") or [],
        args_for=[claims[c] for c in debate.get("arguments_for") or [] if c in claims],
        args_against=[claims[c] for c in debate.get("arguments_against") or [] if c in claims],
        arbiter=debate.get("arbiter_rationale") or "",
        level=level,
        level_label=LEVELS.get(level, level),
        module_label=MODULES.get(incident.get("primary_module"), str(incident.get("primary_module"))),
        status_label=STATUSES.get(incident.get("status"), incident.get("status")),
        rule_status=RULE_STATUS,
        registry_status=REGISTRY_STATUS,
        evidence_kind=EVIDENCE_KIND,
        verdicts=VERDICTS,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        backend_version=__version__,
    )


def render_pdf(incident: dict) -> bytes:
    return html_to_pdf(render_html(incident))
