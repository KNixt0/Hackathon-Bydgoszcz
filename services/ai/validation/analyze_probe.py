"""Analyze captured public-page input offline, with deterministic local rules and no cloud model."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

from app.config import load_settings
from app.engine import Engine
from app.schemas import Context, Document

output = Path(os.environ.get("VALIDATION_OUTPUT", "validation-results"))


async def run():
    documents = json.loads((output / "live-documents.json").read_text())
    engine = Engine(load_settings())
    records = []
    for document in documents:
        started = time.perf_counter()
        try:
            result = await engine.analyze(Document.model_validate(document), Context(synthetic=False))
            payload = result.model_dump(mode="json")
            # Keep machine output for a private engineering review, not a public allegation.
            records.append(
                {
                    "url": document["url"],
                    "analysis_ms": round((time.perf_counter() - started) * 1000),
                    "analysis": payload,
                }
            )
        except Exception as error:
            records.append({"url": document["url"], "error": f"{type(error).__name__}: {error}"})
    (output / "live-analysis.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(
        json.dumps(
            [
                {k: v for k, v in item.items() if k != "analysis"}
                | {
                    "evaluated_plugins": item.get("analysis", {}).get("engine", {}).get("plugins", []),
                    "rules": len(item.get("analysis", {}).get("rules", [])),
                    "entities": item.get("analysis", {}).get("entities", {}),
                }
                for item in records
            ],
            ensure_ascii=False,
        )
    )


asyncio.run(run())
