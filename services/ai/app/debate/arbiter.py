"""Round 3: Arbiter + Aggregator.

Turns the critiqued claims into plugin scores, one risk score, a recommendation and the
rationale. All wording is assembled from the claims; nothing is invented here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..schemas import Recommendation
from ..scoring import (
    ScoreBreakdown,
    aggregate,
    finding_weight,
    llm_adjustment,
    plugin_score,
    recommendation_action,
    risk_level,
    rule_residual,
)
from ..scoring import weights as W
from .models import AgentReport, DebateClaim

# The system detects and reports. Its output never qualifies conduct legally and never proposes a
# formal step (summons, criminal notice, warning-list entry): that belongs to the competent UKNF unit.
RECOMMENDATIONS = {
    "none": ("Brak działań", "Materiał nie wymaga oceny analityka; wynik pozostaje w archiwum."),
    "monitor": (
        "Monitorowanie",
        "Obserwować źródło i powtórzyć analizę przy zmianie treści lub kolejnej publikacji.",
    ),
    "explain": (
        "Wymaga oceny analityka",
        "Analityk ocenia ustalenia i materiał dowodowy w zakresie: {topics}.",
    ),
    "escalate": (
        "Wysoki priorytet",
        "Przekazać raport z wykrycia do oceny merytorycznej właściwej komórki UKNF. Zakres ustaleń: {topics}.",
    ),
}
LEVEL_PL = {"green": "niskie", "orange": "podwyższone", "red": "wysokie"}


@dataclass
class Verdict:
    plugin_scores: dict[str, float]
    breakdown: ScoreBreakdown
    level: str
    recommendation: Recommendation
    rationale: str
    arguments_for: list[str]
    arguments_against: list[str]
    summary: str


class Arbiter:
    name = "Arbiter i agregator"
    role = "Ważenie argumentów, wynik ryzyka 0–100, rekomendacja"

    def decide(
        self, reports: list[AgentReport], against: list[DebateClaim], llm_claims: list[DebateClaim] | None = None
    ) -> Verdict:
        """llm_claims: grounded claims proposed by the optional model; they add a capped few points."""
        for_claims = [c for r in reports for c in r.claims]
        plugin_scores: dict[str, float] = {}
        for report in reports:
            for result in report.results:
                signals = [
                    (c.code, c.confidence) for c in for_claims if c.plugin == result.plugin and c.verdict != "rejected"
                ]
                residual = rule_residual(result.rules) if result.rules else 0.0
                plugin_scores[result.plugin] = round(plugin_score(signals, residual), 1)
        kept_against = [c for c in against if c.verdict != "rejected"]
        breakdown = aggregate(plugin_scores, [(c.code, c.confidence) for c in kept_against])
        llm_for = [c for c in llm_claims or [] if c.verdict != "rejected"]
        llm_points = llm_adjustment([c.confidence for c in llm_for])
        if llm_points:
            breakdown = replace(
                breakdown, llm_points=llm_points, risk_score=round(min(100.0, breakdown.risk_score + llm_points), 1)
            )
        score = breakdown.risk_score
        level = risk_level(score)
        action = recommendation_action(score)
        kept_for = sorted(
            (c for c in [*for_claims, *llm_for] if c.verdict != "rejected"),
            key=lambda c: -finding_weight(c.code) * c.confidence,
        )
        # A grave, fully upheld finding is never closed without at least monitoring.
        if action == "none" and any(c.verdict == "upheld" and finding_weight(c.code) >= 0.6 for c in kept_for):
            action = "monitor"
        topics = "; ".join(_topic(c) for c in kept_for[:3]) or "całość materiału"
        label, next_step = RECOMMENDATIONS[action]
        recommendation = Recommendation(action=action, label=label, next_step=next_step.format(topics=topics))

        rejected = sum(c.verdict == "rejected" for c in for_claims)
        llm_note = (
            f" Model językowy dodał {len(llm_for)} ugruntowanych tez (wpływ na wynik: +{llm_points:.1f} pkt, "
            f"limit {W.LLM_MAX_POINTS:.0f} pkt)."
            if llm_points
            else ""
        )
        weakened = sum(c.verdict == "weakened" for c in for_claims)
        parts = [f"Ryzyko {LEVEL_PL[level]}: {score:.0f}/100 (zgodność {100 - score:.0f}/100)."]
        if kept_for:
            parts.append(
                f"Za naruszeniem przemawia {len(kept_for)} tez, z czego {weakened} osłabionych przez "
                f"krytyka; {rejected} odrzucono."
            )
            parts.append(
                "Najmocniejsze argumenty: " + " ".join(f"({i}) {c.text}" for i, c in enumerate(kept_for[:3], 1))
            )
            if llm_note:
                parts.append(llm_note.strip())
        else:
            parts.append("Żadna teza o naruszeniu nie utrzymała się po weryfikacji.")
        if kept_against:
            strongest = sorted(kept_against, key=lambda c: -W.MITIGATION_WEIGHTS.get(c.code, 0) * c.confidence)[:3]
            parts.append(
                "Okoliczności łagodzące: "
                + " ".join(f"({i}) {c.text}" for i, c in enumerate(strongest, 1))
                + f" Łącznie obniżają one wynik o {breakdown.mitigation:.0%}."
            )
        parts.append(f"Rekomendacja: {label.lower()}.")
        return Verdict(
            plugin_scores=plugin_scores,
            breakdown=breakdown,
            level=level,
            recommendation=recommendation,
            rationale=" ".join(parts),
            arguments_for=[c.id for c in kept_for],
            arguments_against=[c.id for c in kept_against],
            summary=(
                f"Wynik ryzyka {score:.1f}/100 (surowy {100 * breakdown.raw:.1f}, redukcja "
                f"{breakdown.mitigation:.0%} za okoliczności łagodzące"
                + (f", +{llm_points:.1f} pkt za tezy modelu" if llm_points else "")
                + f"). Rekomendacja: {label.lower()}."
            ),
        )


TOPICS = {
    "PROMOTED_FIRM_NOT_LISTED": "status prawny promowanego podmiotu (brak wpisu w rejestrach KNF)",
    "REGISTRY_NOT_LISTED": "podstawa prawna świadczenia usług (brak wpisu w rejestrach KNF)",
    "UNREGISTERED_SERVICE_PROVIDER": "zakres oferowanych usług inwestycyjnych",
    "WARNING_LISTED": "wpis na liście ostrzeżeń publicznych KNF",
    "COOPERATION_NOT_NOTIFIED": "brak zgłoszenia współpracy reklamowej do UKNF",
    "UNMARKED_THIRD_PARTY_AD": "brak oznaczenia reklamy przez twórcę",
    "DISGUISED_AD": "przedstawianie reklamy jako niezależnej opinii",
    "LEGAL_ADVISER_INACTIVE": "powołanie się na radcę prawnego niewykonującego zawodu",
    "LEGAL_ADVISER_NOT_FOUND": "powołanie się na radcę prawnego spoza rejestru KIRP",
    "ADVISORY_PHRASE": "rekomendacje inwestycyjne w rozumieniu art. 76 ustawy o obrocie",
    "PORTFOLIO_MANAGEMENT": "zarządzanie portfelami klientów",
    "GUARANTEED_RETURN": "obietnice gwarantowanego zysku",
    "FAKE_LICENCE": "deklarowana licencja doradcy inwestycyjnego",
    "BRAND_IMPERSONATION": "używanie marki zarejestrowanej firmy inwestycyjnej",
    "ENTITY_UNIDENTIFIED": "tożsamość podmiotu świadczącego usługę",
    "PR_CONFLICT_PATH": "powiązania osobowe między firmą, agencją PR i twórcą",
    "PERSONAL_TIE_PATH": "powiązania osobowe między firmą a twórcą",
    "FOREIGN_SHELL": "siedziba podmiotu poza EOG",
    "COMPANY_YOUNG": "krótki okres działalności spółki",
    "LOW_SHARE_CAPITAL": "kapitał zakładowy spółki",
    "NO_FINANCIAL_STATEMENTS": "brak sprawozdań finansowych",
    "OPINION_SPIKE": "skok liczby opinii",
    "FRESH_ACCOUNT_CLUSTER": "opinie z nowo założonych kont",
    "NAME_PATTERN_CLUSTER": "opinie z kont o seryjnych nazwach",
    "FOREIGN_ORIGIN_CLUSTER": "pochodzenie kont komentujących",
    "PROFIT_RISK_IMBALANCE": "proporcja treści o zyskach do informacji o ryzyku",
}


def _topic(claim: DebateClaim) -> str:
    """Short name of the issue for the recommendation's next step."""
    if claim.code.startswith("RULE_"):
        return claim.text.split(": ", 1)[0].replace("Reguła", "kryterium", 1)
    if claim.code in TOPICS:
        return TOPICS[claim.code]
    text = claim.text.rstrip(".")
    return text if len(text) <= 120 else text[:120].rsplit(" ", 1)[0] + "…"
