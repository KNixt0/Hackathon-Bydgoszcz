"""Rules 4-8 and 13 decided from browser measurements (`document.visual`, contract v3).

The scraper collects *candidate* elements with a keyword list; here a candidate counts only
when it holds a sentence the text analysis recognises as risk information (or, for rule 13,
as a past-performance claim). Every decision quotes the measured numbers, and the evidence
carries the element's box on the archived screenshot of that viewport.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..context import Hit
from ..preprocess import fold
from ..schemas import BBox, BBoxIn, PerformanceBlockIn, RiskElementIn, ViewportIn
from . import settings
from .base import RuleOutcome, RuleView, failed, passed, rendered

VIEWPORT_PL = {"desktop": "desktop", "tablet": "tablet", "mobile": "telefon"}
PLACEMENT_PL = {
    "footer": "stopce strony",
    "footnote": "przypisie",
    "legal_section": "sekcji not prawnych",
    "body": "treści głównej",
}
INTERACTION_PL = {
    "details": "rozwinięcia zwiniętego elementu",
    "accordion": "rozwinięcia zwiniętej sekcji (akordeon)",
    "tooltip": "najechania na podpowiedź (tooltip)",
    "modal": "otwarcia okna (modal)",
    "link": "przejścia pod link na inną stronę",
}
_NON_WORD = re.compile(r"[^a-z0-9]+")


def _key(text: str) -> str:
    return _NON_WORD.sub(" ", fold(text)).strip()


def num(value: float, digits: int = 1) -> str:
    """Polish decimal comma."""
    return f"{value:.{digits}f}".replace(".", ",")


def px(value: float) -> str:
    return f"{value:.0f} px" if abs(value - round(value)) < 0.05 else f"{num(value)} px"


def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def gap_strength(value: float, threshold: float) -> float:
    """0.5 at the threshold, rising to 1.0 as the value falls to zero."""
    if threshold <= 0:
        return 0.5
    return 0.5 + 0.5 * max(0.0, min(1.0, (threshold - value) / threshold))


@dataclass
class RenderedRisk:
    el: RiskElementIn
    hits: list[Hit]

    @property
    def chars(self) -> int:
        return len(self.el.text)

    @property
    def open(self) -> bool:
        """Readable without any action: rendered, not hidden behind a click."""
        return self.el.visible and not self.el.requires_interaction


@dataclass
class RenderedHistory:
    block: PerformanceBlockIn
    hits: list[Hit]


def _hits_in(text: str, hits: list[Hit]) -> list[Hit]:
    key = _key(text)
    if not key:
        return []
    out = []
    for h in hits:
        hk = _key(h.sentence.text)
        if hk and (hk in key or (len(key) >= 20 and key in hk)):
            out.append(h)
    return out


def match_risk(v: RuleView) -> list[RenderedRisk]:
    out = []
    for el in v.visual.risk_elements:
        hits = _hits_in(el.text, v.risk)
        if hits:
            out.append(RenderedRisk(el, hits))
    return out


def match_history(v: RuleView) -> list[RenderedHistory]:
    out = []
    for block in v.visual.performance_blocks:
        hits = _hits_in(block.text, v.facts.historical)
        if hits:
            out.append(RenderedHistory(block, hits))
    return out


def _viewports(v: RuleView) -> dict[str, ViewportIn]:
    return {vp.name: vp for vp in v.visual.viewports}


def _screenshot_key(v: RuleView, viewport: str) -> str | None:
    vp = _viewports(v).get(viewport)
    if vp and vp.screenshot_key:
        return vp.screenshot_key
    shots = v.ctx.document.archive.screenshots
    key = getattr(shots, viewport, None) if shots else None
    if key:
        return key
    return v.ctx.document.archive.screenshot_key if viewport == "desktop" else None


def _bbox_for(item: RenderedRisk | RenderedHistory, viewport: str | None) -> BBoxIn | None:
    measured = item.el if isinstance(item, RenderedRisk) else item.block
    if viewport and viewport in measured.by_viewport and measured.by_viewport[viewport].bbox:
        return measured.by_viewport[viewport].bbox
    return measured.bbox


def evidence(v: RuleView, item: RenderedRisk | RenderedHistory, label: str, viewport: str | None = None) -> list[str]:
    """Quote of the matched sentence, placed on the screenshot of `viewport` (default: desktop)."""
    hit = item.hits[0]
    box = _bbox_for(item, viewport or "desktop")
    if box is None or box.w <= 0 or box.h <= 0:
        return [v.ctx.evidence.quote(hit.sentence.start, hit.sentence.end, label)]
    bbox = BBox(viewport=box.viewport, x=box.x, y=box.y, w=box.w, h=box.h)
    return [
        v.ctx.evidence.visual_quote(hit.sentence.start, hit.sentence.end, label, bbox, _screenshot_key(v, box.viewport))
    ]


def main_warning(items: list[RenderedRisk]) -> RenderedRisk:
    """The warning a reader has the best chance to read: open ones first, then the largest font."""
    pool = [r for r in items if r.open] or items
    return max(pool, key=lambda r: (r.el.font_px, r.chars))


def _desktop_size(v: RuleView) -> str:
    vp = _viewports(v).get("desktop")
    return f"{vp.width}×{vp.height}" if vp else "desktop"


# ------------------------------------------------------------------------------- rules


def font_size(v: RuleView, items: list[RenderedRisk]) -> RuleOutcome:
    main = main_warning(items)
    dominant = v.visual.dominant_font_px
    size = main.el.font_px
    ratio = size / dominant if dominant else 1.0
    limits = f"progi: {num(settings.RENDERED_FONT_RATIO_MIN)}× i {px(settings.RENDERED_FONT_MIN_PX)}"
    hidden = "" if main.open else " Ostrzeżenie nie jest widoczne bez interakcji; zmierzono jego styl po rozwinięciu."
    detail = (
        f"Tekst główny {px(dominant)}, ostrzeżenie {px(size)} ({num(ratio, 2)}×; {limits}; "
        f"pomiar w przeglądarce, {_desktop_size(v)})."
    )
    ev = evidence(v, main, "Ostrzeżenie o ryzyku (pomiar czcionki)")
    if ratio < settings.RENDERED_FONT_RATIO_MIN or size < settings.RENDERED_FONT_MIN_PX:
        strength = max(
            gap_strength(ratio, settings.RENDERED_FONT_RATIO_MIN),
            gap_strength(size, settings.RENDERED_FONT_MIN_PX) if size < settings.RENDERED_FONT_MIN_PX else 0.0,
        )
        return rendered(
            failed(f"{detail} Ostrzeżenie jest wyraźnie mniejsze od głównego przekazu.{hidden}", 0.95, ev), strength
        )
    return rendered(passed(f"{detail}{hidden}", 0.9, ev), 0.0)


def contrast(v: RuleView, items: list[RenderedRisk]) -> RuleOutcome:
    main = main_warning(items)
    el = main.el
    ev = evidence(v, main, "Ostrzeżenie o ryzyku (pomiar kontrastu)")
    colours = f"tekst {el.color} na tle {el.background}" if el.color and el.background else "kolory zmierzone"
    if not el.visible and not el.requires_interaction:
        return rendered(
            failed(
                "Ostrzeżenie o ryzyku jest w kodzie strony, ale przeglądarka go nie wyświetla (ukryte stylami).",
                0.9,
                ev,
            ),
            1.0,
        )
    if el.occluded:
        return rendered(
            failed(
                "Ostrzeżenie o ryzyku jest przesłonięte przez inny element strony "
                "(w miejscu tekstu przeglądarka zwraca inny element).",
                0.9,
                ev,
            ),
            0.9,
        )
    cut = [VIEWPORT_PL.get(n, n) for n, m in main.el.by_viewport.items() if m.clipped]
    if cut:
        return rendered(
            failed(
                f"Tekst ostrzeżenia jest ucinany (overflow / wielokropek), czyli częściowo zakryty: {', '.join(cut)}.",
                0.9,
                evidence(
                    v, main, "Ucięte ostrzeżenie o ryzyku", next(n for n, m in main.el.by_viewport.items() if m.clipped)
                ),
            ),
            0.5 + 0.5 * len(cut) / max(1, len(main.el.by_viewport)),
        )
    if el.opacity < settings.RENDERED_OPACITY_MIN:
        return rendered(
            failed(
                f"Ostrzeżenie o ryzyku ma krycie {pct(el.opacity)} (minimum {pct(settings.RENDERED_OPACITY_MIN)}), "
                "co obniża czytelność.",
                0.9,
                ev,
            ),
            gap_strength(el.opacity, settings.RENDERED_OPACITY_MIN),
        )
    if el.contrast < settings.RENDERED_CONTRAST_MIN:
        return rendered(
            failed(
                f"Kontrast ostrzeżenia {num(el.contrast)}:1 ({colours}); minimum WCAG AA "
                f"{num(settings.RENDERED_CONTRAST_MIN)}:1.",
                0.95,
                ev,
            ),
            gap_strength(el.contrast - 1.0, settings.RENDERED_CONTRAST_MIN - 1.0),
        )
    return rendered(
        passed(
            f"Kontrast ostrzeżenia {num(el.contrast)}:1 ({colours}); nie jest przesłonięte, krycie {pct(el.opacity)}.",
            0.9,
            ev,
        ),
        0.0,
    )


def concealment(v: RuleView, items: list[RenderedRisk]) -> RuleOutcome:
    faint = [r for r in items if r.open and r.el.contrast < settings.CONCEALING_CONTRAST_MAX]
    body = [r for r in items if r.el.placement == "body" and r.open and not r.el.occluded and r not in faint]
    tucked = [r for r in items if r.el.placement != "body"]
    body_chars = sum(r.chars for r in body)
    tucked_chars = sum(r.chars for r in tucked)
    total = sum(r.chars for r in items)
    faint_chars = sum(r.chars for r in faint if r not in tucked)
    if faint_chars and faint_chars >= body_chars and faint_chars >= tucked_chars:
        worst = min(faint, key=lambda r: r.el.contrast)
        return rendered(
            failed(
                f"{faint_chars} z {total} znaków informacji o ryzyku ma kontrast {num(worst.el.contrast)}:1, poniżej "
                f"{num(settings.CONCEALING_CONTRAST_MAX)}:1 (minimum nawet dla dużego tekstu), więc ostrzeżenie zlewa się "
                "z tłem i jest w praktyce zaciemnione.",
                0.85,
                evidence(v, worst, "Ostrzeżenie zlewające się z tłem"),
            ),
            gap_strength(worst.el.contrast - 1.0, settings.CONCEALING_CONTRAST_MAX - 1.0),
        )
    if tucked and tucked_chars >= body_chars:
        worst = max(tucked, key=lambda r: r.chars)
        where = PLACEMENT_PL[worst.el.placement]
        share = tucked_chars / total if total else 1.0
        return rendered(
            failed(
                f"{tucked_chars} z {total} znaków informacji o ryzyku ({pct(share)}) znajduje się w {where}; "
                f"w widocznej treści głównej jest {body_chars} znaków.",
                0.9,
                evidence(v, worst, "Informacja o ryzyku poza treścią główną"),
            ),
            0.5 + 0.5 * share,
        )
    if not body:
        hidden = items[0]
        return rendered(
            failed(
                "Żadna informacja o ryzyku nie jest widoczna w treści głównej bez interakcji "
                "(jest ukryta, przesłonięta lub wymaga kliknięcia).",
                0.85,
                evidence(v, hidden, "Informacja o ryzyku"),
            ),
            0.8,
        )
    best = max(body, key=lambda r: r.chars)
    return rendered(
        passed(
            f"{body_chars} z {total} znaków informacji o ryzyku jest w widocznej treści głównej, "
            "nie w przypisie ani stopce.",
            0.9,
            evidence(v, best, "Informacja o ryzyku w treści głównej"),
        ),
        0.0,
    )


def one_click(v: RuleView, items: list[RenderedRisk]) -> RuleOutcome:
    needs = [r for r in items if r.el.requires_interaction]
    open_ = [r for r in items if r.open]
    need_chars = sum(r.chars for r in needs)
    open_chars = sum(r.chars for r in open_)
    total = sum(r.chars for r in items)
    if needs and need_chars >= open_chars:
        worst = max(needs, key=lambda r: r.chars)
        how = INTERACTION_PL.get(worst.el.requires_interaction or "", "interakcji")
        control = f" („{worst.el.control_text}”)" if worst.el.control_text else ""
        share = need_chars / total if total else 1.0
        return rendered(
            failed(
                f"{need_chars} z {total} znaków informacji o ryzyku ({pct(share)}) jest widoczne dopiero po "
                f"wykonaniu akcji: {how}{control}; bez interakcji widać {open_chars} znaków.",
                0.95,
                evidence(v, worst, "Informacja o ryzyku widoczna dopiero po interakcji"),
            ),
            0.5 + 0.5 * share,
        )
    best = max(open_, key=lambda r: r.chars) if open_ else items[0]
    return rendered(
        passed(
            f"{open_chars} z {total} znaków informacji o ryzyku jest widoczne od razu, bez rozwijania i bez "
            "przechodzenia na inną warstwę.",
            0.9,
            evidence(v, best, "Informacja o ryzyku widoczna bez interakcji"),
        ),
        0.0,
    )


def responsiveness(v: RuleView, items: list[RenderedRisk]) -> RuleOutcome:
    pool = [r for r in items if r.open] or items
    problems: list[tuple[str, str, RenderedRisk | None]] = []
    checked = []
    for vp in v.visual.viewports:
        name = VIEWPORT_PL.get(vp.name, vp.name)
        where = f"{name} {vp.width}×{vp.height}"
        checked.append(where)
        clipped_keys = [_key(t) for t in vp.clipped_texts]
        smallest: tuple[float, RenderedRisk] | None = None
        for r in pool:
            m = r.el.by_viewport.get(vp.name)
            if m is None:
                continue
            if r.open and not m.visible:
                problems.append((vp.name, f"{where}: ostrzeżenie nie jest wyświetlane", r))
                continue
            key = _key(r.el.text)
            if m.clipped or any(k and (k in key or key in k) for k in clipped_keys):
                problems.append((vp.name, f"{where}: tekst ostrzeżenia jest ucinany", r))
            if m.font_px is not None and (smallest is None or m.font_px < smallest[0]):
                smallest = (m.font_px, r)
        if smallest is None and vp.min_risk_font_px is not None and not any(r.el.by_viewport for r in pool):
            smallest = (vp.min_risk_font_px, None)  # type: ignore[assignment]
        if smallest is not None and smallest[0] < settings.RESPONSIVE_FONT_MIN_PX:
            problems.append(
                (
                    vp.name,
                    f"{where}: ostrzeżenie ma {px(smallest[0])} (próg {px(settings.RESPONSIVE_FONT_MIN_PX)})",
                    smallest[1],
                )
            )
        if vp.overflow_x:
            wide = f" ({vp.scroll_width} px szerokości)" if vp.scroll_width else ""
            problems.append((vp.name, f"{where}: strona wychodzi poza ekran w poziomie{wide}", None))
    if problems:
        order = {"mobile": 0, "tablet": 1, "desktop": 2}
        worst_vp, _, worst = min(problems, key=lambda p: (order.get(p[0], 3), p[2] is None))
        target = worst or main_warning(items)
        texts = "; ".join(dict.fromkeys(p[1] for p in problems))
        return rendered(
            failed(
                f"Pomiar na {len(checked)} rozmiarach ekranu: {texts}.",
                0.9,
                evidence(v, target, "Ostrzeżenie o ryzyku na małym ekranie", worst_vp),
            ),
            min(1.0, 0.5 + 0.15 * len(problems)),
        )
    sizes = []
    for vp in v.visual.viewports:
        fonts = [r.el.by_viewport[vp.name].font_px for r in pool if vp.name in r.el.by_viewport]
        fonts = [f for f in fonts if f is not None]
        if fonts:
            sizes.append(f"{VIEWPORT_PL.get(vp.name, vp.name)} {px(min(fonts))}")
    detail = f" (najmniejsza czcionka ostrzeżenia: {', '.join(sizes)})" if sizes else ""
    return rendered(
        passed(
            f"Na {len(checked)} rozmiarach ekranu ({', '.join(checked)}) ostrzeżenie jest wyświetlane w całości, "
            f"bez ucinania i przewijania w poziomie{detail}.",
            0.9,
            evidence(v, main_warning(items), "Ostrzeżenie o ryzyku"),
        ),
        0.0,
    )


def history_dominance(v: RuleView, items: list[RenderedHistory]) -> RuleOutcome:
    dominant = v.visual.dominant_font_px
    largest = v.visual.max_font_px or dominant
    worst: tuple[float, str, RenderedHistory, str | None] | None = None
    for item in items:
        b = item.block
        reasons = []
        strength = 0.0
        viewport = None
        is_largest = b.font_px >= largest - settings.HISTORY_LARGEST_TOLERANCE_PX
        if is_largest and b.font_px >= dominant * settings.HISTORY_FONT_RATIO:
            reasons.append(
                f"jest największym tekstem na stronie: {px(b.font_px)} wobec {px(dominant)} tekstu głównego "
                f"({num(b.font_px / dominant, 2)}×)"
            )
            strength = max(strength, min(1.0, 0.5 + 0.25 * (b.font_px / dominant - 1)))
        shares = {
            "desktop": b.area_share,
            **{n: m.area_share for n, m in b.by_viewport.items() if m.area_share is not None},
        }
        vp_name, share = max(shares.items(), key=lambda kv: kv[1])
        if share >= settings.HISTORY_AREA_SHARE_MAX:
            reasons.append(
                f"zajmuje {pct(share)} pierwszego ekranu ({VIEWPORT_PL.get(vp_name, vp_name)}; "
                f"próg {pct(settings.HISTORY_AREA_SHARE_MAX)})"
            )
            strength = max(strength, min(1.0, 0.5 + share))
            viewport = vp_name
        if reasons and (worst is None or strength > worst[0]):
            worst = (strength, " i ".join(reasons), item, viewport)
    if worst:
        strength, why, item, viewport = worst
        return rendered(
            failed(
                f"Wynik historyczny „{item.block.text[:90]}” {why}.",
                0.9,
                evidence(v, item, "Wyeksponowany wynik historyczny", viewport),
            ),
            strength,
        )
    top = max(items, key=lambda i: i.block.font_px)
    return rendered(
        passed(
            f"Wyniki historyczne nie dominują: największy blok ma {px(top.block.font_px)} przy tekście głównym "
            f"{px(dominant)} i najwyższym tekście strony {px(largest)}, zajmuje {pct(top.block.area_share)} "
            "pierwszego ekranu.",
            0.85,
            evidence(v, top, "Prezentacja wyników historycznych"),
        ),
        0.0,
    )
