from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from app.config import load_settings  # noqa: E402
from app.context import AnalysisContext  # noqa: E402
from app.engine import Engine  # noqa: E402
from app.preprocess import HashEmbedder, preprocess  # noqa: E402
from app.registries import RegistryStore  # noqa: E402
from app.schemas import Context, Document  # noqa: E402

SAMPLES = ROOT.parent.parent / "samples"
FETCHED_AT = "2026-11-21T12:00:00Z"


@pytest.fixture(scope="session")
def registries() -> RegistryStore:
    return RegistryStore(data_dir=None, demo_overlay=True)


@pytest.fixture(scope="session")
def engine(registries) -> Engine:
    return Engine(load_settings(), registries)


@pytest.fixture(scope="session")
def make_ctx(registries):
    embedder = HashEmbedder()

    def _make(
        text: str = "",
        html: str = "",
        title: str = "",
        url: str = "https://test.example/x",
        platform: str = "web",
        author: dict | None = None,
        **context,
    ) -> AnalysisContext:
        doc = Document(
            url=url, platform=platform, fetched_at=FETCHED_AT, title=title, html=html, text=text, author=author
        )
        page = preprocess(html, text, title)
        return AnalysisContext(doc, Context.model_validate(context), page, registries, embedder)

    return _make


@pytest.fixture(scope="session")
def analyze(engine):
    def _analyze(
        text: str = "",
        html: str = "",
        title: str = "",
        url: str = "https://test.example/x",
        platform: str = "web",
        author: dict | None = None,
        **context,
    ):
        doc = Document(
            url=url, platform=platform, fetched_at=FETCHED_AT, title=title, html=html, text=text, author=author
        )
        return asyncio.run(engine.analyze(doc, Context.model_validate(context)))

    return _analyze


@pytest.fixture(scope="session")
def analyze_sample(engine):
    from run_eval import analyze_file

    cache: dict[Path, object] = {}

    def _analyze(path: Path):
        if path not in cache:
            cache[path] = asyncio.run(analyze_file(engine, path))
        return cache[path]

    return _analyze
