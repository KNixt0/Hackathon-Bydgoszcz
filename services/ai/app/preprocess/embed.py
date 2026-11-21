"""Embeddings behind one interface.

`HashEmbedder` is the default: hashed character n-grams plus word tokens, L2-normalised,
compared by cosine similarity. It needs no model download and runs in microseconds, which
keeps the service usable on any laptop. `OllamaEmbedder` is an optional drop-in that calls
a local Ollama embedding model when `EMBEDDINGS_BACKEND=ollama` is configured.
"""

from __future__ import annotations

import hashlib
import logging
import math
from abc import ABC, abstractmethod

import httpx

from .normalize import fold
from .tokens import tokenize

log = logging.getLogger(__name__)
Vector = dict[int, float]


class Embedder(ABC):
    name: str = "base"
    # Cosine similarity above which two short texts count as "the same statement".
    similar_threshold: float = 0.5
    duplicate_threshold: float = 0.8

    @abstractmethod
    def embed(self, text: str) -> Vector: ...

    def similarity(self, a: str, b: str) -> float:
        return cosine(self.embed(a), self.embed(b))


def cosine(a: Vector, b: Vector) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def _bucket(feature: str, dim: int) -> int:
    return int.from_bytes(hashlib.blake2b(feature.encode("utf-8"), digest_size=4).digest(), "big") % dim


class HashEmbedder(Embedder):
    name = "hash-ngram"

    def __init__(self, dim: int = 2048, ngram: tuple[int, int] = (3, 5)) -> None:
        self.dim = dim
        self.ngram = ngram
        self._cache: dict[str, Vector] = {}

    def embed(self, text: str) -> Vector:
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        vec: Vector = {}
        tokens = tokenize(text)
        for tok in tokens:
            key = _bucket("w:" + tok, self.dim)
            vec[key] = vec.get(key, 0.0) + 1.0
        joined = " " + " ".join(tokens) + " "
        lo, hi = self.ngram
        for n in range(lo, hi + 1):
            for i in range(len(joined) - n + 1):
                key = _bucket(f"c{n}:" + joined[i : i + n], self.dim)
                vec[key] = vec.get(key, 0.0) + 0.5
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vec = {k: v / norm for k, v in vec.items()}
        if len(self._cache) < 5000:
            self._cache[text] = vec
        return vec


class OllamaEmbedder(Embedder):
    """Dense embeddings from a local Ollama model, with the hash embedder as fallback."""

    name = "ollama"
    similar_threshold = 0.72
    duplicate_threshold = 0.92

    def __init__(self, base_url: str, model: str, timeout_s: float = 4.0) -> None:
        self.base_url = base_url
        self.model = model
        self.timeout_s = timeout_s
        self._fallback = HashEmbedder()
        self._healthy = True
        self._cache: dict[str, Vector] = {}

    def embed(self, text: str) -> Vector:
        if not self._healthy:
            return self._fallback.embed(text)
        if text in self._cache:
            return self._cache[text]
        try:
            resp = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": fold(text)},
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            values = resp.json()["embedding"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            log.warning("ollama embeddings unavailable, using hash embedder: %s", exc)
            self._healthy = False
            self.similar_threshold = self._fallback.similar_threshold
            self.duplicate_threshold = self._fallback.duplicate_threshold
            return self._fallback.embed(text)
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        vec = {i: v / norm for i, v in enumerate(values)}
        self._cache[text] = vec
        return vec


def build_embedder(backend: str, ollama_url: str, model: str | None) -> Embedder:
    if backend == "ollama" and model:
        return OllamaEmbedder(ollama_url, model)
    return HashEmbedder()
