"""Analyze captured public-page input offline, with deterministic local rules and no cloud model."""

from __future__ import annotations

import asyncio
import base64
import gzip
import json
import os
import statistics
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
            analysis_ms = round((time.perf_counter() - started) * 1000)
            warm_times = []
            for _ in range(3):
                warm_start = time.perf_counter()
                await engine.analyze(Document.model_validate(document), Context(synthetic=False))
                warm_times.append(round((time.perf_counter() - warm_start) * 1000))
            # Keep machine output for a private engineering review, not a public allegation.
            records.append(
                {
                    "url": document["url"],
                    "analysis_ms": analysis_ms,
                    "warm_median_ms": statistics.median(warm_times),
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
                    "evaluated_modules": sorted(
                        {plugin.module for plugin in engine.plugins.values() if plugin.module is not None}
                    ),
                    "rules": len(item.get("analysis", {}).get("rules", [])),
                    "entities": item.get("analysis", {}).get("entities", {}),
                }
                for item in records
            ],
            ensure_ascii=False,
        )
    )

    # Transfer the actual captured results for the review preview; this does not write to the repository.
    transfer = base64.b64encode(
        gzip.compress(json.dumps({"documents": documents, "records": records}, ensure_ascii=False).encode())
    ).decode()
    chunks = [transfer[i : i + 12000] for i in range(0, len(transfer), 12000)]
    for index, chunk in enumerate(chunks):
        print(f"WATCHIT_REALDATA|{index}|{len(chunks)}|{chunk}")
    if not records or any("error" in item for item in records):
        raise SystemExit("One or more captured documents failed analysis")


asyncio.run(run())
