"""Fuzzy matching of entity names against register entries.

Names are compared after folding, removing punctuation and stripping legal forms
("S.A.", "sp. z o.o.", "Ltd", "GmbH" ...). A second, looser key (`core`) also drops generic
sector words ("dom maklerski", "bank", "securities" ...), which catches brand-only mentions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from ..preprocess.normalize import fold

LEGAL_SEQUENCES = [
    ("spolka", "z", "ograniczona", "odpowiedzialnoscia"), ("spolka", "akcyjna"),
    ("spolka", "komandytowa"), ("spolka", "jawna"), ("sp", "z", "o", "o"), ("sp", "z", "oo"),
    ("sp", "zoo"), ("sp", "k"), ("sp", "j"), ("s", "a"), ("a", "s"), ("s", "r", "o"),
    ("b", "v"), ("n", "v"), ("oddzial", "w", "polsce"),
]
LEGAL_TOKENS = {
    "sa", "spzoo", "zoo", "spk", "spj", "ska", "ltd", "limited", "llc", "llp", "lp", "plc", "inc",
    "corp", "corporation", "gmbh", "ag", "kg", "ug", "se", "sarl", "sas", "spa", "srl", "sau",
    "bv", "nv", "as", "sro", "oy", "oyj", "ab", "asa", "ou", "uab", "sia", "doo", "ead", "kft",
    "zrt", "cy", "co", "company", "psc",
}
GENERIC_TOKENS = {
    "dom", "maklerski", "maklerskie", "biuro", "departament", "dm", "bm", "bank", "banku",
    "securities", "brokers", "broker", "investment", "investments", "invest", "capital",
    "kapital", "management", "asset", "assets", "wealth", "partners", "group", "grupa",
    "holding", "financial", "finance", "services", "markets", "trading", "europe", "polska",
    "poland", "international", "global", "inwestycyjny", "towarzystwo", "funduszy", "fund",
    "funds", "advisory", "advisors", "consulting", "family", "office", "private", "banking",
    "the", "and", "i", "of", "de", "eu",
}

LISTED_THRESHOLD = 0.9
SIMILAR_THRESHOLD = 0.72


def _tokens(name: str) -> list[str]:
    text = fold(name).replace(".", "").replace("'", "")
    return re.findall(r"[^\W_]+", text)


def _split(name: str) -> tuple[list[str], list[str]]:
    """(name tokens, legal-form tokens). "S.A." -> "sa", "sp. z o.o." -> "sp z oo"."""
    toks = _tokens(name)
    legal: list[str] = []
    for seq in LEGAL_SEQUENCES:
        n = len(seq)
        i = 0
        while i <= len(toks) - n:
            if tuple(toks[i : i + n]) == seq and i > 0:
                legal.append("".join(seq))
                del toks[i : i + n]
            else:
                i += 1
    kept = [t for t in toks if t not in LEGAL_TOKENS]
    legal += [t for t in toks if t in LEGAL_TOKENS]
    return (kept, legal) if kept else (toks, [])


def name_tokens(name: str) -> list[str]:
    """Tokens of a name without its legal form."""
    return _split(name)[0]


def legal_form(name: str) -> str:
    return " ".join(sorted(set(_split(name)[1])))


def normalize_name(name: str) -> str:
    return " ".join(name_tokens(name))


def core_name(name: str) -> str:
    toks = [t for t in name_tokens(name) if t not in GENERIC_TOKENS]
    return " ".join(toks)


@dataclass(frozen=True)
class Match:
    entry: dict
    score: float
    how: str  # exact | alias | core | fuzzy | brand_contained

    @property
    def listed(self) -> bool:
        return self.score >= LISTED_THRESHOLD


def _keys(entry: dict) -> list[tuple[str, str]]:
    """(normalised name, kind) for the entry name and all aliases; cached on the entry."""
    cached = entry.get("_keys")
    if cached is None:
        name = entry["name"]
        names = [(name, "exact")] + [(a, "alias") for a in entry.get("aliases", []) if a]
        # "BANK PEKAO S.A. (BANK POLSKA KASA OPIEKI S.A.)" -> both variants are valid names.
        for inner in re.findall(r"\(([^)]{3,})\)", name):
            names += [(inner, "alias"), (re.sub(r"\s*\([^)]*\)", "", name), "exact")]
        cached = [(normalize_name(n), kind) for n, kind in names]
        cached = [(k, kind) for k, kind in cached if k]
        entry["_keys"] = cached
        entry["_forms"] = {legal_form(n) for n, _ in names}
        entry["_cores"] = sorted(c for c in {core_name(n) for n, _ in names} if len(c) >= 3)
    return cached


def _core_ratio(q_core: str, entry: dict) -> float:
    if not q_core:
        return 0.0
    return max((SequenceMatcher(None, q_core, c).ratio() for c in entry["_cores"]), default=0.0)


def best_match(query: str, entries: list[dict]) -> Match | None:
    """Best register entry for `query`, or None when nothing is even similar."""
    q_norm = normalize_name(query)
    if not q_norm:
        return None
    q_core = core_name(query)
    q_tokens = set(q_norm.split())
    q_form = legal_form(query)
    best: Match | None = None

    def consider(entry: dict, score: float, how: str) -> None:
        nonlocal best
        if best is None or score > best.score:
            best = Match(entry, round(score, 3), how)

    for entry in entries:
        for key, kind in _keys(entry):
            if key == q_norm:
                consider(entry, 1.0, kind)
                continue
            key_tokens = set(key.split())
            if not (key_tokens & q_tokens) and key[:3] != q_norm[:3]:
                continue
            ratio = SequenceMatcher(None, q_norm, key).ratio()
            if ratio >= SIMILAR_THRESHOLD and _core_ratio(q_core, entry) >= 0.8:
                consider(entry, min(ratio, 0.99), "fuzzy")
        for core in entry["_cores"]:
            if q_core and core == q_core:
                # Same brand. A different legal form ("XTB Ltd" vs "XTB S.A.") is another
                # entity using the brand, not the registered one.
                same_form = not q_form or q_form in entry["_forms"]
                consider(entry, 0.94 if same_form else 0.8, "core" if same_form else "brand_contained")
            elif set(core.split()) <= q_tokens and len(core) >= 3:
                # The registered brand is embedded in a longer, different name.
                consider(entry, 0.8, "brand_contained")
    return best


def find_brands_in_text(text: str, folded: str, entries: list[dict]) -> list[tuple[int, int, dict]]:
    """Occurrences of register names (legal form optional) in a text: (start, end, entry).

    Single-word names must start with a capital letter in the original text, so that a
    register entry never matches an ordinary lower-case word.
    """
    index: dict[str, dict] = {}
    for entry in entries:
        for key, _ in _keys(entry):
            if len(key) >= 3 and key not in GENERIC_TOKENS:
                index.setdefault(key, entry)
    words = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"[^\W_]+", folded)]
    hits: list[tuple[int, int, dict]] = []
    i = 0
    while i < len(words):
        found = False
        for n in range(min(6, len(words) - i), 0, -1):
            key = " ".join(w for _, _, w in words[i : i + n])
            entry = index.get(key)
            if entry is None:
                continue
            start, end = words[i][0], words[i + n - 1][1]
            if n == 1 and not text[start].isupper():
                continue
            hits.append((start, end, entry))
            i += n
            found = True
            break
        if not found:
            i += 1
    return hits
