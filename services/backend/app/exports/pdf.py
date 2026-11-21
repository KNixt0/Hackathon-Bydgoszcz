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
    "new": "Nowa",
    "in_review": "W weryfikacji",
    "escalation_requested": "Wniosek o eskalację",
    "escalated": "Eskalowana",
    "resolved": "Zamknięta – naruszenie potwierdzone",
    "false_positive": "Zamknięta – fałszywy alarm",
}
HISTORY_ACTIONS = {"assign": "Przypisanie", "transition": "Zmiana etapu", "label": "Ocena trafności"}
HISTORY_FIELDS = {
    "status": "Etap",
    "assigned_to": "Prowadzi",
    "escalation_path": "Ścieżka eskalacji",
    "resolution_action": "Działanie końcowe",
    "resolution_note": "Notatka",
    "label": "Ocena",
}
HISTORY_VALUES = {
    **STATUSES,
    "SUPERVISION_RISK_DEPT": "Departament nadzoru (ryzyko)",
    "LEGAL_WARNING_LIST": "Departament Prawny – lista ostrzeżeń",
    "THIRD_PARTY_AUDIT": "Audyt podmiotu trzeciego",
    "evidence_report": "Raport dowodowy",
    "warning_list_request": "Wniosek o wpis na listę ostrzeżeń",
    "enhanced_monitoring": "Wzmożony monitoring",
    "false_positive": "Fałszywy alarm",
    "true_positive": "Trafny alarm",
    "unlabeled": "Bez oceny",
}
ROLES = {"ANALYST": "analityk", "SUPERVISOR": "kierownik"}
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
REPORT_CATEGORIES = {1: "reklama influencera", 2: "materiał firmy", 3: "doradztwo bez zezwolenia"}
VERDICTS = {"upheld": "utrzymany", "weakened": "osłabiony", "rejected": "odrzucony"}


def _level(score: float, threshold: float) -> str:
    return "red" if score >= threshold else "orange" if score >= threshold / 2 else "green"


def _history_context(history: list[dict] | None) -> dict:
    return {
        "history": history or [],
        "actions": HISTORY_ACTIONS,
        "fields": HISTORY_FIELDS,
        "values": HISTORY_VALUES,
        "roles": ROLES,
    }


def render_html(incident: dict, history: list[dict] | None = None, reports: list[dict] | None = None) -> str:
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
        reports=reports or [],
        report_categories=REPORT_CATEGORIES,
        **_history_context(history),
    )


def render_pdf(incident: dict, history: list[dict] | None = None, reports: list[dict] | None = None) -> bytes:
    return html_to_pdf(render_html(incident, history, reports))


def render_warning_list_html(incident: dict, history: list[dict] | None = None) -> str:
    """Draft request to add the entity to the KNF public warnings list (Module 3)."""
    workflow = incident.get("workflow") or {}
    phrases = [e for e in incident.get("evidence") or [] if isinstance(e, dict) and e.get("quote")]
    return _env.get_template("warning_list_request.html").render(
        i=incident,
        source=incident.get("source") or {},
        entities=incident.get("entities") or {},
        registry_checks=incident.get("registry_checks") or [],
        phrases=phrases,
        requested_by=workflow.get("assigned_to") or "analityk prowadzący sprawę",
        module_label=MODULES.get(incident.get("primary_module"), str(incident.get("primary_module"))),
        status_label=STATUSES.get(incident.get("status"), incident.get("status")),
        registry_status=REGISTRY_STATUS,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        backend_version=__version__,
        **_history_context(history),
    )


def render_warning_list_pdf(incident: dict, history: list[dict] | None = None) -> bytes:
    return html_to_pdf(render_warning_list_html(incident, history))
