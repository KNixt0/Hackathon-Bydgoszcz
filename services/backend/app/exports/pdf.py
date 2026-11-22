"""Detection report ("Raport z wykrycia"): Jinja2 HTML (autoescaped) rendered to A4 PDF by headless Chromium.

The report documents what was detected and how; it is not a legal qualification and proposes no
formal step (contract v4, decision #22)."""

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
    "awaiting_correction": "Po interwencji – oczekuje na weryfikację",
    "resolved": "Zamknięta – potwierdzona przez analityka",
    "false_positive": "Zamknięta – fałszywy alarm",
}
HISTORY_ACTIONS = {"assign": "Przypisanie", "transition": "Zmiana etapu", "label": "Ocena trafności"}
HISTORY_FIELDS = {
    "status": "Etap",
    "assigned_to": "Prowadzi",
    "escalation_path": "Ścieżka eskalacji",
    "resolution_action": "Działanie końcowe",
    "resolution_note": "Notatka",
    "intervention_note": "Interwencja",
    "follow_up_due": "Termin weryfikacji",
    "label": "Ocena",
}
HISTORY_VALUES = {
    **STATUSES,
    "RISK_INFORMATION": "Ryzyko informacyjne",
    "UNLICENSED_ACTIVITY": "Działalność bez zezwolenia",
    "THIRD_PARTY_ADVERTISING": "Reklama podmiotu trzeciego",
    # values written before contract v4, shown in old histories
    "SUPERVISION_RISK_DEPT": "Ryzyko informacyjne",
    "LEGAL_WARNING_LIST": "Działalność bez zezwolenia",
    "THIRD_PARTY_AUDIT": "Reklama podmiotu trzeciego",
    "evidence_report": "Raport z wykrycia",
    "content_removed": "Treść usunięta",
    "content_corrected": "Treść poprawiona",
    "warning_list_request": "Raport z wykrycia",
    "enhanced_monitoring": "Monitorowanie",
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
CONTENT_STATES = {
    "online": "dostępna, bez zmian",
    "changed": "zmieniona od wykrycia",
    "removed": "usunięta (HTTP 404/410)",
    "unreachable": "niedostępna",
}
FOLLOW_UP_OUTCOMES = {
    "removed": "treść usunięta",
    "corrected": "treść poprawiona",
    "persisting": "naruszenie trwa",
}


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
        observation=incident.get("observation") or {},
        follow_up=incident.get("follow_up"),
        scope=incident.get("scope") or {},
        content_states=CONTENT_STATES,
        follow_up_outcomes=FOLLOW_UP_OUTCOMES,
        **_history_context(history),
    )


def render_pdf(incident: dict, history: list[dict] | None = None, reports: list[dict] | None = None) -> bytes:
    return html_to_pdf(render_html(incident, history, reports))
