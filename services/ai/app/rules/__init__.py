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

__all__ = ["REGISTRY", "RULE_ORDER", "SPECS", "RuleOutcome", "RuleSpec", "RuleView", "run_rules"]


def run_rules(ctx: AnalysisContext) -> list[RuleResult]:
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
            )
        )
    return results
