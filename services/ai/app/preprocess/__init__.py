"""Preprocessing: HTML stripping + visual signals, normalisation, hash, sentences, language."""

from __future__ import annotations

from dataclasses import dataclass, field

from .embed import Embedder, HashEmbedder, OllamaEmbedder, build_embedder, cosine
from .html import PageSignals, Segment, Style, contrast_ratio, extract_segments
from .normalize import content_hash, fold, normalize_line, normalize_text
from .tokens import Sentence, detect_language, split_sentences, tokenize

__all__ = [
    "Embedder",
    "HashEmbedder",
    "OllamaEmbedder",
    "Page",
    "PageSignals",
    "Segment",
    "Sentence",
    "Style",
    "build_embedder",
    "content_hash",
    "contrast_ratio",
    "cosine",
    "detect_language",
    "fold",
    "normalize_text",
    "preprocess",
    "split_sentences",
    "tokenize",
]


@dataclass
class Page:
    """Everything downstream code needs to know about one document."""

    text: str  # normalised text; all evidence spans index into this string
    folded: str  # same length, lower-case, no diacritics; lexicons match on this
    segments: list[Segment]
    signals: PageSignals
    sentences: list[Sentence]
    language: str
    language_confidence: float
    content_hash: str
    title: str = ""
    extra: dict = field(default_factory=dict)

    def segments_in(self, start: int, end: int) -> list[Segment]:
        return [s for s in self.segments if s.start < end and s.end > start]

    def sentence_at(self, pos: int) -> Sentence | None:
        for s in self.sentences:
            if s.start <= pos < s.end:
                return s
        return None


def preprocess(html: str, text: str, title: str = "", language: str | None = None) -> Page:
    """Build a `Page` from raw scraper output.

    HTML wins when it carries the content, because it also carries visual signals. A page
    whose HTML is only a script shell (visible text much longer than what the markup holds)
    falls back to the visible text; the visual rules then answer `unknown`.
    """
    plain = normalize_text(text or "")
    segments: list[Segment] = []
    signals = PageSignals(has_html=False)
    full = plain
    if html and html.strip():
        html_text, html_segments, html_signals = extract_segments(html)
        if html_text and len(html_text) >= 0.5 * len(plain):
            full, segments, signals = html_text, html_segments, html_signals
    title = normalize_line(title or "")
    if title and fold(title) not in fold(full[: len(title) + 400]):
        shift = len(title) + 1
        for seg in segments:
            seg.start += shift
            seg.end += shift
        if segments:
            segments.insert(0, Segment(title, 0, len(title), Style(role="title", bold=True)))
        full = f"{title}\n{full}" if full else title
    if not segments:
        pos = 0
        for line in full.split("\n"):
            role = "title" if title and pos == 0 and line == title else "body"
            segments.append(Segment(line, pos, pos + len(line), Style(role=role)))
            pos += len(line) + 1
    folded = fold(full)
    lang, conf = detect_language(full, default=language or "pl")
    if conf < 0.5 and language:
        lang = language
    return Page(
        text=full,
        folded=folded,
        segments=segments,
        signals=signals,
        sentences=split_sentences(full, folded),
        language=lang,
        language_confidence=conf,
        content_hash=content_hash(full),
        title=title,
    )
