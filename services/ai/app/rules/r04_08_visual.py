"""Rules 4-8: how the risk information is displayed.

These rules read the visual signals extracted from the HTML. Without HTML, or when a signal
cannot be resolved without rendering the page, the answer is `unknown`.
"""

from __future__ import annotations

import re

from ..preprocess import contrast_ratio
from . import settings
from .base import RuleOutcome, RuleView, failed, not_applicable, passed, rule, unknown

NO_RISK = "Materiał nie zawiera informacji o ryzyku, więc nie ma czego ocenić (por. reguła 3)."
NO_HTML = "Brak kodu HTML materiału; ocena wymaga analizy wizualnej (zrzut ekranu lub render strony)."
_FOOTNOTE_TEXT = re.compile(r"^(?:\*+|\(?\d\)|\[\d\]|[¹²³])\s?")
_LEGAL_LINE = re.compile(
    r"(?:^|\n)(?:legal|nota prawna|informacje prawne|zastrzezenia prawne|przypisy|disclaimer)\s*:?\s*(?:\n|$)"
)


@rule("4", "Rozmiar czcionki ryzyka", "art. 44 ust. 2 lit. c rozporządzenia del. 2017/565")
def risk_font_size(v: RuleView) -> RuleOutcome:
    if not v.risk:
        return not_applicable(NO_RISK)
    if not v.has_html or not v.signals.dominant_font_px:
        return unknown(NO_HTML)
    hit = v.main_risk
    segs = v.segs(hit)
    risk_px = min(s.style.font_px for s in segs)
    dominant = v.signals.dominant_font_px
    ratio = risk_px / dominant
    detail = f"Informacja o ryzyku: {risk_px:.0f} px, przeważająca czcionka materiału: {dominant:.0f} px"
    if ratio < settings.FONT_RATIO_MIN:
        return failed(f"{detail}. Ostrzeżenie jest wyraźnie mniejsze od głównego przekazu.", 0.9, v.risk_quote(hit))
    explicit = any(s.style.styled for s in segs) or not v.signals.external_stylesheets
    if not explicit:
        return unknown(
            "Rozmiar czcionki zależy od zewnętrznego arkusza stylów, którego nie da się ocenić bez renderowania strony."
        )
    return passed(f"{detail}.", 0.85, v.risk_quote(hit))


@rule("5", "Ekspozycja i kontrast ryzyka", "art. 44 ust. 2 lit. c i e rozporządzenia del. 2017/565")
def risk_contrast(v: RuleView) -> RuleOutcome:
    if not v.risk:
        return not_applicable(NO_RISK)
    if not v.has_html:
        return unknown(NO_HTML)
    hit = v.main_risk
    segs = v.segs(hit)
    ev = v.risk_quote(hit)
    if any(s.style.truncated for s in segs):
        return failed(
            "Tekst informacji o ryzyku jest przycinany (ucięcie lub wielokropek), czyli częściowo przesłonięty.",
            0.8,
            ev,
        )
    opacity = min(s.style.opacity for s in segs)
    if opacity < settings.OPACITY_MIN:
        return failed(
            f"Informacja o ryzyku jest wyświetlana z przezroczystością {opacity:.0%}, co obniża czytelność.", 0.8, ev
        )
    fg = next((s.style.color for s in segs if s.style.color), None)
    bg = next((s.style.background for s in segs if s.style.background), None)
    if v.signals.external_stylesheets and (fg is None or bg is None):
        return unknown("Kolory zależą od zewnętrznego arkusza stylów; kontrast wymaga oceny na zrzucie ekranu.")
    ratio = contrast_ratio(fg or (0, 0, 0), bg or (255, 255, 255))
    if ratio < settings.CONTRAST_MIN:
        return failed(
            f"Kontrast tekstu ostrzeżenia względem tła wynosi {ratio:.1f}:1 "
            f"(minimum czytelności {settings.CONTRAST_MIN}:1).",
            0.85,
            ev,
        )
    if fg is None and bg is None:
        return passed(
            "Informacja o ryzyku nie ma odrębnej stylizacji kolorystycznej; jest wyświetlana tak jak główny tekst.",
            0.7,
            ev,
        )
    return passed(f"Kontrast tekstu ostrzeżenia względem tła wynosi {ratio:.1f}:1.", 0.85, ev)


@rule("6", "Zakrywanie / ukrywanie ryzyka", "art. 44 ust. 2 lit. e rozporządzenia del. 2017/565")
def risk_concealment(v: RuleView) -> RuleOutcome:
    if not v.risk:
        return not_applicable(NO_RISK)
    if v.has_html:
        tucked = [h for h in v.risk if v.is_low_visibility(h)]
        prominent = [h for h in v.risk if not v.is_low_visibility(h) and not v.is_concealed(h)]
        if tucked and v.chars(tucked) >= v.chars(prominent):
            hit = max(tucked, key=lambda h: h.end - h.start)
            return failed(
                "Przeważająca część informacji o ryzyku znajduje się w przypisie, stopce lub sekcji "
                "typu „Nota prawna”, czyli w miejscu o niskiej widoczności.",
                0.85,
                v.risk_quote(hit),
            )
        if not prominent:
            return failed(
                "Informacja o ryzyku nie występuje w głównej, widocznej części materiału.", 0.75, v.risk_quote()
            )
        return passed(
            "Informacja o ryzyku znajduje się w głównej części materiału, nie w przypisie ani stopce.",
            0.8,
            v.risk_quote(),
        )
    # Text only: a footnote marker or a preceding "Nota prawna" line is still recognisable.
    folded = v.page.folded
    tucked = [h for h in v.risk if _FOOTNOTE_TEXT.match(h.sentence.text) or _LEGAL_LINE.search(folded[: h.start])]
    if tucked and len(tucked) == len(v.risk):
        return failed(
            "Informacja o ryzyku ma postać przypisu lub znajduje się w sekcji not prawnych "
            "(ocena na podstawie samego tekstu).",
            0.55,
            v.risk_quote(tucked[0]),
        )
    return unknown(NO_HTML)


@rule("7", "Dostępność za 1 kliknięciem", "art. 44 ust. 2 lit. b i e rozporządzenia del. 2017/565")
def risk_one_click(v: RuleView) -> RuleOutcome:
    refs = v.facts.risk_refs
    if not v.risk:
        if refs:
            ev = [v.ctx.quote(refs[0], label="Odesłanie do informacji o ryzyku")]
            return failed(
                "Materiał jedynie odsyła do informacji o ryzyku (link lub inna warstwa); samej "
                "informacji w nim nie ma.",
                0.75 if v.has_html else 0.6,
                ev,
            )
        return not_applicable(NO_RISK)
    if not v.has_html:
        return unknown(NO_HTML)
    concealed = [h for h in v.risk if v.is_concealed(h)]
    if concealed and v.chars(concealed) >= v.chars(v.risk_open):
        hit = max(concealed, key=lambda h: h.end - h.start)
        ev = v.risk_quote(hit, "Informacja o ryzyku widoczna dopiero po rozwinięciu")
        for link in v.signals.expand_links[:1]:
            ev.append(v.ctx.evidence.quote(link.start, link.end, "Element rozwijający treść"))
        return failed(
            "Przeważająca część informacji o ryzyku jest dostępna dopiero po rozwinięciu elementu lub "
            "kliknięciu (inna warstwa strony).",
            0.9,
            ev,
        )
    return passed(
        "Informacja o ryzyku jest widoczna bez rozwijania i bez przechodzenia na inną warstwę.", 0.85, v.risk_quote()
    )


@rule("8", "Responsywność (różne urządzenia)", "art. 44 ust. 2 lit. g rozporządzenia del. 2017/565")
def risk_responsiveness(v: RuleView) -> RuleOutcome:
    if not v.risk:
        return not_applicable(NO_RISK)
    if not v.has_html:
        return unknown(NO_HTML)
    hit = v.main_risk
    segs = v.segs(hit)
    ev = v.risk_quote(hit)
    if any(s.style.media_hidden for s in segs):
        return failed("Reguła @media ukrywa informację o ryzyku na części rozmiarów ekranu.", 0.85, ev)
    if any(s.style.truncated for s in segs):
        return failed("Informacja o ryzyku jest ucinana, gdy nie mieści się na ekranie.", 0.75, ev)
    px = min(s.style.font_px for s in segs)
    if px < settings.MOBILE_MIN_FONT_PX:
        return failed(f"Informacja o ryzyku ma {px:.0f} px, czyli poniżej progu czytelności na telefonie.", 0.75, ev)
    if v.signals.has_viewport_meta and not v.signals.external_stylesheets:
        return passed(
            "Strona deklaruje widok mobilny, a informacja o ryzyku nie jest ukrywana, ucinana ani "
            "pomniejszana poniżej czytelności (analiza kodu, bez renderowania).",
            0.6,
            ev,
        )
    return unknown(
        "Ocena wymaga wyświetlenia materiału na ekranach o różnych wielkościach (desktop, tablet, "
        "telefon); sam kod nie wystarcza."
    )
