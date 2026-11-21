"""The 19 UKNF risk-information criteria (ids 1-18, 12 split into 12a / 12b).

Each criterion is one small function registered with `@rule(id, name, legal_basis)`.
`run_rules` always returns all 19 rows, in attachment order.
"""

from __future__ import annotations

from ..context import AnalysisContext
from ..schemas import RuleResult
from . import (  # noqa: F401  (import order = attachment order)
    r01_02_identification,
    r03_risk_presence,
    r04_08_visual,
    r09_10_language,
    r11_15_performance,
    r16_18_tax_supervisor,
)
from .base import REGISTRY, RuleOutcome, RuleSpec, RuleView

RULE_ORDER = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12a", "12b", "13", "14", "15", "16", "17", "18"]
REGISTRY.sort(key=lambda item: RULE_ORDER.index(item[0].id))
SPECS: dict[str, RuleSpec] = {spec.id: spec for spec, _ in REGISTRY}
assert list(SPECS) == RULE_ORDER, "rule registry must cover exactly the 19 criteria"

__all__ = ["REGISTRY", "RULE_ORDER", "SPECS", "VISUAL_RULES", "RuleOutcome", "RuleSpec", "RuleView", "run_rules"]


# Criteria about how the warning is displayed: decided from browser measurements when the scraper
# rendered the page (method "rendered"), else from the HTML source ("static").
VISUAL_RULES = {"4", "5", "6", "7", "8", "13"}


def _method(spec: RuleSpec, outcome: RuleOutcome, view: RuleView) -> str:
    if outcome.method:
        return outcome.method
    if spec.id in VISUAL_RULES and view.has_html and outcome.status != "na":
        return "static"
    return "text"


def _score(outcome: RuleOutcome) -> float:
    """Violation strength 0-1: a failed rule by its confidence, a passed one by its residual doubt."""
    if outcome.score is not None:
        return outcome.score
    if outcome.status == "fail":
        return outcome.confidence
    if outcome.status == "pass":
        return (1.0 - outcome.confidence) * 0.3
    return 0.1 if outcome.status == "unknown" else 0.0


def _out_of_scope_rows(ctx: AnalysisContext) -> list[RuleResult]:
    """Outside UKNF's remit the risk-information criteria do not apply: all 19 rows are "na"."""
    why = f"Nie dotyczy: materiał poza właściwością UKNF w zakresie modułów InvestWatch ({ctx.scope.reason})"
    return [
        RuleResult(
            id=spec.id,
            name=spec.name,
            legal_basis=spec.legal_basis,
            status="na",
            confidence=1.0,
            explanation=why,
            evidence_ids=[],
            method="text",
            score=0.0,
        )
        for spec, _ in REGISTRY
    ]


def run_rules(ctx: AnalysisContext) -> list[RuleResult]:
    if not ctx.scope.in_scope:
        return _out_of_scope_rows(ctx)
    view = RuleView(ctx)
    results = []
    for spec, check in REGISTRY:
        outcome = check(view)
        evidence = list(dict.fromkeys(outcome.evidence_ids))
        if outcome.status in {"fail", "unknown"}:
            evidence.append(view.legal(spec))
        results.append(
            RuleResult(
                id=spec.id,
                name=spec.name,
                legal_basis=spec.legal_basis,
                status=outcome.status,
                confidence=round(outcome.confidence, 2),
                explanation=outcome.explanation,
                evidence_ids=evidence,
                method=_method(spec, outcome, view),
                score=round(max(0.0, min(1.0, _score(outcome))), 2),
            )
        )
    return results
