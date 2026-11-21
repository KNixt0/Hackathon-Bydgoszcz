"""Rules 9-10: is the warning understandable and in the language of the main message."""

from __future__ import annotations

import re

from .. import lexicon as lx
from ..preprocess import detect_language, tokenize
from ..preprocess.tokens import split_sentences
from . import settings
from .base import RuleOutcome, RuleView, failed, not_applicable, passed, rule
from .r04_08_visual import NO_RISK

_VOWEL_GROUPS = re.compile(r"[aeiouy]+")
LANG_NAMES = {"pl": "polski", "en": "angielski", "de": "niemiecki", "ru": "rosyjski/ukraiński"}


def fog_index(text: str) -> tuple[float, float]:
    """Polish variant of the Gunning FOG index and the average sentence length in words.

    FOG = 0.4 * (words per sentence + 100 * share of words with 4+ syllables).
    """
    sentences = split_sentences(text) or []
    words = tokenize(text)
    if not words or not sentences:
        return 0.0, 0.0
    hard = sum(1 for w in words if len(_VOWEL_GROUPS.findall(w)) >= 4)
    per_sentence = len(words) / len(sentences)
    return 0.4 * (per_sentence + 100 * hard / len(words)), per_sentence


@rule("9", "Zrozumiałość dla grupy docelowej", "art. 44 ust. 2 lit. d rozporządzenia del. 2017/565")
def risk_comprehensibility(v: RuleView) -> RuleOutcome:
    if not v.risk:
        return not_applicable(NO_RISK)
    ev = v.risk_quote()
    if any(lx.RISK_STANDARD.search(h.sentence.folded) for h in v.risk):
        return passed(
            "Zastosowano standardowe, powszechnie stosowane ostrzeżenie o ryzyku (odsetek rachunków "
            "detalicznych odnotowujących straty).",
            0.85,
            ev,
        )
    text = " ".join(h.sentence.text for h in v.risk)
    fog, per_sentence = fog_index(text)
    if per_sentence > settings.SENTENCE_WORDS_MAX or fog > settings.FOG_MAX:
        return failed(
            f"Ostrzeżenie o ryzyku jest trudne w odbiorze: średnio {per_sentence:.0f} słów w zdaniu, "
            f"indeks mglistości FOG {fog:.0f} (język specjalistyczny).",
            0.6,
            ev,
        )
    return passed(
        f"Ostrzeżenie jest sformułowane prostym językiem (średnio {per_sentence:.0f} słów w zdaniu, "
        f"indeks FOG {fog:.0f}).",
        0.7,
        ev,
    )


@rule("10", "Spójność językowa", "art. 44 ust. 2 lit. f rozporządzenia del. 2017/565")
def risk_language(v: RuleView) -> RuleOutcome:
    if not v.risk:
        return not_applicable(NO_RISK)
    risk_text = " ".join(h.sentence.text for h in v.risk)
    spans = [(h.start, h.end) for h in v.risk]
    main_text = " ".join(s.text for s in v.page.sentences if (s.start, s.end) not in spans)
    main_lang, main_conf = detect_language(main_text, default=v.page.language)
    risk_lang, risk_conf = detect_language(risk_text, default=main_lang)
    ev = v.risk_quote()
    if len(tokenize(risk_text)) >= 4 and risk_conf >= 0.5 and main_conf >= 0.5 and risk_lang != main_lang:
        return failed(
            f"Główny przekaz jest w języku: {LANG_NAMES.get(main_lang, main_lang)}, a informacja o ryzyku "
            f"w języku: {LANG_NAMES.get(risk_lang, risk_lang)}.",
            0.85,
            ev,
        )
    return passed(
        f"Informacja o ryzyku jest w tym samym języku co główny przekaz ({LANG_NAMES.get(main_lang, main_lang)}).",
        0.8,
        ev,
    )
