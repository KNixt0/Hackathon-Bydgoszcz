"""HTML -> visible text segments with the visual signals the risk rules need.

No browser is involved: the walker resolves inline styles and simple `<style>` rules
(tag, .class, #id selectors) and inherits them down the tree. Whatever cannot be resolved
this way (external stylesheets, script-driven layout) stays `None`; the rules then report
`unknown` instead of guessing.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser

from .normalize import fold, normalize_line

DEFAULT_FONT_PX = 16.0

BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "body",
    "dd",
    "details",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "summary",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
    "title",
    "button",
    "label",
    "option",
}
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "object", "select"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
HEADING_SCALE = {"h1": 2.0, "h2": 1.5, "h3": 1.17, "h4": 1.0, "h5": 0.83, "h6": 0.67}

_LOW_VIS_CLASS = re.compile(r"foot-?note|przypis|disclaimer|legal|nota-?prawna|fine-?print|small-?print|zastrzezeni")
_COLLAPSE_CLASS = re.compile(r"collaps|accordion|spoiler|tooltip|modal|tab-pane|read-?more-content|hidden")
_COLLAPSE_OPEN = re.compile(r"\b(show|open|expanded|active)\b")
_LEGAL_HEADING = re.compile(r"^(legal|nota prawna|informacje prawne|zastrzezenia prawne|przypisy|disclaimer)\b")
EXPAND_LINK = re.compile(
    r"rozwin|czytaj (wiecej|dalej)|zobacz wiecej|pokaz wiecej|wiecej informacji|dowiedz sie wiecej"
    r"|read more|show more|szczegoly|kliknij,? aby"
)

NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "lightgray": (211, 211, 211),
    "lightgrey": (211, 211, 211),
    "darkgray": (169, 169, 169),
    "darkgrey": (169, 169, 169),
    "dimgray": (105, 105, 105),
    "gainsboro": (220, 220, 220),
    "whitesmoke": (245, 245, 245),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "navy": (0, 0, 128),
    "gold": (255, 215, 0),
}

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Style:
    font_px: float = DEFAULT_FONT_PX
    color: RGB | None = None
    background: RGB | None = None
    opacity: float = 1.0
    hidden: bool = False  # display:none / visibility:hidden / [hidden]
    collapsed: bool = False  # needs a click: <details>, accordion, collapsed block
    low_visibility: bool = False  # footnote / <small> / footer / "Legal" section
    truncated: bool = False  # ellipsis, line clamp, clipped overflow
    media_hidden: bool = False  # hidden by an @media rule (some screen sizes)
    bold: bool = False
    heading: int | None = None
    href: str | None = None
    role: str = "body"  # title | body
    styled: bool = False  # any explicit visual declaration reached this element


@dataclass
class Segment:
    text: str
    start: int
    end: int
    style: Style


@dataclass
class PageSignals:
    has_html: bool = False
    has_viewport_meta: bool = False
    media_queries: int = 0
    media_hidden_selectors: list[str] = field(default_factory=list)
    external_stylesheets: int = 0
    dominant_font_px: float | None = None
    expand_links: list[Segment] = field(default_factory=list)


@dataclass
class CssRule:
    tag: str | None
    ident: str | None
    classes: frozenset[str]
    decls: dict[str, str]
    specificity: int


def parse_color(value: str) -> RGB | None:
    value = value.strip().lower()
    if value in NAMED_COLORS:
        return NAMED_COLORS[value]
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})(?:[0-9a-f]{2})?", value)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    m = re.match(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)", value)
    if m:
        r, g, b = (min(255, int(x)) for x in m.groups())
        return (r, g, b)
    return None


def _first_color(value: str) -> RGB | None:
    for token in re.findall(r"#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|[a-zA-Z]+", value):
        color = parse_color(token)
        if color:
            return color
    return None


def parse_font_size(value: str, parent_px: float) -> float | None:
    value = value.strip().lower()
    keywords = {
        "xx-small": 9,
        "x-small": 10,
        "small": 13,
        "medium": 16,
        "large": 18,
        "x-large": 24,
        "xx-large": 32,
        "smaller": parent_px * 0.83,
        "larger": parent_px * 1.2,
    }
    if value in keywords:
        return float(keywords[value])
    m = re.fullmatch(r"([\d.]+)\s*(px|pt|em|rem|%)?", value)
    if not m:
        return None  # clamp(), calc(), vw ... cannot be resolved without a renderer
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    unit = m.group(2) or "px"
    return {
        "px": num,
        "pt": num * 4 / 3,
        "em": num * parent_px,
        "rem": num * DEFAULT_FONT_PX,
        "%": num / 100 * parent_px,
    }[unit]


def parse_declarations(css: str) -> dict[str, str]:
    decls: dict[str, str] = {}
    for part in css.split(";"):
        if ":" in part:
            prop, _, value = part.partition(":")
            decls[prop.strip().lower()] = value.replace("!important", "").strip()
    return decls


def _parse_selector(selector: str) -> tuple[str | None, str | None, frozenset[str]] | None:
    last = re.split(r"[\s>+~]+", selector.strip())[-1]
    last = re.sub(r"::?[\w-]+(\([^)]*\))?", "", last)
    m = re.fullmatch(r"([a-zA-Z][\w-]*|\*)?((?:[#.][\w-]+)*)", last)
    if not m or not last:
        return None
    tag = m.group(1).lower() if m.group(1) and m.group(1) != "*" else None
    ident = None
    classes = set()
    for kind, name in re.findall(r"([#.])([\w-]+)", m.group(2)):
        if kind == "#":
            ident = name
        else:
            classes.add(name)
    return tag, ident, frozenset(classes)


def parse_stylesheet(css: str, signals: PageSignals) -> list[CssRule]:
    """Tiny CSS reader: flat rules plus `@media` blocks (kept only as responsiveness hints)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[CssRule] = []
    pos = 0
    while True:
        m = re.search(r"@media[^{]*\{", css[pos:])
        if not m:
            break
        start = pos + m.start()
        depth, i = 1, pos + m.end()
        while i < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        signals.media_queries += 1
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css[pos + m.end() : i - 1]):
            decls = parse_declarations(body)
            if decls.get("display") == "none" or decls.get("visibility") == "hidden":
                signals.media_hidden_selectors.extend(s.strip() for s in selector.split(","))
        css = css[:start] + css[i:]
        pos = start
    css = re.sub(r"@[\w-]+[^{;]*;", "", css)
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        decls = parse_declarations(body)
        for single in selector.split(","):
            parsed = _parse_selector(single)
            if parsed and decls:
                tag, ident, classes = parsed
                spec = (100 if ident else 0) + 10 * len(classes) + (1 if tag else 0)
                rules.append(CssRule(tag, ident, classes, decls, spec))
    return rules


class _Walker(HTMLParser):
    def __init__(self, rules: list[CssRule], signals: PageSignals) -> None:
        super().__init__(convert_charrefs=True)
        self.rules = rules
        self.signals = signals
        self.stack: list[tuple[str, Style]] = [("#root", Style())]
        self.skip_depth = 0
        self.runs: list[tuple[str, Style, bool]] = []  # text, style, starts a new block
        self.block_break = True
        self.legal_section_depth: int | None = None

    # -- style resolution
    def _style_for(self, tag: str, attrs: dict[str, str], parent: Style) -> Style:
        classes = set(attrs.get("class", "").split())
        ident = attrs.get("id")
        decls: dict[str, str] = {}
        matched = [
            r
            for r in self.rules
            if (r.tag is None or r.tag == tag) and (r.ident is None or r.ident == ident) and r.classes <= classes
        ]
        for rule in sorted(matched, key=lambda r: r.specificity):
            decls.update(rule.decls)
        decls.update(parse_declarations(attrs.get("style", "")))
        if attrs.get("color") and "color" not in decls:  # legacy <font color>
            decls["color"] = attrs["color"]
        if attrs.get("bgcolor") and "background-color" not in decls:
            decls["background-color"] = attrs["bgcolor"]

        st = replace(parent, href=parent.href)
        changes: dict[str, object] = {}
        font_px = parent.font_px
        if tag in HEADING_SCALE:
            font_px = DEFAULT_FONT_PX * HEADING_SCALE[tag]
            changes.update(heading=int(tag[1]), bold=True)
        if tag in {"small", "sub", "sup"}:
            font_px = parent.font_px * 0.83
            changes["low_visibility"] = True
        if tag in {"b", "strong"}:
            changes["bold"] = True
        if "font-size" in decls:
            parsed = parse_font_size(decls["font-size"], parent.font_px)
            if parsed:
                font_px = parsed
                changes["styled"] = True
        elif "font" in decls:
            m = re.search(r"([\d.]+(?:px|pt|em|rem|%))", decls["font"])
            if m and (parsed := parse_font_size(m.group(1), parent.font_px)):
                font_px = parsed
                changes["styled"] = True
        changes["font_px"] = font_px
        if "color" in decls and (c := parse_color(decls["color"])):
            changes.update(color=c, styled=True)
        bg = decls.get("background-color") or decls.get("background")
        if bg and (c := _first_color(bg)):
            changes.update(background=c, styled=True)
        if "opacity" in decls:
            with contextlib.suppress(ValueError):
                changes.update(opacity=parent.opacity * float(decls["opacity"]), styled=True)
        weight = decls.get("font-weight", "")
        if weight in {"bold", "bolder"} or (weight.isdigit() and int(weight) >= 600):
            changes["bold"] = True

        hidden = (
            decls.get("display") == "none"
            or decls.get("visibility") in {"hidden", "collapse"}
            or "hidden" in attrs
            or attrs.get("aria-hidden") == "true"
            or (font_px is not None and font_px < 1)
        )
        zero_box = decls.get("max-height") in {"0", "0px"} or decls.get("height") in {"0", "0px"}
        if hidden:
            changes["hidden"] = True
        cls_id = fold(" ".join([*classes, ident or ""]))
        if tag == "details" and "open" not in attrs:
            changes["collapsed"] = True
        if zero_box or (_COLLAPSE_CLASS.search(cls_id) and not _COLLAPSE_OPEN.search(cls_id)):
            changes["collapsed"] = True
        if tag == "footer" or _LOW_VIS_CLASS.search(cls_id) or attrs.get("role") == "contentinfo":
            changes["low_visibility"] = True
        clip = decls.get("overflow") in {"hidden", "clip"} or decls.get("overflow-x") == "hidden"
        if (
            decls.get("text-overflow") == "ellipsis"
            or "-webkit-line-clamp" in decls
            or (decls.get("white-space") == "nowrap" and clip)
        ):
            changes["truncated"] = True
        for selector in self.signals.media_hidden_selectors:
            parsed = _parse_selector(selector)
            if parsed and (parsed[0] or parsed[1] or parsed[2]):
                m_tag, m_id, m_classes = parsed
                if (m_tag in (None, tag)) and (m_id in (None, ident)) and m_classes <= classes:
                    changes["media_hidden"] = True
        if tag == "a" and attrs.get("href"):
            changes["href"] = attrs["href"]
        if tag == "title":
            changes["role"] = "title"
        return replace(st, **changes)  # type: ignore[arg-type]

    # -- parser events
    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {k: (v or "") for k, v in attrs_list}
        if tag == "meta" and attrs.get("name", "").lower() == "viewport":
            self.signals.has_viewport_meta = True
        if tag == "link" and "stylesheet" in attrs.get("rel", "").lower():
            self.signals.external_stylesheets += 1
        if tag == "br":
            self.block_break = True
        if tag in VOID_TAGS:
            return
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        if tag in BLOCK_TAGS:
            self.block_break = True
        parent = self.stack[-1][1]
        style = self._style_for(tag, attrs, parent)
        if tag == "summary":  # the summary line of <details> is the visible part
            style = replace(style, collapsed=self._collapsed_above_details())
        self.stack.append((tag, style))

    def _collapsed_above_details(self) -> bool:
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == "details":
                return self.stack[i - 1][1].collapsed if i else False
        return False

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i][0] == tag:
                for closed, _ in self.stack[i:]:
                    if closed in SKIP_TAGS:
                        self.skip_depth = max(0, self.skip_depth - 1)
                if self.legal_section_depth is not None and i <= self.legal_section_depth:
                    self.legal_section_depth = None
                del self.stack[i:]
                break
        if tag in BLOCK_TAGS:
            self.block_break = True

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = normalize_line(data)
        if not text:
            return
        style = self.stack[-1][1]
        # A heading such as "Nota prawna" turns the rest of its container into a legal section.
        if style.heading and _LEGAL_HEADING.match(fold(text)):
            self.legal_section_depth = max(1, len(self.stack) - 2)
        elif self.legal_section_depth is not None and len(self.stack) - 1 >= self.legal_section_depth:
            style = replace(style, low_visibility=True)
        self.runs.append((text, style, self.block_break or not self.runs))
        self.block_break = False


def extract_segments(html: str) -> tuple[str, list[Segment], PageSignals]:
    """Return (normalised text, segments with offsets into it, page-level signals)."""
    signals = PageSignals(has_html=True)
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, flags=re.S | re.I))
    rules = parse_stylesheet(css, signals) if css else []
    walker = _Walker(rules, signals)
    walker.feed(html)
    walker.close()

    parts: list[str] = []
    segments: list[Segment] = []
    cursor = 0
    for text, style, new_block in walker.runs:
        if parts:
            sep = "\n" if new_block else " "
            parts.append(sep)
            cursor += 1
        segments.append(Segment(text, cursor, cursor + len(text), style))
        parts.append(text)
        cursor += len(text)
    full = "".join(parts)

    weights: dict[float, int] = {}
    for seg in segments:
        st = seg.style
        if st.hidden or st.collapsed or st.low_visibility or st.heading or st.role == "title":
            continue
        weights[round(st.font_px, 1)] = weights.get(round(st.font_px, 1), 0) + len(seg.text)
    if weights:
        signals.dominant_font_px = max(weights.items(), key=lambda kv: (kv[1], kv[0]))[0]
    signals.expand_links = [
        s for s in segments if len(s.text) <= 60 and EXPAND_LINK.search(fold(s.text)) and not s.style.hidden
    ]
    return full, segments, signals


def relative_luminance(rgb: RGB) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: RGB, bg: RGB) -> float:
    """WCAG 2.x contrast ratio, 1.0 (none) to 21.0 (black on white)."""
    hi, lo = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)
