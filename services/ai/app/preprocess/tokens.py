"""Tokenisation, sentence splitting and a small stop-word language detector."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import fold

_WORD = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*")
_SENT_END = re.compile(r"(?<=[.!?…])[\"”')\]]*\s+(?=[\"„(\[]?[A-ZĄĆĘŁŃÓŚŹŻ0-9#@+])|\n+")
# Abbreviations after which a full stop does not end a sentence (folded form).
_ABBREV = re.compile(
    r"(?:\b(?:np|tzw|tj|m\.in|ok|art|ust|lit|pkt|nr|ul|sp|r|s|z o|o|dr|prof|mec|inz|wg|godz|tys|mln|mld|proc|pon|ww|a|b|c)\.)$"
)

STOPWORDS = {
    "pl": {
        "i",
        "w",
        "z",
        "na",
        "do",
        "nie",
        "to",
        "jest",
        "sie",
        "ze",
        "o",
        "jak",
        "ale",
        "po",
        "co",
        "tak",
        "za",
        "od",
        "czy",
        "tylko",
        "lub",
        "oraz",
        "przez",
        "dla",
        "przy",
        "sa",
        "jego",
        "jej",
        "ich",
        "ten",
        "ta",
        "te",
        "tym",
        "tego",
        "byc",
        "bedzie",
        "moze",
        "mozna",
        "juz",
        "bardzo",
        "wiecej",
        "kiedy",
        "ktory",
        "ktora",
        "ktore",
        "nas",
        "was",
        "nasz",
        "nasze",
        "twoj",
        "twoje",
        "ci",
        "u",
        "pod",
        "nad",
        "bez",
        "gdy",
        "bo",
        "aby",
        "zeby",
        "wszystko",
        "wiaze",
        "ryzykiem",
        "inwestycje",
    },
    "en": {
        "the",
        "and",
        "of",
        "to",
        "a",
        "in",
        "is",
        "that",
        "it",
        "for",
        "on",
        "with",
        "as",
        "are",
        "this",
        "be",
        "at",
        "or",
        "by",
        "from",
        "not",
        "your",
        "you",
        "we",
        "our",
        "can",
        "will",
        "have",
        "has",
        "an",
        "if",
        "all",
        "more",
        "when",
        "which",
        "their",
        "they",
        "was",
        "but",
        "may",
        "any",
        "money",
        "risk",
        "investors",
        "lose",
    },
    "de": {
        "der",
        "die",
        "das",
        "und",
        "ist",
        "nicht",
        "mit",
        "von",
        "zu",
        "den",
        "ein",
        "eine",
        "auf",
        "fur",
        "sich",
        "des",
        "dem",
        "im",
        "auch",
        "als",
        "an",
        "es",
        "bei",
        "sie",
        "wir",
        "ihr",
        "oder",
        "wird",
        "sind",
        "kann",
        "nur",
        "noch",
        "werden",
        "einer",
        "durch",
        "wie",
    },
}


@dataclass(frozen=True)
class Sentence:
    start: int
    end: int
    text: str
    folded: str


def tokenize(text: str) -> list[str]:
    """Folded word tokens."""
    return _WORD.findall(fold(text))


def split_sentences(text: str, folded: str | None = None) -> list[Sentence]:
    folded = folded if folded is not None else fold(text)
    cuts: list[tuple[int, int]] = []
    start = 0
    for m in _SENT_END.finditer(text):
        if "\n" not in m.group(0) and _ABBREV.search(folded[max(0, m.start() - 8) : m.start()]):
            continue
        cuts.append((start, m.start()))
        start = m.end()
    cuts.append((start, len(text)))
    out = []
    for a, b in cuts:
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if b > a:
            out.append(Sentence(a, b, text[a:b], folded[a:b]))
    return out


def detect_language(text: str, default: str = "pl") -> tuple[str, float]:
    """Return (language, confidence). Cyrillic text is reported as "uk/ru"."""
    if not text.strip():
        return default, 0.0
    letters = [c for c in text if c.isalpha()]
    if letters and sum("Ѐ" <= c <= "ӿ" for c in letters) / len(letters) > 0.5:
        return "ru", 0.9
    toks = tokenize(text)
    if not toks:
        return default, 0.0
    scores = {lang: sum(t in words for t in toks) for lang, words in STOPWORDS.items()}
    if re.search(r"[ąćęłńśźż]", text.lower()):
        scores["pl"] += 2
    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    if total == 0 or scores[best] < 2:
        return default, 0.2
    return best, round(scores[best] / total, 2)
