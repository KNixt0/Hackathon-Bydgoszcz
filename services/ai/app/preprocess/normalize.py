"""Text normalisation, matching fold and the dedup hash."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
_SPACES = re.compile(r"[ \t\r\f\v  -   　]+")
_FOLD_MAP = str.maketrans(
    "ąćęłńóśźżäöüßáéíúàèâêôçñ’‘`´“”„«»–—‑",
    "acelnoszzaousaeiuaeaeocn''''\"\"\"\"\"---",
)


def normalize_line(text: str) -> str:
    """NFC, drop zero-width characters, collapse whitespace inside one line."""
    text = unicodedata.normalize("NFC", text).translate(_ZERO_WIDTH)
    return _SPACES.sub(" ", text.replace("\n", " ")).strip()


def normalize_text(text: str) -> str:
    """Normalise a plain-text document; paragraph breaks survive as single newlines."""
    lines = (normalize_line(line) for line in unicodedata.normalize("NFC", text).split("\n"))
    return "\n".join(line for line in lines if line)


def fold(text: str) -> str:
    """Lower-case and strip diacritics, character for character.

    The result has exactly the same length as the input, so a regex match on the folded
    text is also a valid span in the original text. All lexicons are written in this form.
    """
    out = []
    for ch in text:
        low = ch.lower()
        out.append(low if len(low) == 1 else ch)
    return "".join(out).translate(_FOLD_MAP)


def content_hash(normalized_text: str) -> str:
    """Dedup key: sha256 of the normalised text."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
