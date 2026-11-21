"""Module 1: advertisements of investment firms published by third parties (finfluencers)."""

from __future__ import annotations

from ..context import AnalysisContext
from ._affiliate import affiliate_links
from ._registers import check_professionals, lookup_firm, make_check, registry_evidence
from .base import Plugin, PluginFinding, PluginResult

REGISTER_NAMES = {
    "knf_banks_brokerage": "banki prowadzące działalność maklerską",
    "knf_brokerage_houses": "domy maklerskie",
    "knf_foreign_branches": "oddziały zagranicznych firm inwestycyjnych",
    "knf_foreign_cross_border": "zagraniczne firmy inwestycyjne bez oddziału",
    "knf_investment_firms": "rejestr firm inwestycyjnych",
}


class FinfluencerPlugin(Plugin):
    id = "m1_finfluencer"
    module = 1
    description = (
        "Moduł 1: reklamy firm inwestycyjnych publikowane przez podmioty trzecie (finfluencerów): "
        "status firmy w rejestrach KNF, zgłoszenie współpracy do UKNF, oznaczenie reklamy."
    )

    def applies(self, ctx: AnalysisContext) -> bool:
        ent = ctx.entities
        return bool(ent.firm and ent.advertiser and ent.third_party)

    def run(self, ctx: AnalysisContext) -> PluginResult:
        ent, facts = ctx.entities, ctx.facts
        firm, publisher = ent.firm.name, ent.advertiser.name
        findings: list[PluginFinding] = []
        lookup = lookup_firm(ctx, firm)
        checks = list(lookup.checks)
        mention_ev = []
        if ent.firm_mentions:
            a, _ = ent.firm_mentions[0]
            mention_ev = [ctx.quote_sentence(a, "Promowana firma w treści materiału")]

        if lookup.warning:
            findings.append(
                PluginFinding(
                    "WARNING_LISTED",
                    "high",
                    f"„{publisher}” promuje podmiot „{firm}”, który figuruje na liście ostrzeżeń publicznych KNF.",
                    lookup.evidence_ids + mention_ev,
                    0.95,
                )
            )
        if lookup.listed:
            where = ", ".join(REGISTER_NAMES[r] for r in lookup.listed_in if r != "knf_investment_firms")
            findings.append(
                PluginFinding(
                    "FIRM_REGISTERED",
                    "info",
                    f"Promowana firma „{firm}” figuruje w rejestrach KNF ({where or 'rejestr firm inwestycyjnych'}).",
                    lookup.evidence_ids,
                    0.95,
                    {"entry": lookup.listed.entry["name"]},
                )
            )
        else:
            similar = (
                f" Nazwa jest podobna do zarejestrowanego podmiotu „{lookup.similar.entry['name']}”."
                if lookup.similar
                else ""
            )
            findings.append(
                PluginFinding(
                    "PROMOTED_FIRM_NOT_LISTED",
                    "high",
                    f"„{publisher}” promuje podmiot „{firm}”, którego nie ma w żadnym z pięciu rejestrów firm "
                    f"inwestycyjnych KNF.{similar}",
                    lookup.evidence_ids + mention_ev,
                    0.85,
                    {"similar": lookup.similar.entry["name"] if lookup.similar else None},
                )
            )

        notified = ctx.context.cooperation_notified
        subject = f"{firm} ↔ {publisher}"
        reg = "uknf_cooperation_notice"
        if notified is True:
            checks.append(make_check(ctx, reg, subject, "listed", "Współpraca zgłoszona do UKNF (dane z kontekstu)"))
            findings.append(
                PluginFinding(
                    "COOPERATION_NOTIFIED",
                    "info",
                    f"Współpraca „{subject}” została zgłoszona do UKNF.",
                    [registry_evidence(ctx, reg, subject, "współpraca zgłoszona")],
                    0.95,
                )
            )
        elif notified is False:
            checks.append(
                make_check(ctx, reg, subject, "not_listed", "Brak zgłoszenia współpracy w UKNF (dane z kontekstu)")
            )
            findings.append(
                PluginFinding(
                    "COOPERATION_NOT_NOTIFIED",
                    "medium",
                    f"UKNF nie ma zgłoszenia współpracy reklamowej „{subject}”, mimo że materiał promuje firmę.",
                    [registry_evidence(ctx, reg, subject, "brak zgłoszenia"), *mention_ev],
                    0.8,
                )
            )
        else:
            checks.append(make_check(ctx, reg, subject, "not_checked", "Brak danych o zgłoszeniu współpracy"))

        open_markers = [h for h in facts.ad_markers if not _concealed(ctx, h.start, h.end)]
        promo = facts.cta or facts.profit_claims
        denial = facts.independence or facts.ad_negations
        if open_markers:
            findings.append(
                PluginFinding(
                    "AD_MARKED",
                    "info",
                    "Materiał podmiotu trzeciego jest oznaczony jako reklama lub współpraca.",
                    [ctx.evidence.quote(open_markers[0].start, open_markers[0].end, "Oznaczenie reklamy")],
                    0.9,
                )
            )
        elif promo and denial:
            # One finding per fact: the unmarked ad that also claims independence.
            findings.append(
                PluginFinding(
                    "DISGUISED_AD",
                    "medium",
                    f"Materiał „{publisher}” zachęca do oferty „{firm}”, nie jest oznaczony jako reklama i przedstawia "
                    "się jako niezależna opinia lub recenzja, co może ukrywać współpracę z firmą.",
                    [
                        ctx.quote(denial[0], label="Deklaracja niezależności"),
                        ctx.quote(promo[0], label="Zachęta do skorzystania z oferty"),
                    ],
                    0.75,
                )
            )
        elif promo:
            findings.append(
                PluginFinding(
                    "UNMARKED_THIRD_PARTY_AD",
                    "medium",
                    f"Materiał „{publisher}” zachęca do oferty „{firm}”, ale nie jest oznaczony jako reklama ani "
                    "współpraca komercyjna.",
                    [ctx.quote(promo[0], label="Zachęta do skorzystania z oferty")],
                    0.8,
                )
            )

        findings += _affiliate_findings(ctx, publisher, bool(open_markers))

        prof_checks, prof_findings = check_professionals(ctx)
        return self.result(findings=findings + prof_findings, registry_checks=checks + prof_checks)


def _affiliate_findings(ctx: AnalysisContext, publisher: str, marked: bool) -> list[PluginFinding]:
    """An affiliate / tracking link to a registered firm in a third party's material is evidence of a
    commercial relationship; together with a missing ad label it is an undisclosed advertisement."""
    links = affiliate_links(ctx)
    if not links:
        return []
    link = links[0]
    params = ", ".join(link.params[:4])
    how = (
        f"adres materiału przekierowuje ({len(ctx.document.redirect_chain)} kroki) na stronę"
        if link.via_redirect
        else "zawiera link do strony"
    )
    evidence = [ctx.evidence.url(link.url, f"Link partnerski do {link.firm}")]
    if len(links) > 1:
        evidence += [ctx.evidence.url(other.url, f"Link partnerski do {other.firm}") for other in links[1:3]]
    base = (
        f"Materiał „{publisher}” {how} „{link.firm}” ({link.host}) z parametrami partnerskimi / śledzącymi "
        f"({params}), co wskazuje na relację komercyjną z firmą."
    )
    data = {"host": link.host, "params": link.params, "firm": link.firm, "links": len(links)}
    if marked:
        return [
            PluginFinding(
                "AFFILIATE_LINK_DISCLOSED", "info", base + " Materiał jest oznaczony jako reklama.", evidence, 0.9, data
            )
        ]
    return [
        PluginFinding(
            "AFFILIATE_LINK_TO_FIRM",
            "medium",
            base + " Materiał nie jest oznaczony jako reklama ani współpraca.",
            evidence,
            0.85,
            data,
        )
    ]


def _concealed(ctx: AnalysisContext, start: int, end: int) -> bool:
    segs = ctx.page.segments_in(start, end)
    return bool(segs) and all(s.style.hidden or s.style.collapsed for s in segs)
