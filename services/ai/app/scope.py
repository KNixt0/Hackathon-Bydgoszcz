"""Is the material within UKNF's remit as covered by modules 1-3?

The modules look at investment firms, financial instruments and investment services offered
on the Polish market. A promotional text about a car, a payday loan, a bank deposit, crypto
coins without any financial instrument, an insurance policy or tax advice is somebody else's
matter (or a different UKNF area), so it must not end up in the queue as a violation just
because it says "zysk" or "inwestuj".

Decision order (first match wins):
1. the entity is on the KNF public warnings list            -> in scope (warning_listed)
2. the entity is in a KNF register (investment firms, TFI)   -> in scope (supervised_entity),
   except a foreign firm notified only cross-border whose material is not in Polish
3. the text offers financial instruments / investment services:
   aimed at the Polish market                                -> in scope (investment_offer)
   otherwise                                                 -> out of scope (foreign_market)
4. otherwise the strongest out-of-scope category wins (credit, deposit, crypto, insurance,
   tax / legal advice), else "no_financial_offer".

`authority_hint` is a hint for the analyst, not a legal qualification.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .lexicon import ADVISORY_SERVICE, PORTFOLIO_MANAGEMENT, rx
from .registries import KNF_OTHER_LICENSED, KNF_SUB_REGISTERS
from .schemas import Scope

if TYPE_CHECKING:
    from .context import AnalysisContext

# Financial instruments and investment services, stricter than lexicon.INSTRUMENT: no bare
# "spółka", "indeks" or "fundusz" (EU funds, a holiday fund) and no "akcja" (a promotion).
FIN_INSTRUMENT = rx(
    r"\bakcje\b",
    r"\bakcjami\b",
    r"\bakcj\w+ (?:spol\w+|gieldow\w+|na gpw|dywidendow\w+|notowan\w+|firm\w*)",
    r"\bakcjonariusz\w*",
    r"\bobligacj\w+",
    r"\bpapier\w+ wartosciow\w+",
    r"\bcertyfikat\w+ inwestycyjn\w+",
    r"\blist\w+ zastawn\w+",
    r"\bwarrant\w+",
    r"\bkwit\w+ depozytow\w+",
    r"\bjednost\w+ uczestnictwa",
    r"\bfundusz\w* (?:inwestycyjn\w+|akcji|obligacji|etf|indeksow\w+|zrownowazon\w+|pieniezn\w+|dluzn\w+)",
    r"\b(?:tfi|fio|sfio|fiz)\b",
    r"\btowarzystw\w+ funduszy",
    r"\betf\w*",
    r"\binstrument\w+ (?:finansow\w+|pochodn\w+|rynku pienieznego)",
    r"\bopcj\w+ (?:binarn\w+|kupna|sprzedazy|na )",
    r"\bkontrakt\w+ (?:terminow\w+|na roznic\w+|futures|cfd)",
    r"\bcfd\w*\b",
    r"\bforex\w*",
    r"\bpar\w* walutow\w+",
    r"\bderywat\w+",
    r"\bfutures\b",
    r"\bstocks?\b|\bshares\b|\bbonds?\b|\betfs?\b",
    r"\bgield\w* papierow\w+",
    r"\bgpw\b|\bnewconnect\b|\bnasdaq\b|\bnyse\b",
    r"\b(?:rachun\w+|kont\w+) maklersk\w+",
    r"\b(?:dom\w*|biur\w+) maklersk\w+",
    r"\bbroker\w*",
    r"\bplatform\w+ (?:inwestycyjn\w+|transakcyjn\w+|tradingow\w+)",
    r"\btrading\w*",
    r"\binwestowan\w+ na gieldzie",
    r"\bportfel\w* inwestycyjn\w+",
    r"\bike\b|\bikze\b",
    r"\binvest(?:ing|ment)s? (?:in|account|platform|advice|portfolio)",
)

# Weaker signal: a promise of investment returns without naming an instrument ("wypłacamy zyski co
# tydzień", "20% rocznie", "stopa zwrotu"). Typical of unlicensed schemes, so it keeps the material in
# scope unless the text is clearly about credit, deposits, crypto, insurance or tax / legal advice.
RETURN_PROMISE = rx(
    r"\d{1,4}(?:[.,]\d+)?\s?(?:%|proc\w*)\s+(?:\w+ ){0,2}(?:rocznie|miesiecznie|tygodniowo|dziennie|w skali roku|"
    r"w (?:rok|miesiac|kwartal|tydzien)|zysk\w*|zwrot\w*)",
    r"\bstop\w+ zwrotu",
    r"\bzwrot\w* z inwestycj\w+",
    r"\b(?:wyplac|wyplat)\w* (?:\w+ )?zysk\w*",
    r"\bzysk\w* (?:co|kazdego|kazdy) (?:tydzien|tygodnia|miesiac|miesiaca|dzien|dnia)",
    r"\b(?:zainwestuj|inwestuj|wplac)\w*\s+(?:juz\s+)?(?:\d|kwot\w+|kapital\w*|pieniadz\w*|srodk\w+|oszczednosc\w*)",
    r"\bpomnaz\w+ (?:\w+ )?(?:oszczednosc\w*|kapital\w*|pieniadz\w*|majat\w+)",
    r"\bpasywn\w+ dochod\w*",
)

CREDIT = rx(
    r"\bpozycz\w+",
    r"\bchwilow\w+",
    r"\bkredyt\w*",
    r"\brrso\b",
    r"\bbik\b",
    r"\bkart\w+ kredytow\w+",
    r"\braty? 0\s?%",
    r"\bkonsolidacj\w+",
)
DEPOSIT = rx(
    r"\blokat\w+",
    r"\b(?:kont\w+|rachun\w+) oszczednosciow\w+",
    r"\bbfg\b",
)
CRYPTO = rx(
    r"\bkryptowalut\w+",
    r"\bkrypto\w*",
    r"\bbitcoin\w*",
    r"\bbtc\b",
    r"\beth\b|\bethereum\b",
    r"\baltcoin\w*",
    r"\btoken\w*",
    r"\bnft\w*",
    r"\bblockchain\w*",
    r"\bcrypto\w*",
    r"\bmemecoin\w*",
)
INSURANCE = rx(
    r"\bubezpiecz\w+",
    r"\bpolis\w+",
    r"\bufk\b",
    r"\binsurance\b",
)
TAX_LEGAL = rx(
    r"\bdorad\w+ podatkow\w+",
    r"\bpodatk\w+ (?:dochodow\w+|vat|pit|cit)",
    r"\brozlicz\w+ (?:pit|podatk\w+)",
    r"\bradc\w+ prawn\w+",
    r"\badwokat\w*",
    r"\bkancelari\w+",
)

CATEGORY_HINTS = {
    "consumer_credit": (
        "Kredyt lub pożyczka konsumencka, nie instrument finansowy.",
        "Ochrona konsumentów (UOKiK); instytucje pożyczkowe można sprawdzić w rejestrze KNF.",
    ),
    "deposit": (
        "Produkt depozytowy (lokata, konto oszczędnościowe), nie instrument finansowy.",
        "Poza modułami InvestWatch; reklama usług bankowych podlega innym przepisom.",
    ),
    "crypto": (
        "Kryptoaktywa bez instrumentu finansowego w rozumieniu ustawy o obrocie.",
        "Poza modułami InvestWatch; właściwość według przepisów o rynku kryptoaktywów.",
    ),
    "insurance": (
        "Produkt ubezpieczeniowy, także z elementem inwestycyjnym (UFK).",
        "Poza modułami InvestWatch (nadzór ubezpieczeniowy, inne przepisy o reklamie).",
    ),
    "tax_legal": (
        "Doradztwo podatkowe lub prawne, nie doradztwo inwestycyjne.",
        "Samorząd zawodowy (KIDP, KIRP).",
    ),
    "foreign_market": (
        "Oferta inwestycyjna niekierowana na rynek polski (inny język, brak polskiej domeny i wpisu w polskich "
        "rejestrach).",
        "Moduł 1 obejmuje zagraniczne firmy tylko w reklamach polskojęzycznych.",
    ),
    "no_financial_offer": (
        "Materiał nie dotyczy instrumentów finansowych ani usług inwestycyjnych.",
        None,
    ),
}

# Investment registers of entities that act in Poland (not only cross-border notified).
_POLISH_REGISTERS = [r for r in KNF_SUB_REGISTERS if r != "knf_foreign_cross_border"] + KNF_OTHER_LICENSED
_TFI_NAME = re.compile(r"\bTFI\b|towarzystw\w* funduszy inwestycyjnych", re.I)


def is_tfi_name(name: str) -> bool:
    return bool(_TFI_NAME.search(name))


def _registered(ctx: AnalysisContext, name: str, registers: list[str]) -> str | None:
    for registry in registers:
        match = ctx.registries.lookup(registry, name)
        if match and match.listed:
            return registry
    return None


def _names(ctx: AnalysisContext) -> list[str]:
    ent = ctx.entities
    return [p.name for p in (ent.firm, ent.advertiser) if p is not None]


def _polish_market(ctx: AnalysisContext) -> bool:
    return ctx.page.language == "pl" or ctx.host.endswith(".pl")


def _hits(pattern: re.Pattern[str], folded: str) -> int:
    return sum(1 for _ in pattern.finditer(folded))


def assess_scope(ctx: AnalysisContext) -> Scope:
    folded = ctx.page.folded
    names = _names(ctx)

    for name in names:
        warn = ctx.registries.lookup("knf_public_warnings", name)
        if warn and warn.listed:
            return Scope(
                in_scope=True,
                category="investment",
                basis="warning_listed",
                reason=f"Podmiot „{name}” figuruje na liście ostrzeżeń publicznych KNF.",
            )

    for name in names:
        registry = _registered(ctx, name, _POLISH_REGISTERS)
        if registry:
            return Scope(
                in_scope=True,
                category="investment",
                basis="supervised_entity",
                reason=f"Podmiot „{name}” figuruje w rejestrze KNF i podlega nadzorowi UKNF.",
            )
        if _registered(ctx, name, ["knf_foreign_cross_border"]):
            if _polish_market(ctx):
                return Scope(
                    in_scope=True,
                    category="investment",
                    basis="supervised_entity",
                    reason=f"Zagraniczna firma inwestycyjna „{name}” działa w Polsce transgranicznie, a materiał "
                    "jest polskojęzyczny.",
                )
            reason, hint = CATEGORY_HINTS["foreign_market"]
            return Scope(
                in_scope=False, category="foreign_market", basis="out_of_scope", reason=reason, authority_hint=hint
            )

    investment = (
        FIN_INSTRUMENT.search(folded)
        or ADVISORY_SERVICE.search(folded)
        or PORTFOLIO_MANAGEMENT.search(folded)
        or any(is_tfi_name(n) for n in names)
    )
    if investment:
        return _investment_scope(ctx)

    counts = {
        "consumer_credit": _hits(CREDIT, folded),
        "deposit": _hits(DEPOSIT, folded),
        "crypto": _hits(CRYPTO, folded),
        "insurance": _hits(INSURANCE, folded),
        "tax_legal": _hits(TAX_LEGAL, folded),
    }
    if not any(counts.values()) and RETURN_PROMISE.search(folded):
        return _investment_scope(ctx)
    category = max(counts, key=lambda k: counts[k]) if any(counts.values()) else "no_financial_offer"
    reason, hint = CATEGORY_HINTS[category]
    return Scope(in_scope=False, category=category, basis="out_of_scope", reason=reason, authority_hint=hint)


def _investment_scope(ctx: AnalysisContext) -> Scope:
    if _polish_market(ctx):
        return Scope(
            in_scope=True,
            category="investment",
            basis="investment_offer",
            reason="Materiał dotyczy instrumentów finansowych, usług inwestycyjnych lub obietnicy zysków z "
            "inwestycji na rynku polskim.",
        )
    reason, hint = CATEGORY_HINTS["foreign_market"]
    return Scope(in_scope=False, category="foreign_market", basis="out_of_scope", reason=reason, authority_hint=hint)

