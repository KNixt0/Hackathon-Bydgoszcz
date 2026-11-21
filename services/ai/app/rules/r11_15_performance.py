"""Rules 11-15: comparisons, historical performance and forecasts."""

from __future__ import annotations

import re

from .. import lexicon as lx
from . import settings
from .base import RuleOutcome, RuleView, failed, not_applicable, passed, rule, unknown

NO_HISTORY = "Materiał nie prezentuje wyników historycznych."
_YEAR = re.compile(r"\b20[012]\d\b")
_YEAR_RANGE = re.compile(r"\b(20[012]\d)\s?[-–/]\s?(20[012]\d)\b")
_FEES_CONTEXT = re.compile(r"wynik|zwrot|stop|uwzgledn|pomniejsz|netto|brutto|wplyw|obniz|przed |po ")


def _history_text(v: RuleView) -> str:
    return " ".join(h.sentence.folded for h in v.facts.historical)


def _history_ev(v: RuleView) -> list[str]:
    return [v.ctx.quote(v.facts.historical[0], label="Prezentacja wyników historycznych")]


@rule("11", "Porównania produktów / usług", "art. 44 ust. 3 rozporządzenia del. 2017/565")
def comparisons(v: RuleView) -> RuleOutcome:
    hits = v.facts.comparisons
    if not hits:
        return not_applicable("Nie wykryto porównań produktów ani usług.")
    ev = [v.ctx.quote(hits[0], label="Porównanie produktów / usług")]
    folded = v.page.folded
    missing = []
    if not lx.SOURCE_GIVEN.search(folded):
        missing.append("źródła informacji")
    if not lx.ASSUMPTIONS_GIVEN.search(folded):
        missing.append("przyjętych założeń")
    if missing:
        return failed(f"Wykryto porównanie, ale nie podano: {' ani '.join(missing)}.", 0.7, ev)
    return passed("Wykryto porównanie; podano źródło informacji i przyjęte założenia.", 0.7, ev)


@rule("12a", "Wyniki historyczne: okres i zakres", "art. 44 ust. 4 rozporządzenia del. 2017/565")
def history_period(v: RuleView) -> RuleOutcome:
    if not v.facts.historical:
        return not_applicable(NO_HISTORY)
    hist = _history_text(v)
    years = {int(y) for y in _YEAR.findall(hist)}
    spans = [int(b) - int(a) + 1 for a, b in _YEAR_RANGE.findall(hist)]  # "2021–2025" covers 5 years
    five_years = bool(lx.FIVE_YEARS.search(hist)) or len(years) >= 5 or any(n >= 5 for n in spans)
    missing = []
    if not five_years:
        missing.append("wyniki nie obejmują ostatnich 5 lat (ani całego okresu oferowania)")
    if lx.SUB_YEAR_PERIOD.search(hist):
        missing.append("wyniki nie są oparte o pełne okresy 12-miesięczne")
    if not lx.PERIOD_GIVEN.search(hist):
        missing.append("nie wskazano okresu referencyjnego")
    if not lx.SOURCE_GIVEN.search(v.page.folded):
        missing.append("nie wskazano źródła danych")
    if missing:
        return failed(
            "Niekompletna prezentacja wyników historycznych: " + "; ".join(missing) + ".", 0.8, _history_ev(v)
        )
    return passed(
        "Wyniki historyczne obejmują 5 lat w pełnych okresach 12-miesięcznych, ze wskazaniem okresu "
        "referencyjnego i źródła.",
        0.75,
        _history_ev(v),
    )


@rule("12b", "Wyniki historyczne: warunki i waluta", "art. 44 ust. 4 rozporządzenia del. 2017/565")
def history_conditions(v: RuleView) -> RuleOutcome:
    if not v.facts.historical:
        return not_applicable(NO_HISTORY)
    folded = v.page.folded
    fees = any(lx.FEES_EFFECT.search(s.folded) and _FEES_CONTEXT.search(s.folded) for s in v.page.sentences)
    fx_needed = bool(lx.FX_EXPOSURE.search(folded))
    missing = []
    if not fees:
        missing.append("nie wskazano wpływu prowizji, opłat i innych obciążeń na wyniki")
    if fx_needed and not lx.FX_WARNING.search(folded):
        missing.append("brak ostrzeżenia o wpływie zmian kursów walutowych (wyniki w walucie obcej)")
    if missing:
        return failed("; ".join(missing).capitalize() + ".", 0.75, _history_ev(v))
    fx_note = "zawarto ostrzeżenie o kursach walut" if fx_needed else "wyniki nie odnoszą się do waluty obcej"
    return passed(f"Wskazano wpływ opłat i prowizji na wyniki; {fx_note}.", 0.7, _history_ev(v))


@rule("13", "Dominacja wyników historycznych", "art. 44 ust. 4 lit. a rozporządzenia del. 2017/565")
def history_dominance(v: RuleView) -> RuleOutcome:
    hist = v.facts.historical
    if not hist:
        return not_applicable(NO_HISTORY)
    ev = _history_ev(v)
    dominant = v.signals.dominant_font_px
    for h in hist:
        for seg in v.page.segments_in(h.start, h.end):
            st = seg.style
            if st.role == "title" or (st.heading and st.heading <= 2):
                return failed(
                    "Wyniki historyczne znajdują się w tytule lub głównym nagłówku, czyli są najbardziej "
                    "wyeksponowanym elementem.",
                    0.8 if v.has_html else 0.6,
                    [v.ctx.quote(h, label="Wynik historyczny w nagłówku")],
                )
            if v.has_html and dominant and st.font_px >= dominant * settings.PROMINENT_FONT_RATIO:
                return failed(
                    f"Wyniki historyczne są wyświetlane większą czcionką ({st.font_px:.0f} px) niż "
                    f"główny tekst ({dominant:.0f} px).",
                    0.8,
                    [v.ctx.quote(h, label="Wyeksponowany wynik historyczny")],
                )
    if not v.has_html:
        sentences = v.page.sentences
        lead = sentences[1] if v.page.title and len(sentences) > 1 else sentences[0]
        if hist[0].sentence is lead:
            return failed("Materiał otwiera się od wyników historycznych (ocena na podstawie samego tekstu).", 0.55, ev)
        return unknown("Brak kodu HTML; ocena ekspozycji wyników historycznych wymaga analizy wizualnej.")
    return passed("Wyniki historyczne nie są wyeksponowane ponad pozostałe informacje.", 0.7, ev)


@rule("14", "Ostrzeżenie przy wynikach historycznych", "art. 44 ust. 4 lit. d rozporządzenia del. 2017/565")
def history_warning(v: RuleView) -> RuleOutcome:
    if not v.facts.historical:
        return not_applicable(NO_HISTORY)
    m = lx.HIST_WARNING.search(v.page.folded)
    if m:
        return passed(
            "Zawarto zastrzeżenie, że wyniki historyczne nie stanowią wiarygodnego wskaźnika przyszłych wyników.",
            0.9,
            [v.ctx.quote_sentence(m.start(), "Zastrzeżenie o wynikach historycznych")],
        )
    return failed(
        "Brak wyraźnego zastrzeżenia, że wyniki historyczne nie stanowią wiarygodnego wskaźnika przyszłych wyników.",
        0.85,
        _history_ev(v),
    )


@rule("15", "Prognozy przyszłych wyników", "art. 44 ust. 6 rozporządzenia del. 2017/565")
def forecasts(v: RuleView) -> RuleOutcome:
    hits = v.facts.forecasts
    if not hits:
        return not_applicable("Nie wykryto prognoz przyszłych wyników.")
    ev = [v.ctx.quote(hits[0], label="Prognoza przyszłych wyników")]
    m = lx.FORECAST_WARNING.search(v.page.folded)
    if m:
        ev.append(v.ctx.quote_sentence(m.start(), "Zastrzeżenie o prognozach"))
        return passed(
            "Wykryto prognozę przyszłych wyników wraz z ostrzeżeniem, że nie jest ona wiarygodnym "
            "wskaźnikiem przyszłych wyników.",
            0.8,
            ev,
        )
    return failed(
        "Wykryto prognozę przyszłych wyników bez ostrzeżenia, że prognoza nie jest wiarygodnym "
        "wskaźnikiem przyszłych wyników.",
        0.75,
        ev,
    )
