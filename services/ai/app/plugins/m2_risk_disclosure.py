"""Module 2: the 19-row validator of the UKNF risk-information criteria."""

from __future__ import annotations

from ..context import AnalysisContext
from ..rules import run_rules
from .base import Plugin, PluginFinding, PluginResult

RULE_SEVERITY = {
    "1": "medium",
    "2": "high",
    "3": "high",
    "4": "medium",
    "5": "medium",
    "6": "high",
    "7": "high",
    "8": "low",
    "9": "low",
    "10": "medium",
    "11": "medium",
    "12a": "medium",
    "12b": "medium",
    "13": "medium",
    "14": "medium",
    "15": "medium",
    "16": "low",
    "17": "high",
    "18": "high",
}
IMBALANCE_RATIO = 6.0  # profit text this many times longer than risk text


class RiskDisclosurePlugin(Plugin):
    id = "m2_risk_disclosure"
    module = 2
    description = (
        "Moduł 2: walidator 18 kryteriów informacji o ryzyku (19 wierszy, reguła 12 jako 12a/12b) "
        "wg rozporządzenia delegowanego 2017/565 i MiFID II."
    )

    def run(self, ctx: AnalysisContext) -> PluginResult:
        rules = run_rules(ctx)
        findings: list[PluginFinding] = []
        for r in rules:
            if r.status == "fail":
                findings.append(
                    PluginFinding(
                        f"RULE_{r.id}",
                        RULE_SEVERITY[r.id],
                        f"Reguła {r.id} ({r.name}): {r.explanation}",
                        list(r.evidence_ids),
                        r.confidence,
                        {"rule": r.id},
                    )
                )

        facts = ctx.facts
        # UKNF criterion 15: the tool "flaguje w raporcie wykrycie prognozy przyszłych wyników". The rule
        # itself may pass (warning present); the detection is reported either way, with the exact quote.
        if facts.forecasts:
            hit = facts.forecasts[0]
            rule15 = next((r for r in rules if r.id == "15"), None)
            state = {"pass": "zawiera wymagane ostrzeżenie", "fail": "nie zawiera wymaganego ostrzeżenia"}.get(
                rule15.status if rule15 else "", "wymaga oceny"
            )
            findings.append(
                PluginFinding(
                    "FORECAST_DETECTED",
                    "info",
                    f"Wykryto prognozę przyszłych wyników („{ctx.page.text[hit.sentence.start : hit.sentence.end].strip()}”); "
                    f"materiał {state}.",
                    list(rule15.evidence_ids)
                    if rule15 and rule15.evidence_ids
                    else [ctx.quote(hit, label="Prognoza przyszłych wyników")],
                    1.0,
                    {"rule": "15", "count": len(facts.forecasts)},
                )
            )

        profit_chars = sum(s.end - s.start for s in {id(h.sentence): h.sentence for h in facts.profit_claims}.values())
        risk_chars = sum(h.end - h.start for h in facts.risk)
        ratio = profit_chars / risk_chars if risk_chars else None
        if ratio is not None and ratio >= IMBALANCE_RATIO:
            findings.append(
                PluginFinding(
                    "PROFIT_RISK_IMBALANCE",
                    "low",
                    f"Treści o zyskach zajmują ok. {ratio:.0f} razy więcej miejsca niż informacja o ryzyku "
                    f"({profit_chars} wobec {risk_chars} znaków).",
                    [ctx.quote(facts.profit_claims[0], label="Twierdzenie o zyskach")],
                    0.7,
                    {"ratio": ratio},
                )
            )

        counts = {s: sum(r.status == s for r in rules) for s in ("pass", "fail", "na", "unknown")}
        proportion = f"; proporcja tekstu o zyskach do tekstu o ryzyku: {ratio:.1f}" if ratio is not None else ""
        findings.append(
            PluginFinding(
                "RULES_SUMMARY",
                "info",
                f"Walidator kryteriów informacji o ryzyku: {counts['pass']} spełnionych, {counts['fail']} naruszonych, "
                f"{counts['na']} nie dotyczy, {counts['unknown']} do oceny wizualnej{proportion}.",
                [],
                1.0,
                {"counts": counts, "profit_risk_ratio": ratio},
            )
        )
        return self.result(findings=findings, rules=rules)
