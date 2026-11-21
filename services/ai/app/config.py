"""Runtime configuration. Everything comes from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BUNDLED_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _flag(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    port: int
    data_dir: Path  # writable: runtime register snapshots land here
    demo_overlay: bool  # merge the fictional demo entities into the registers
    llm_enabled: bool
    ollama_url: str
    ollama_model: str | None
    llm_timeout_s: float
    embeddings_backend: str  # "hash" (default, local) or "ollama"
    ollama_embed_model: str | None


def load_settings() -> Settings:
    return Settings(
        port=int(os.environ.get("AI_PORT", "8001")),
        data_dir=Path(os.environ.get("AI_DATA_DIR", str(BUNDLED_DATA_DIR / "runtime"))),
        demo_overlay=_flag("AI_DEMO_OVERLAY", True),
        llm_enabled=_flag("LLM_ENABLED", False),
        ollama_url=os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/"),
        ollama_model=os.environ.get("OLLAMA_MODEL") or None,
        llm_timeout_s=float(os.environ.get("LLM_TIMEOUT_S", "8")),
        embeddings_backend=os.environ.get("EMBEDDINGS_BACKEND", "hash").strip().lower(),
        ollama_embed_model=os.environ.get("OLLAMA_EMBED_MODEL") or None,
    )
