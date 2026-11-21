"""Samples ("pendrive" format): discovery under SAMPLES_DIR and turning them into scan jobs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from app.config import get_settings

log = logging.getLogger(__name__)

BARE_SUFFIXES = {".html", ".htm", ".txt"}
MAX_SAMPLE_JSON_BYTES = 5_000_000


class UnsafePath(ValueError):
    pass


def samples_root() -> Path:
    return Path(get_settings().samples_dir).resolve()


def safe_join(root: Path, relative: str) -> Path:
    """Resolve `relative` under `root`; refuse anything that escapes it (.., absolute, symlinks out)."""
    if "\x00" in relative or relative.startswith(("/", "\\")) or Path(relative).is_absolute():
        raise UnsafePath("path must be relative")
    root = root.resolve()
    target = (root / relative).resolve()
    if target != root and not target.is_relative_to(root):
        raise UnsafePath("path escapes the samples directory")
    return target


@dataclass
class Sample:
    path: str  # the .json (or bare file), relative to the samples root, posix style
    fetch_path: str  # the file the scraper fetches from /fixtures/
    meta: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)

    @property
    def seed(self) -> bool:
        return self.meta.get("seed") is not False

    @property
    def fixture_url(self) -> str:
        return f"{get_settings().fixture_base_url}/fixtures/{quote(self.fetch_path)}"

    @property
    def url(self) -> str:
        url = self.meta.get("url")
        return url if isinstance(url, str) and url.startswith(("http://", "https://")) else self.fixture_url


def _visible(path: Path, root: Path) -> bool:
    return not any(part.startswith(".") for part in path.relative_to(root).parts)


def _load_json_sample(path: Path, root: Path) -> Sample | None:
    try:
        if path.stat().st_size > MAX_SAMPLE_JSON_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("unreadable sample json", extra={"sample": path.name})
        return None
    if not isinstance(data, dict):
        return None
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    context = data.get("context") if isinstance(data.get("context"), dict) else {}
    relative = path.relative_to(root).as_posix()
    html_file = data.get("html_file")
    if isinstance(html_file, str) and html_file:
        try:
            target = safe_join(root, (path.parent.relative_to(root) / html_file).as_posix())
        except UnsafePath:
            log.warning("sample html_file outside samples dir", extra={"sample": path.name})
            return None
        if not target.is_file():
            log.warning("sample html_file missing", extra={"sample": path.name})
            return None
        return Sample(relative, target.relative_to(root).as_posix(), meta, context)
    if isinstance(data.get("text"), str) and data["text"].strip():
        return Sample(relative, relative, meta, context)
    return None  # some other json (not a sample)


def discover(subdir: str | None = None) -> list[Sample]:
    """All samples under SAMPLES_DIR[/subdir], sorted by path. Raises UnsafePath for a bad subdir."""
    root = samples_root()
    base = safe_join(root, subdir) if subdir else root
    if not base.exists():
        return []
    files = (
        [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file() and _visible(p, root))
    )
    samples: list[Sample] = []
    claimed: set[str] = set()
    for path in files:
        if path.suffix.lower() == ".json":
            sample = _load_json_sample(path, root)
            if sample:
                samples.append(sample)
                claimed.add(sample.fetch_path)
    for path in files:
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() in BARE_SUFFIXES and relative not in claimed:
            if path.with_suffix(".json").is_file() and path.with_suffix(".json") in files:
                continue  # belongs to a json that was rejected or uses another html_file
            samples.append(Sample(relative, relative, {"platform": "sample", "title": path.stem}, {}))
    samples.sort(key=lambda s: s.path)
    return samples


def find_demo_case(case: str) -> Sample | None:
    for sample in discover():
        if sample.context.get("demo_case") == case:
            return sample
    return None
