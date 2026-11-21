"""Rule plumbing: spec, outcome, registry and the shared view of the risk information."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property

from ..context import ATTACHMENT_RULES, AnalysisContext, Hit
from ..preprocess import Segment


@dataclass(frozen=True)
class RuleSpec:
    id: str
    name: str  # verbatim from the UKNF criteria attachment
    legal_basis: str


@dataclass
class RuleOutcome:
    status: str  # pass | fail | na | unknown
    confidence: float
    explanation: str
    evidence_ids: list[str] = field(default_factory=list)
    method: str | None = None  # rendered | static | text | llm (None = decided by run_rules)
    score: float | None = None  # 0-1 violation strength (None = derived from status/confidence)


def rendered(outcome: RuleOutcome, score: float | None = None) -> RuleOutcome:
    """Mark an outcome as decided from browser measurements (contract v3, invariant 5)."""
    outcome.method = "rendered"
    if score is not None:
        outcome.score = max(0.0, min(1.0, score))
    return outcome


def passed(explanation: str, confidence: float = 0.8, evidence: list[str] | None = None) -> RuleOutcome:
    return RuleOutcome("pass", confidence, explanation, evidence or [])


def failed(explanation: str, confidence: float = 0.8, evidence: list[str] | None = None) -> RuleOutcome:
    return RuleOutcome("fail", confidence, explanation, evidence or [])


def not_applicable(explanation: str) -> RuleOutcome:
    return RuleOutcome("na", 0.9, explanation, [])


def unknown(explanation: str) -> RuleOutcome:
    return RuleOutcome("unknown", 0.0, explanation, [])


class RuleView:
    """What the rules know about the document; computed once per analysis."""

    def __init__(self, ctx: AnalysisContext) -> None:
        self.ctx = ctx
        self.page = ctx.page
        self.facts = ctx.facts
        self.signals = ctx.page.signals
        self.has_html = ctx.page.signals.has_html

    def segs(self, hit: Hit) -> list[Segment]:
        return self.page.segments_in(hit.start, hit.end)

    def _all(self, hit: Hit, attr: str) -> bool:
        segs = self.segs(hit)
        return bool(segs) and all(getattr(s.style, attr) for s in segs)

    def is_concealed(self, hit: Hit) -> bool:
        """Needs an action to be seen: collapsed block or not rendered at all."""
        segs = self.segs(hit)
        return bool(segs) and all(s.style.hidden or s.style.collapsed for s in segs)

    def is_low_visibility(self, hit: Hit) -> bool:
        return self._all(hit, "low_visibility")

    @cached_property
    def risk(self) -> list[Hit]:
        return self.facts.risk

    @cached_property
    def risk_open(self) -> list[Hit]:
        """Risk sentences readable without any click."""
        return [h for h in self.risk if not self.is_concealed(h)]

    @cached_property
    def risk_prominent(self) -> list[Hit]:
        return [h for h in self.risk_open if not self.is_low_visibility(h)]

    @cached_property
    def main_risk(self) -> Hit | None:
        """The risk passage a reader is most likely to see (longest of the best-placed ones)."""
        pool = self.risk_prominent or self.risk_open or self.risk
        return max(pool, key=lambda h: h.end - h.start) if pool else None

    @cached_property
    def visual(self):  # type: ignore[no-untyped-def]
        """`document.visual` measurements (None when the page was not rendered)."""
        return self.ctx.document.visual

    @cached_property
    def rendered_risk(self) -> list:
        """Measured elements that hold risk information as the text analysis understands it."""
        from .rendered import match_risk

        return match_risk(self) if self.visual else []

    @cached_property
    def rendered_history(self) -> list:
        from .rendered import match_history

        return match_history(self) if self.visual else []

    @staticmethod
    def chars(hits: list[Hit]) -> int:
        return sum(h.end - h.start for h in hits)

    def risk_quote(self, hit: Hit | None = None, label: str = "Informacja o ryzyku") -> list[str]:
        hit = hit or self.main_risk
        return [self.ctx.evidence.quote(hit.start, hit.end, label)] if hit else []

    def legal(self, spec: RuleSpec) -> str:
        return self.ctx.evidence.legal(spec.legal_basis, f"Reguła {spec.id}: {spec.name}", ATTACHMENT_RULES)


RuleCheck = Callable[[RuleView], RuleOutcome]
REGISTRY: list[tuple[RuleSpec, RuleCheck]] = []


def rule(rule_id: str, name: str, legal_basis: str) -> Callable[[RuleCheck], RuleCheck]:
    """Register one criterion. Registration order = attachment order."""

    def decorator(fn: RuleCheck) -> RuleCheck:
        REGISTRY.append((RuleSpec(rule_id, name, legal_basis), fn))
        return fn

    return decorator
