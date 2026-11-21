"""Rule 3: profit claims must be directly accompanied by information on material risk."""

from __future__ import annotations

from . import settings
from .base import RuleOutcome, RuleView, failed, not_applicable, passed, rule


def claim_risk_distance(v: RuleView) -> int | None:
    """Smallest character distance between a profit claim and an openly readable warning."""
    best = None
    for claim in v.facts.profit_claims:
        for risk in v.risk_open:
            gap = max(risk.start - claim.end, claim.start - risk.end, 0)
            best = gap if best is None else min(best, gap)
    return best


@rule("3", "Informacja o ryzyku", "art. 44 ust. 2 lit. b rozporządzenia del. 2017/565")
def risk_information(v: RuleView) -> RuleOutcome:
    claims = v.facts.profit_claims
    if not claims:
        if v.risk:
            return passed(
                "Materiał nie zawiera twierdzeń o zyskach, a informacja o ryzyku jest obecna.", 0.75, v.risk_quote()
            )
        return not_applicable("Nie wykryto twierdzeń o potencjalnych zyskach.")
    claim_ev = v.ctx.quote(claims[0], label="Twierdzenie o potencjalnych zyskach")
    if not v.risk:
        extra = " Jest tylko odesłanie do informacji o ryzyku." if v.facts.risk_refs else ""
        return failed(
            f"Materiał zawiera twierdzenia o zyskach, którym nie towarzyszy żadna informacja o istotnym ryzyku.{extra}",
            0.9,
            [claim_ev],
        )
    if not v.risk_open:
        return failed(
            "Informacja o ryzyku istnieje, ale jest ukryta lub zwinięta; twierdzeniom o zyskach "
            "nie towarzyszy bezpośrednio.",
            0.85,
            [claim_ev, *v.risk_quote()],
        )
    distance = claim_risk_distance(v)
    soft_only = all(h.kind == "soft" for h in v.risk_open)
    if distance is not None and distance <= settings.RISK_PROXIMITY_CHARS:
        conf = 0.6 if soft_only else 0.85
        return passed(
            "Twierdzeniom o zyskach bezpośrednio towarzyszy informacja o ryzyku.", conf, [claim_ev, *v.risk_quote()]
        )
    return failed(
        "Informacja o ryzyku jest oddalona od twierdzeń o zyskach "
        f"(ok. {distance} znaków), więc nie towarzyszy im bezpośrednio.",
        0.7,
        [claim_ev, *v.risk_quote()],
    )
