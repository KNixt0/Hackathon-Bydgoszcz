"""Module 3: investment advice / portfolio management offered without authorisation.

Art. 76 of the act on trading in financial instruments: investment advice is a personalised
recommendation to buy, sell or hold financial instruments (vocabulary of art. 2 and 3).
The plugin looks for such offers and checks whether the entity behind them is authorised.
"""

from __future__ import annotations

import re

from .. import lexicon as lx
from ..context import ART_76, ATTACHMENT_ART76, AnalysisContext
from ..preprocess import Sentence, cosine
from ..scope import is_tfi_name
from ._registers import check_professionals, lookup_firm, make_check
from .base import Plugin, PluginFinding, PluginResult

ADVISORY_PROTOTYPES = [
    "Przygotujemy dla Ciebie indywidualne rekomendacje, które akcje kupić, a które sprzedać.",
    "Nasz doradca wskaże Ci dokładnie, kiedy kupić i kiedy sprzedać instrumenty finansowe, dopasowane do "
    "Twojej sytuacji.",
    "Otrzymasz spersonalizowany portfel inwestycyjny i sygnały kupna oraz sprzedaży.",
]
MAX_QUOTES = 3
_PUNCT = re.compile(r"\s*[,;:]\s*")
_BANK_NAME = re.compile(r"(?:\b|\bm)bank\b", re.I)


def _advisory_strength(s: Sentence) -> tuple[float, str] | None:
    """(confidence, description) when the sentence offers a recommendation on instruments."""
    f = _PUNCT.sub(" ", s.folded)  # "wskażę, które akcje" reads like "wskażę które akcje"
    rec = lx.RECOMMEND.search(f)
    if not rec or lx.NEGATION_BEFORE.search(f[max(0, rec.start() - 40) : rec.start()]):
        return None  # "nie rekomendujemy instrumentów" is the opposite of an offer
    inst, act, pers = lx.INSTRUMENT.search(f), lx.TRADE_ACTION.search(f), lx.PERSONALISATION.search(f)
    if inst and pers and act:
        return 0.92, "spersonalizowana rekomendacja nabycia/zbycia instrumentów finansowych"
    if inst and (pers or act):
        return 0.85, "rekomendacja dotycząca instrumentów finansowych"
    if (pers and act) or inst:
        return 0.7, "zapowiedź rekomendacji inwestycyjnych"
    return None


class ShadowAdvisoryPlugin(Plugin):
    id = "m3_shadow_advisory"
    module = 3
    description = (
        "Moduł 3: oferty typu wealth management / consulting inwestycyjny / family office przez podmioty "
        "bez zezwolenia: rekomendacje w rozumieniu art. 76 ustawy o obrocie, zarządzanie portfelem, "
        "gwarancje zysku, weryfikacja w rejestrach KNF, KIRP, KIDP, podszywanie się pod markę."
    )

    def _signals(self, ctx: AnalysisContext) -> dict:
        cached = ctx.__dict__.get("_m3_signals")
        if cached is not None:
            return cached
        sentences = ctx.page.sentences
        risk_ids = {id(h.sentence) for h in ctx.facts.risk}
        advisory = []
        for s in sentences:
            strength = _advisory_strength(s)
            if strength and not lx.ADVICE_DISCLAIMER.search(s.folded) and id(s) not in risk_ids:
                advisory.append((strength[0], strength[1], s))
        if not advisory:  # semantic fallback: paraphrases the lexicon does not cover
            protos = [ctx.embedder.embed(p) for p in ADVISORY_PROTOTYPES]
            for s in sentences:
                if len(s.text) > 40 and lx.INSTRUMENT.search(s.folded) and lx.PERSONALISATION.search(s.folded):
                    sim = max(cosine(ctx.embedder.embed(s.text), p) for p in protos)
                    if sim >= ctx.embedder.similar_threshold:
                        advisory.append(
                            (0.6, "sformułowanie zbliżone do oferty rekomendacji (podobieństwo semantyczne)", s)
                        )
        advisory.sort(key=lambda t: (-t[0], t[2].start))
        signals = {
            "advisory": advisory,
            "service": [
                (s, m)
                for s in sentences
                if (m := lx.ADVISORY_SERVICE.search(s.folded))
                and not lx.NEGATION_BEFORE.search(s.folded[max(0, m.start() - 40) : m.start()])
            ],
            "portfolio": [(s, m) for s in sentences if (m := lx.PORTFOLIO_MANAGEMENT.search(s.folded))],
        }
        ctx.__dict__["_m3_signals"] = signals
        return signals

    def applies(self, ctx: AnalysisContext) -> bool:
        if not ctx.scope.in_scope:
            return False
        sig = self._signals(ctx)
        return bool(sig["advisory"] or sig["service"] or sig["portfolio"] or ctx.context.module_hint == 3)

    def run(self, ctx: AnalysisContext) -> PluginResult:
        sig = self._signals(ctx)
        ent = ctx.entities
        findings: list[PluginFinding] = []
        checks = []
        art76 = ctx.evidence.legal(
            ART_76,
            "Definicja doradztwa inwestycyjnego (rekomendacje nabycia, zbycia lub trzymania instrumentów finansowych)",
            ATTACHMENT_ART76,
        )
        art2 = ctx.evidence.legal(
            "art. 2 i 3 ustawy o obrocie instrumentami finansowymi",
            "Katalog instrumentów finansowych i papierów wartościowych",
            ATTACHMENT_ART76,
        )

        for conf, what, s in sig["advisory"][:MAX_QUOTES]:
            findings.append(
                PluginFinding(
                    "ADVISORY_PHRASE",
                    "high" if conf >= 0.8 else "medium",
                    f"Oferta zawiera sformułowanie wskazujące na doradztwo inwestycyjne ({what}).",
                    [
                        ctx.evidence.quote(s.start, s.end, "Sformułowanie wskazujące na doradztwo inwestycyjne"),
                        art76,
                        art2,
                    ],
                    conf,
                )
            )
        if sig["portfolio"]:
            s, _ = sig["portfolio"][0]
            findings.append(
                PluginFinding(
                    "PORTFOLIO_MANAGEMENT",
                    "high",
                    "Oferta obejmuje zarządzanie portfelem lub środkami klienta, co wymaga zezwolenia KNF.",
                    [ctx.evidence.quote(s.start, s.end, "Oferta zarządzania portfelem"), art76],
                    0.8,
                )
            )
        if sig["service"] and not sig["advisory"] and not sig["portfolio"]:
            s, m = sig["service"][0]
            findings.append(
                PluginFinding(
                    "ADVISORY_SERVICE_OFFER",
                    "low",
                    f"Materiał oferuje usługę typu „{ctx.page.text[s.start + m.start() : s.start + m.end()]}”, która może "
                    "obejmować doradztwo inwestycyjne.",
                    [ctx.evidence.quote(s.start, s.end, "Oferta usługi inwestycyjnej")],
                    0.55,
                )
            )
        if ctx.facts.guarantees:
            h = ctx.facts.guarantees[0]
            findings.append(
                PluginFinding(
                    "GUARANTEED_RETURN",
                    "high",
                    "Oferta obiecuje gwarantowany zysk lub brak ryzyka.",
                    [ctx.quote(h, label="Obietnica gwarantowanego zysku")],
                    0.85,
                )
            )

        offer = bool(sig["advisory"] or sig["portfolio"])  # a concrete regulated service is offered
        entity = ent.firm.name if ent.firm else (ent.advertiser.name if ent.advertiser else None)
        if entity:
            lookup = lookup_firm(ctx, entity)
            checks += lookup.checks
            if lookup.warning:
                findings.append(
                    PluginFinding(
                        "WARNING_LISTED",
                        "high",
                        f"Podmiot „{entity}” figuruje na liście ostrzeżeń publicznych KNF.",
                        lookup.evidence_ids,
                        0.95,
                    )
                )
            if lookup.listed:
                findings.append(
                    PluginFinding(
                        "ENTITY_AUTHORISED",
                        "info",
                        f"Podmiot „{entity}” figuruje w rejestrach firm inwestycyjnych KNF.",
                        lookup.evidence_ids,
                        0.95,
                        {"entry": lookup.listed.entry["name"]},
                    )
                )
            elif lookup.other_licence:
                findings.append(
                    PluginFinding(
                        "ENTITY_AUTHORISED",
                        "info",
                        f"Podmiot „{entity}” figuruje w rejestrze towarzystw funduszy inwestycyjnych KNF: ma zezwolenie "
                        "KNF w innym reżimie niż firma inwestycyjna (zarządzanie portfelami i doradztwo w zakresie "
                        "objętym zezwoleniem TFI).",
                        lookup.evidence_ids,
                        0.95,
                        {"entry": lookup.other_licence.entry["name"]},
                    )
                )
            elif is_tfi_name(entity) or _BANK_NAME.search(entity):
                kind = "towarzystwo funduszy inwestycyjnych" if is_tfi_name(entity) else "bank"
                findings.append(
                    PluginFinding(
                        "SUPERVISED_FORM_UNVERIFIED",
                        "low",
                        f"Podmiot „{entity}” przedstawia się jako {kind}, czyli podmiot nadzorowany przez KNF w innym "
                        "reżimie niż firma inwestycyjna; nie dopasowano go do rejestru w migawce. Sprawdź wpis w "
                        "wyszukiwarce podmiotów KNF przed dalszą oceną.",
                        lookup.evidence_ids,
                        0.6,
                    )
                )
            elif sig["service"] and not offer:
                findings.append(
                    PluginFinding(
                        "UNREGISTERED_SERVICE_PROVIDER",
                        "medium",
                        f"Podmiot „{entity}” reklamuje usługi inwestycyjne, a nie figuruje w rejestrach firm "
                        "inwestycyjnych KNF; zakres usług wymaga sprawdzenia.",
                        lookup.evidence_ids,
                        0.6,
                    )
                )
            elif offer:
                findings.append(
                    PluginFinding(
                        "REGISTRY_NOT_LISTED",
                        "high",
                        f"Podmiot „{entity}” oferuje usługi o charakterze doradztwa inwestycyjnego, a nie figuruje w "
                        "żadnym z pięciu rejestrów firm inwestycyjnych KNF.",
                        lookup.evidence_ids,
                        0.85,
                    )
                )
            findings += self._impersonation(ctx, entity, lookup)
        elif offer or sig["service"]:
            checks.append(
                make_check(
                    ctx,
                    "knf_investment_firms",
                    "(nie ustalono podmiotu)",
                    "not_checked",
                    "Materiał nie wskazuje podmiotu świadczącego usługę",
                )
            )
            findings.append(
                PluginFinding(
                    "ENTITY_UNIDENTIFIED",
                    "medium" if offer else "low",
                    "Nie da się ustalić, jaki podmiot świadczy oferowaną usługę, więc nie można potwierdzić jego "
                    "zezwolenia.",
                    [],
                    0.7,
                )
            )

        m = lx.LICENCE_NUMBER.search(ctx.page.folded)
        prof_checks, prof_findings = check_professionals(ctx, m.group(1).strip() if m else None)
        if m:
            for f in prof_findings:
                if f.code in {"FAKE_LICENCE", "ADVISOR_LICENCE_VALID"}:
                    f.evidence_ids.append(ctx.quote_sentence(m.start(), "Powołanie się na licencję doradcy"))
        return self.result(findings=findings + prof_findings, registry_checks=checks + prof_checks)

    def _impersonation(self, ctx: AnalysisContext, entity: str, lookup) -> list[PluginFinding]:
        """A registered firm's brand used by a different entity / on a different domain."""
        if lookup.listed or lookup.other_licence:
            return []
        candidates = []
        if lookup.similar:
            candidates.append(lookup.similar.entry)
        for _, _, entry in ctx.entities.registered_brands:
            if entry not in candidates:
                candidates.append(entry)
        for entry in candidates:
            domains = [d.lower() for d in entry.get("domains", [])]
            mention = next(((a, b) for a, b, e in ctx.entities.registered_brands if e is entry), None)
            ev = list(lookup.evidence_ids)
            if mention:
                ev.append(ctx.quote_sentence(mention[0], "Użycie marki zarejestrowanego podmiotu"))
            if domains and ctx.host and not any(ctx.host == d or ctx.host.endswith("." + d) for d in domains):
                ev.append(
                    ctx.evidence.url(
                        ctx.document.url, "Adres materiału (inna domena niż domena zarejestrowanego podmiotu)"
                    )
                )
                return [
                    PluginFinding(
                        "BRAND_IMPERSONATION",
                        "high",
                        f"Podmiot „{entity}” używa marki zarejestrowanej firmy „{entry['name']}”, ale działa pod inną "
                        f"nazwą prawną i w domenie {ctx.host}, która nie należy do tej firmy "
                        f"({', '.join(domains)}).",
                        ev,
                        0.85,
                        {"registered": entry["name"]},
                    )
                ]
            return [
                PluginFinding(
                    "NAME_SIMILAR_TO_REGISTERED",
                    "low",
                    f"Nazwa „{entity}” jest podobna do zarejestrowanej firmy „{entry['name']}”; możliwe podszywanie się "
                    "pod markę (brak danych o domenie do potwierdzenia).",
                    ev,
                    0.5,
                    {"registered": entry["name"]},
                )
            ]
        return []
