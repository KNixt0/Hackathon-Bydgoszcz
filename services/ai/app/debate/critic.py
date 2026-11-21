"""Round 2: the Critic / Red-Teamer.

For every "for" claim the critic
  1. verifies grounding: all evidence ids resolve and every quote is an exact substring of
     the source text at its span; an ungrounded claim is rejected outright,
  2. runs the false-positive checks below (each one a small function) and sets the verdict
     upheld / weakened / rejected with an adjusted confidence,
and then raises the mitigating circumstances it found as "against" claims.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from .. import lexicon as lx
from ..context import AnalysisContext, EvidenceBook, firm_node_ids
from ..registries import REGISTRIES
from .models import AgentReport, DebateClaim

ADVISORY_CODES = {"ADVISORY_PHRASE", "PORTFOLIO_MANAGEMENT", "ADVISORY_SERVICE_OFFER"}
UNLISTED_CODES = {"REGISTRY_NOT_LISTED", "PROMOTED_FIRM_NOT_LISTED"}
FORENSIC_CODES = {"OPINION_SPIKE", "FRESH_ACCOUNT_CLUSTER", "NAME_PATTERN_CLUSTER", "FOREIGN_ORIGIN_CLUSTER"}
COMPANY_CODES = {"COMPANY_YOUNG", "LOW_SHARE_CAPITAL", "NO_FINANCIAL_STATEMENTS"}
UNMARKED_CODES = {"RULE_2", "UNMARKED_THIRD_PARTY_AD", "DISGUISED_AD"}
SMALL_SAMPLE = 20


def grounding_error(evidence: EvidenceBook, evidence_ids: list[str]) -> str | None:
    """None when the evidence is sound, else the reason (Polish) why it is not."""
    for ev_id in evidence_ids:
        item = evidence.get(ev_id)
        if item is None:
            return f"Dowód {ev_id} nie istnieje."
        if item.kind == "quote":
            if not item.quote or item.quote not in evidence.text:
                return f"Cytat w dowodzie {ev_id} nie występuje dosłownie w treści źródła."
            if item.span is None or evidence.text[item.span.start : item.span.end] != item.quote:
                return f"Zakres znaków dowodu {ev_id} nie odpowiada cytatowi."
    return None


@dataclass
class World:
    """Facts about the case the critic argues from."""

    ctx: AnalysisContext
    codes: set[str]  # every finding code, including info-level ones
    firm_listed: bool
    parent_listed: str | None  # name of a registered parent / group company
    cooperation_notified: bool | None
    ad_marked: bool
    first_party: bool
    promo: bool
    affiliate: bool
    reporting: bool
    disclaimer: bool
    comments: int
    hidden_ties: bool
    entity_unauthorised: bool


@dataclass
class Challenge:
    verdict: str  # weakened | rejected
    factor: float
    text: str


Check = Callable[[DebateClaim, World], Challenge | None]
CHECKS: list[Check] = []


def check(fn: Check) -> Check:
    CHECKS.append(fn)
    return fn


@check
def authorised_entity(c: DebateClaim, w: World) -> Challenge | None:
    if c.code in ADVISORY_CODES and w.firm_listed:
        return Challenge(
            "rejected",
            0.0,
            "Podmiot figuruje w rejestrze firm inwestycyjnych KNF; doradztwo i "
            "zarządzanie portfelem mogą mieścić się w zakresie jego zezwolenia, więc reguła nie ma tu "
            "zastosowania.",
        )
    return None


@check
def reporting_context(c: DebateClaim, w: World) -> Challenge | None:
    if w.reporting and c.code not in FORENSIC_CODES | {"WARNING_LISTED"}:
        return Challenge(
            "weakened",
            0.2,
            "Materiał ma charakter ostrzegawczy lub informacyjny: opisuje praktyki "
            "nieuczciwych podmiotów, a nie oferuje usługi.",
        )
    return None


@check
def advice_disclaimer(c: DebateClaim, w: World) -> Challenge | None:
    if c.code in ADVISORY_CODES and w.disclaimer:
        return Challenge(
            "weakened",
            0.8,
            "Materiał zawiera zastrzeżenie, że nie stanowi rekomendacji; samo "
            "zastrzeżenie nie wyłącza jednak kwalifikacji z art. 76.",
        )
    return None


@check
def group_company(c: DebateClaim, w: World) -> Challenge | None:
    if c.code in UNLISTED_CODES and w.parent_listed:
        return Challenge(
            "weakened",
            0.45,
            f"Spółka powiązana kapitałowo („{w.parent_listed}”) figuruje w rejestrze "
            "KNF; możliwe działanie w ramach grupy lub jako agent firmy inwestycyjnej, co wymaga "
            "wyjaśnienia.",
        )
    return None


@check
def same_group_brand(c: DebateClaim, w: World) -> Challenge | None:
    if (
        c.code in {"BRAND_IMPERSONATION", "NAME_SIMILAR_TO_REGISTERED"}
        and c.finding is not None
        and w.parent_listed
        and c.finding.data.get("registered") == w.parent_listed
    ):
        return Challenge(
            "rejected",
            0.0,
            "Podmiot jest powiązany kapitałowo z zarejestrowaną firmą, której marki "
            "używa; to ta sama grupa, a nie podszywanie się.",
        )
    return None


@check
def partial_snapshot(c: DebateClaim, w: World) -> Challenge | None:
    if c.finding is not None and c.finding.data.get("partial_snapshot"):
        return Challenge(
            "weakened",
            0.7,
            "Migawka tego rejestru jest niepełna (próbka demonstracyjna); brak wpisu "
            "wymaga potwierdzenia w rejestrze źródłowym.",
        )
    return None


@check
def own_channel(c: DebateClaim, w: World) -> Challenge | None:
    if c.code == "RULE_2" and w.first_party:
        return Challenge(
            "weakened",
            0.6,
            "Materiał opublikowała sama firma we własnym kanale; jego reklamowy "
            "charakter jest dla odbiorcy rozpoznawalny.",
        )
    return None


@check
def no_commercial_link(c: DebateClaim, w: World) -> Challenge | None:
    if c.code in UNMARKED_CODES | {"COOPERATION_NOT_NOTIFIED"} and not w.first_party:
        if w.cooperation_notified is not False and not w.affiliate and not w.hidden_ties:
            return Challenge(
                "weakened",
                0.7,
                "Brak dowodu relacji komercyjnej między autorem a firmą (brak linku "
                "partnerskiego, zgłoszenia i powiązań); materiał może być treścią własną autora.",
            )
        if c.code == "COOPERATION_NOT_NOTIFIED" and not w.promo:
            return Challenge(
                "weakened",
                0.5,
                "Materiał nie ma wyraźnych cech przekazu reklamowego; wzmianka o "
                "firmie może mieć charakter redakcyjny.",
            )
    return None


@check
def disclosed_relation(c: DebateClaim, w: World) -> Challenge | None:
    if c.code in {"PR_CONFLICT_PATH", "PERSONAL_TIE_PATH"}:
        if w.cooperation_notified and w.ad_marked:
            return Challenge(
                "weakened",
                0.4,
                "Współpraca jest zgłoszona do UKNF i oznaczona w materiale, więc "
                "powiązanie nie jest ukrywane przed odbiorcą.",
            )
        return Challenge(
            "weakened",
            0.85,
            "Powiązanie osobowe samo nie dowodzi wynagrodzenia za publikację; "
            "wymaga potwierdzenia (umowy, przepływy finansowe).",
        )
    return None


@check
def lawful_circumstance(c: DebateClaim, w: World) -> Challenge | None:
    if c.code in COMPANY_CODES:
        return Challenge(
            "weakened", 0.7, "Okoliczność sama w sobie zgodna z prawem; podnosi ryzyko, ale nie stanowi naruszenia."
        )
    return None


@check
def forensic_limits(c: DebateClaim, w: World) -> Challenge | None:
    if c.code not in FORENSIC_CODES:
        return None
    if w.comments < SMALL_SAMPLE:
        return Challenge("weakened", 0.7, f"Mała próba ({w.comments} komentarzy); wniosek statystycznie niepewny.")
    if c.code == "OPINION_SPIKE" and c.finding and c.finding.data.get("new_account_share", 1.0) < 0.3:
        return Challenge(
            "weakened",
            0.5,
            "Skok pochodzi głównie ze starych kont; może wynikać z naturalnego zainteresowania po publikacji.",
        )
    if not w.entity_unauthorised:
        return Challenge(
            "weakened",
            0.85,
            "Wzorzec aktywności kont nie przesądza, kto ją zlecił; brak dowodu, że stoi za nią promowany podmiot.",
        )
    return None


@check
def imbalance_with_full_warning(c: DebateClaim, w: World) -> Challenge | None:
    if c.code == "PROFIT_RISK_IMBALANCE" and any(lx.RISK_STANDARD.search(h.sentence.folded) for h in w.ctx.facts.risk):
        return Challenge(
            "weakened",
            0.6,
            "Materiał zawiera pełne, standardowe ostrzeżenie o ryzyku; sama "
            "dysproporcja objętości ma mniejsze znaczenie.",
        )
    return None


@check
def heuristic_signal(c: DebateClaim, w: World) -> Challenge | None:
    if c.finding is not None and c.finding.confidence < 0.6:
        return Challenge(
            "weakened", 0.8, "Sygnał heurystyczny o niskiej pewności; wymaga potwierdzenia przez analityka."
        )
    return None


class Critic:
    name = "Krytyk / Red-Teamer"
    role = "Weryfikacja cytatów, wzorce fałszywych alarmów, okoliczności łagodzące"

    def build_world(self, ctx: AnalysisContext, reports: list[AgentReport]) -> World:
        findings = [f for r in reports for res in r.results for f in res.findings]
        codes = {f.code for f in findings}
        facts, ent = ctx.facts, ctx.entities
        firm_listed = bool(codes & {"FIRM_REGISTERED", "ENTITY_AUTHORISED"})
        affiliate = any(
            lx.rx(
                r"link\w* (?:partnersk|afiliac|polecajac)",
                r"reflink",
                r"kod\w* (?:rabatow|promocyjn|polecaj)",
                r"z (?:mojego|tego) linku",
                r"afiliac",
            ).search(h.sentence.folded)
            for h in facts.cta
        )
        cta = bool(facts.cta)
        reporting = bool(lx.REPORTING_CONTEXT.search(ctx.page.folded)) and not cta
        unauthorised = bool(codes & (UNLISTED_CODES | {"WARNING_LISTED", "BRAND_IMPERSONATION"}))
        parent = self._registered_parent(ctx) if not firm_listed else None
        return World(
            ctx=ctx,
            codes=codes,
            firm_listed=firm_listed,
            parent_listed=parent,
            cooperation_notified=ctx.context.cooperation_notified,
            ad_marked="AD_MARKED" in codes,
            first_party=bool(ent.firm) and not ent.third_party,
            promo=bool(facts.profit_claims or cta),
            affiliate=affiliate,
            reporting=reporting,
            disclaimer=bool(lx.ADVICE_DISCLAIMER.search(ctx.page.folded)),
            comments=len(ctx.context.comments),
            hidden_ties=bool(codes & {"PR_CONFLICT_PATH", "PERSONAL_TIE_PATH"}),
            entity_unauthorised=unauthorised and not parent,
        )

    @staticmethod
    def _registered_parent(ctx: AnalysisContext) -> str | None:
        """A company tied to the firm by ownership that is itself in a KNF register."""
        graph, firm = ctx.context.graph, ctx.entities.firm
        if not graph or not firm:
            return None
        nodes = {n.id: n for n in graph.nodes}
        firm_ids = set(firm_node_ids(graph, firm.name))
        for e in graph.edges:
            if e.type not in {"owner", "beneficial_owner"}:
                continue
            other = e.target if e.source in firm_ids else e.source if e.target in firm_ids else None
            if other and other in nodes and nodes[other].type == "company":
                match = ctx.registries.lookup("knf_investment_firms", nodes[other].label)
                if match and match.listed:
                    return match.entry["name"]
        return None

    def review_claim(self, claim: DebateClaim, world: World) -> None:
        error = grounding_error(world.ctx.evidence, claim.evidence_ids)
        if error:
            claim.verdict, claim.confidence = "rejected", 0.0
            claim.critique = f"Odrzucono: brak ugruntowania w źródle. {error}"
            return
        challenges = [ch for fn in CHECKS if (ch := fn(claim, world))]
        if not challenges:
            claim.verdict = "upheld"
            claim.critique = "Dowody zweryfikowane w źródle; nie znaleziono okoliczności podważających tezę."
            return
        if any(ch.verdict == "rejected" for ch in challenges):
            claim.verdict, claim.confidence = "rejected", 0.0
        else:
            factor = 1.0
            for ch in challenges:
                factor *= ch.factor
            claim.verdict = "weakened"
            claim.confidence = round(claim.confidence * factor, 3)
        claim.critique = " ".join(ch.text for ch in challenges)

    def mitigations(self, world: World, reports: list[AgentReport], ids: Iterator[int]) -> list[DebateClaim]:
        """Counter-arguments ("against" claims) built from exculpatory facts."""
        ctx = world.ctx
        info = {f.code: f for r in reports for res in r.results for f in res.findings if f.severity == "info"}
        rules = next((res.rules for r in reports for res in r.results if res.rules), None) or []
        rule = {r.id: r for r in rules}
        out: list[DebateClaim] = []
        has_for_claims = any(c.stance == "for" for r in reports for c in r.claims)

        def add(key: str, text: str, confidence: float, evidence_ids: list[str]) -> None:
            out.append(
                DebateClaim(
                    id=f"c{next(ids)}",
                    stance="against",
                    text=text,
                    confidence=confidence,
                    evidence_ids=evidence_ids,
                    agent=self.name,
                    code=key,
                    critique="Okoliczność łagodząca podniesiona przez krytyka.",
                )
            )

        for code in ("FIRM_REGISTERED", "ENTITY_AUTHORISED"):
            if code in info:
                add("FIRM_REGISTERED", info[code].text, info[code].confidence, info[code].evidence_ids)
                break
        if world.parent_listed:
            add(
                "PARENT_REGISTERED",
                f"Spółka powiązana kapitałowo z promowanym podmiotem („{world.parent_listed}”) "
                "figuruje w rejestrze firm inwestycyjnych KNF.",
                0.8,
                [
                    ctx.evidence.registry(
                        "knf_investment_firms",
                        world.parent_listed,
                        f"Rejestr firm inwestycyjnych (KNF): „{world.parent_listed}” – figuruje",
                        REGISTRIES["knf_investment_firms"][1],
                    )
                ],
            )
        for code in (
            "COOPERATION_NOTIFIED",
            "AD_MARKED",
            "ORGANIC_OPINIONS",
            "NO_HIDDEN_TIES",
            "LEGAL_ADVISER_ACTIVE",
            "ADVISOR_LICENCE_VALID",
        ):
            if code in info:
                add(code, info[code].text, info[code].confidence, info[code].evidence_ids)
        if "AD_MARKED" not in info and rule.get("2") and rule["2"].status == "pass":
            add(
                "AD_MARKED",
                "Materiał jest oznaczony jako reklamowy.",
                rule["2"].confidence,
                [e for e in rule["2"].evidence_ids if ctx.evidence.get(e) and ctx.evidence.get(e).kind == "quote"],
            )
        r3 = rule.get("3")
        if (
            r3
            and r3.status == "pass"
            and ctx.facts.profit_claims
            and any(lx.RISK_STANDARD.search(h.sentence.folded) for h in ctx.facts.risk)
        ):
            add(
                "RISK_WARNING_ADJACENT",
                "Pełne, standardowe ostrzeżenie o ryzyku znajduje się bezpośrednio przy twierdzeniach o zyskach.",
                r3.confidence,
                list(r3.evidence_ids),
            )
        elif r3 and r3.status == "pass" and ctx.facts.profit_claims and has_for_claims:
            add(
                "RISK_INFO_PRESENT",
                "Twierdzeniom o zyskach towarzyszy w materiale informacja o ryzyku, choć nie w "
                "pełnym, standardowym brzmieniu.",
                r3.confidence,
                [e for e in r3.evidence_ids if ctx.evidence.get(e) and ctx.evidence.get(e).kind == "quote"],
            )
        if world.reporting:
            m = lx.REPORTING_CONTEXT.search(ctx.page.folded)
            add(
                "REPORTING_CONTEXT",
                "Materiał opisuje lub ostrzega przed nieuczciwymi praktykami i nie zawiera "
                "wezwania do skorzystania z oferty.",
                0.8,
                [ctx.quote_sentence(m.start(), "Kontekst ostrzegawczy")],
            )
        if world.disclaimer:
            m = lx.ADVICE_DISCLAIMER.search(ctx.page.folded)
            add(
                "ADVICE_DISCLAIMER",
                "Materiał zastrzega, że nie stanowi rekomendacji inwestycyjnej.",
                0.7,
                [ctx.quote_sentence(m.start(), "Zastrzeżenie o braku rekomendacji")],
            )
        has_for = any(c.stance == "for" for r in reports for c in r.claims)
        checked_warnings = any(
            ch.registry == "knf_public_warnings" and ch.status == "not_listed"
            for r in reports
            for res in r.results
            for ch in res.registry_checks
        )
        if has_for and checked_warnings and "WARNING_LISTED" not in world.codes:
            subject = ctx.entities.firm.name if ctx.entities.firm else "podmiot"
            add(
                "NOT_ON_WARNING_LIST",
                f"„{subject}” nie figuruje na liście ostrzeżeń publicznych KNF; na tym etapie "
                "nie ma dowodu wyłudzenia środków ani szkody klientów.",
                0.7,
                [
                    ctx.evidence.registry(
                        "knf_public_warnings",
                        subject,
                        f"Lista ostrzeżeń publicznych KNF: „{subject}” – brak wpisu",
                        REGISTRIES["knf_public_warnings"][1],
                    )
                ],
            )
        return out

    def review(
        self, ctx: AnalysisContext, reports: list[AgentReport], ids: Iterator[int]
    ) -> tuple[list[DebateClaim], str, World]:
        world = self.build_world(ctx, reports)
        for_claims = [c for r in reports for c in r.claims]
        for claim in for_claims:
            self.review_claim(claim, world)
        against = self.mitigations(world, reports, ids)
        for claim in against:  # counter-arguments must be grounded too
            error = grounding_error(ctx.evidence, claim.evidence_ids)
            if error:
                claim.verdict, claim.confidence, claim.critique = "rejected", 0.0, error
        n = {v: sum(c.verdict == v for c in for_claims) for v in ("upheld", "weakened", "rejected")}
        summary = (
            f"Sprawdzono {len(for_claims)} tez: {n['upheld']} podtrzymano, {n['weakened']} osłabiono, "
            f"{n['rejected']} odrzucono. Podniesiono {len(against)} okoliczności łagodzących."
        )
        return against, summary, world
