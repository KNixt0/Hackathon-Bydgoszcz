"""Rules 16-18: tax treatment and references to the supervisory authority."""

from __future__ import annotations

from .. import lexicon as lx
from ..context import Hit
from ..preprocess import Sentence
from .base import RuleOutcome, RuleView, failed, not_applicable, passed, rule

NO_SUPERVISOR = "Materiał nie odwołuje się do KNF ani innego organu nadzoru."


@rule("16", "Informacja podatkowa", "art. 44 ust. 7 rozporządzenia del. 2017/565")
def tax_information(v: RuleView) -> RuleOutcome:
    hits = v.facts.tax
    if not hits:
        return not_applicable("Materiał nie odwołuje się do traktowania podatkowego.")
    ev = [v.ctx.quote(hits[0], label="Odwołanie do traktowania podatkowego")]
    folded = v.page.folded
    missing = []
    if not lx.TAX_INDIVIDUAL.search(folded):
        missing.append("zależności od indywidualnej sytuacji klienta")
    if not lx.TAX_MAY_CHANGE.search(folded):
        missing.append("możliwości zmian w przyszłości")
    if missing:
        return failed(f"Odwołanie do podatków bez wyraźnej informacji o: {' oraz '.join(missing)}.", 0.8, ev)
    return passed(
        "Przy odwołaniu do podatków wskazano zależność od indywidualnej sytuacji klienta i możliwość zmian.", 0.85, ev
    )


def _neighbours(v: RuleView, sentence: Sentence) -> list[Sentence]:
    """Previous / next sentence when they sit on the same line (same paragraph)."""
    sents = v.page.sentences
    i = next(k for k, s in enumerate(sents) if s is sentence)
    out = []
    for j in (i - 1, i + 1):
        if 0 <= j < len(sents):
            a, b = sorted((sents[j], sentence), key=lambda s: s.start)
            if "\n" not in v.page.text[a.end : b.start]:
                out.append(sents[j])
    return out


def _risk_sentence(v: RuleView, sentence: Sentence) -> bool:
    return any(h.sentence is sentence for h in v.risk)


@rule("17", "Zakaz sugerowania aprobaty organu nadzoru", "art. 44 ust. 8 rozporządzenia del. 2017/565")
def supervisor_approval(v: RuleView) -> RuleOutcome:
    refs: list[Hit] = v.facts.supervisor
    if not refs:
        return not_applicable(NO_SUPERVISOR)
    for h in refs:
        f = h.sentence.folded
        if lx.APPROVAL_WORDS.search(f) and not lx.SUPERVISOR_NEGATION.search(f):
            return failed(
                "Odwołanie do organu nadzoru sugeruje, że zatwierdził lub zaaprobował on produkt albo usługę.",
                0.85,
                [v.ctx.quote(h, label="Sugestia aprobaty organu nadzoru")],
            )
    return passed(
        "Odwołanie do organu nadzoru ma charakter informacyjny i nie sugeruje aprobaty produktu.",
        0.75,
        [v.ctx.quote(refs[0], label="Odwołanie do organu nadzoru")],
    )


@rule("18", "Nadzór jako argument bezpieczeństwa", "art. 44 ust. 8 rozporządzenia del. 2017/565")
def supervisor_safety(v: RuleView) -> RuleOutcome:
    refs: list[Hit] = v.facts.supervisor
    if not refs:
        return not_applicable(NO_SUPERVISOR)
    for h in refs:
        f = h.sentence.folded
        if lx.SUPERVISOR_NEGATION.search(f) or _risk_sentence(v, h.sentence):
            continue
        if lx.SAFETY_WORDS.search(f):
            return failed(
                "Odwołanie do organu nadzoru jest użyte jako argument za bezpieczeństwem inwestycji.",
                0.85,
                [v.ctx.quote(h, label="Nadzór jako argument bezpieczeństwa")],
            )
        for n in _neighbours(v, h.sentence):
            if (
                lx.SAFETY_WORDS.search(n.folded)
                and not _risk_sentence(v, n)
                and not lx.SUPERVISOR_NEGATION.search(n.folded)
            ):
                a, b = min(n.start, h.sentence.start), max(n.end, h.sentence.end)
                return failed(
                    "Zapewnienie o bezpieczeństwie sąsiaduje bezpośrednio z odwołaniem do organu nadzoru, "
                    "co sugeruje, że nadzór gwarantuje bezpieczeństwo inwestycji.",
                    0.65,
                    [v.ctx.evidence.quote(a, b, "Nadzór jako argument bezpieczeństwa")],
                )
    return passed(
        "Odwołanie do organu nadzoru nie jest używane jako argument za bezpieczeństwem inwestycji.",
        0.75,
        [v.ctx.quote(refs[0], label="Odwołanie do organu nadzoru")],
    )
