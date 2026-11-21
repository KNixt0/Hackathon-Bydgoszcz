"""HTTP API of the AI service (see coord/contracts/api.md)."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .config import load_settings
from .engine import Engine
from .registries import CONTEXT_ONLY, REGISTRIES
from .schemas import Analysis, AnalyzeRequest, RegistryPut

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("investwatch.ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.engine = Engine(settings)
    log.info("engine ready: plugins=%s llm_enabled=%s", list(app.state.engine.plugins), settings.llm_enabled)
    yield


app = FastAPI(title="InvestWatch AI", version="0.1.0", lifespan=lifespan)


def _engine() -> Engine:
    return app.state.engine


def _registry_rows(with_meta: bool) -> list[dict]:
    rows = _engine().registries.summary()
    if with_meta:
        return rows
    return [{k: r[k] for k in ("registry", "entries", "snapshot_date")} for r in rows]


@app.get("/health")
async def health() -> dict:
    engine = _engine()
    available = await engine.llm.available()
    embedder = engine.embedder
    embed_ok = await asyncio.to_thread(embedder.probe)  # real request for the Ollama backend
    return {
        "status": "ok",
        "llm_enabled": engine.llm.enabled,
        "llm_available": available,
        "model": engine.llm.model if available else None,
        "embeddings": {
            "requested": engine.settings.embeddings_backend,
            "backend": embedder.active if embed_ok else "hash-ngram",
            "model": embedder.model if embedder.active == "ollama" else None,
        },
        "plugins": list(engine.plugins),
        "registries": _registry_rows(with_meta=False),
    }


@app.post("/analyze", response_model=Analysis)
async def analyze(request: AnalyzeRequest) -> Analysis:
    return await _engine().analyze(request.document, request.context)


@app.get("/plugins")
async def plugins() -> dict:
    return {
        "items": [{"id": p.id, "module": p.module, "description": p.description} for p in _engine().plugins.values()]
    }


@app.get("/registries")
async def registries() -> dict:
    return {"items": _registry_rows(with_meta=True)}


@app.put("/registries/{registry}")
async def put_registry(registry: str, body: RegistryPut) -> dict:
    if registry not in REGISTRIES:
        raise HTTPException(status_code=404, detail=f"Nieznany rejestr: {registry}")
    if registry in CONTEXT_ONLY:
        raise HTTPException(
            status_code=422, detail="Rejestr zasilany wyłącznie z kontekstu analizy (źródło wewnętrzne UKNF)"
        )
    entries = [e.model_dump(exclude_defaults=True) | {"name": e.name} for e in body.entries]
    try:
        count = _engine().registries.replace(registry, body.snapshot_date, entries)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Nie można zapisać migawki rejestru: {exc}") from exc
    return {"entries": count}
