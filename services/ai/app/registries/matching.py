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
    ("spolka", "z", "ograniczona", "odpowiedzialnoscia"),
    ("spolka", "akcyjna"),
    ("spolka", "komandytowa"),
    ("spolka", "jawna"),
    ("sp", "z", "o", "o"),
    ("sp", "z", "oo"),
    ("sp", "zoo"),
    ("sp", "k"),
    ("sp", "j"),
    ("s", "a"),
    ("a", "s"),
    ("s", "r", "o"),
    ("b", "v"),
    ("n", "v"),
    ("oddzial", "w", "polsce"),
]
LEGAL_TOKENS = {
    "sa",
    "spzoo",
    "zoo",
    "spk",
    "spj",
    "ska",
    "ltd",
    "limited",
    "llc",
    "llp",
    "lp",
    "plc",
    "inc",
    "corp",
    "corporation",
    "gmbh",
    "ag",
    "kg",
    "ug",
    "se",
    "sarl",
    "sas",
    "spa",
    "srl",
    "sau",
    "bv",
    "nv",
    "as",
    "sro",
    "oy",
    "oyj",
    "ab",
    "asa",
    "ou",
    "uab",
    "sia",
    "doo",
    "ead",
    "kft",
    "zrt",
    "cy",
    "co",
    "company",
    "psc",
}
GENERIC_TOKENS = {
    "dom",
    "maklerski",
    "maklerskie",
    "biuro",
    "departament",
    "dm",
    "bm",
    "bank",
    "banku",
    "securities",
    "brokers",
    "broker",
    "investment",
    "investments",
    "invest",
    "capital",
    "kapital",
    "management",
    "asset",
    "assets",
    "wealth",
    "partners",
    "group",
    "grupa",
    "holding",
    "financial",
    "finance",
    "services",
    "markets",
    "trading",
    "europe",
    "polska",
    "poland",
    "international",
    "global",
    "inwestycyjny",
    "towarzystwo",
    "funduszy",
    "fund",
    "funds",
    "advisory",
    "advisors",
    "consulting",
    "family",
    "office",
    "private",
    "banking",
    "the",
    "and",
    "i",
    "of",
    "de",
    "eu",
}

NEUTRAL_DESCRIPTORS = {
    "dom",
    "maklerski",
    "maklerskie",
    "biuro",
    "departament",
    "dm",
    "bm",
    "bank",
    "banku",
    "polska",
    "poland",
    "grupa",
    "group",
    "broker",
    "brokers",
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
        entry["_tokens"] = {t for k, _ in cached for t in k.split()}
        entry["_forms"] = {legal_form(n) for n, _ in names}
        entry["_cores"] = sorted(c for c in {core_name(n) for n, _ in names} if len(c) >= 3)
    return cached


def _core_ratio(q_core: str, entry: dict) -> float:
    if not q_core:
        return 0.0
    return max((SequenceMatcher(None, q_core, c).ratio() for c in entry["_cores"]), default=0.0)


def _tokens_alike(a: set[str], b: set[str]) -> bool:
    return all(any(x == y or SequenceMatcher(None, x, y).ratio() >= 0.8 for y in b) for x in a)


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
                # Same name but another legal form ("XTB sp. z o.o." vs "XTB S.A.") is a
                # different entity.
                if q_form and entry["_forms"] - {""} and q_form not in entry["_forms"]:
                    consider(entry, 0.8, "brand_contained")
                else:
                    consider(entry, 1.0, kind)
                continue
            key_tokens = set(key.split())
            if not (key_tokens & q_tokens) and key[:3] != q_norm[:3]:
                continue
            ratio = SequenceMatcher(None, q_norm, key).ratio()
            # Fuzzy = typo tolerance only: same number of words, similar brand core.
            if (
                ratio >= SIMILAR_THRESHOLD
                and len(key_tokens) == len(q_tokens)
                and _core_ratio(q_core, entry) >= 0.8
                and _tokens_alike(q_tokens, key_tokens)
            ):
                consider(entry, min(ratio, 0.99), "fuzzy")
        for core in entry["_cores"]:
            core_tokens = set(core.split())
            if q_core and core == q_core:
                # Same brand. It is the registered entity only if the legal form agrees and
                # the query adds nothing but neutral descriptors ("Dom Maklerski XTB").
                # "XTB Wealth Partners Ltd" is a different entity using the brand.
                extra = q_tokens - core_tokens - entry["_tokens"] - NEUTRAL_DESCRIPTORS
                same_form = not q_form or q_form in entry["_forms"]
                ok = same_form and not extra
                consider(entry, 0.94 if ok else 0.8, "core" if ok else "brand_contained")
            elif core_tokens <= q_tokens:
                # The registered brand is embedded in a longer, different name.
                consider(entry, 0.8, "brand_contained")
    return best


def _names_brand(key: str) -> bool:
    return len(key) >= 3 and not set(key.split()) <= (GENERIC_TOKENS | NEUTRAL_DESCRIPTORS)


def compile_brand_index(entries: list[dict]) -> dict:
    """A longest-prefix index. Sector words alone never identify a particular firm."""
    root: dict = {}
    for entry in entries:
        # A key made only of generic words ("dom maklerski" left of "DOM MAKLERSKI INC S.A.")
        # names no brand and would match every brokerage house mentioned in a text.
        # key -> whether the match needs a capital letter: a name that is one word once its legal
        # form is dropped ("mBank S.A." -> "mbank") must not match an ordinary lower-case word.
        keys = {key: len(key.split()) == 1 for key, _ in _keys(entry) if _names_brand(key)}
        # Preserve a literal full legal name too: INC can be a brand inside a Polish
        # registered name, although it is normally an English legal-form token.
        for name in [entry["name"], *entry.get("aliases", [])]:
            literal = " ".join(re.findall(r"[^\W_]+", fold(name)))
            if _names_brand(literal):
                keys.setdefault(literal, len(normalize_name(name).split()) <= 1)
        for key, needs_capital in keys.items():
            node = root
            for token in key.split():
                node = node.setdefault(token, {})
            node.setdefault(None, (entry, needs_capital))
    return root


def find_brands_in_text(
    text: str, folded: str, entries: list[dict], index: dict | None = None
) -> list[tuple[int, int, dict]]:
    """Longest register-name occurrences, with original source offsets.

    One-word brands (legal form aside) require a capital letter. A trie removes the old six-word limit
    and lets RegistryStore reuse its index across documents without repeated rebuilding.
    """
    index = compile_brand_index(entries) if index is None else index
    words = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"[^\W_]+", folded)]
    hits: list[tuple[int, int, dict]] = []
    i = 0
    while i < len(words):
        node, j, best = index, i, None
        while j < len(words) and words[j][2] in node:
            node = node[words[j][2]]
            j += 1
            if None in node:
                entry, needs_capital = node[None]
                if not needs_capital or text[words[i][0]].isupper():
                    best = (j, entry)
        if best is None:
            i += 1
            continue
        end, entry = best
        hits.append((words[i][0], words[end - 1][1], entry))
        i = end
    return hits
