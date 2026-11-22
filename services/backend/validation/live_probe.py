"""At most three official public pages, one attempt each, with robots.txt and normal SSRF guards.

This is an extraction experiment. It does not publish findings or submit decisions about firms.
The stored HTML is a bounded, untrusted test input and is never executed by this script.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from app.models import ScanJob
from app.pipeline import build_document
from app.scraper.engine import Fetcher

URLS = ["https://bossa.pl/oferta", "https://www.xtb.com/pl/konto-i-oplaty", "https://www.bm.pkobp.pl/oferta/rachunek-inwestycyjny"]
output = Path(os.environ.get("VALIDATION_OUTPUT", "validation-results"))
output.mkdir(parents=True, exist_ok=True)
results, documents = [], []
fetcher = Fetcher()
for index, url in enumerate(URLS):
    start = time.perf_counter()
    record = {"url": url, "at": datetime.now(UTC).isoformat()}
    try:
        page = fetcher.fetch(url, render=False)
        record.update(http_status=page.status, final_url=page.url, html_bytes=len(page.body.encode()), engine=page.engine)
        if page.status >= 400:
            record["error"] = f"HTTP {page.status}; no retry or bypass attempted"
        else:
            job = ScanJob(id=f"probe-{index}", url=url, fetch_url=url, origin="scan", meta={}, context={})
            document = build_document(job, page, fetcher)
            record.update(title=document["title"], text_chars=len(document["text"]), sha256=hashlib.sha256(document["text"].encode()).hexdigest())
            if document["text"].strip():
                documents.append(document)
            else:
                record["error"] = "No readable text extracted"
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
    record["elapsed_ms"] = round((time.perf_counter() - start) * 1000)
    results.append(record)
report = {"at": datetime.now(UTC).isoformat(), "limit": 3, "results": results}
(output / "live-scrape.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
(output / "live-documents.json").write_text(json.dumps(documents, ensure_ascii=False))
print(json.dumps(report, ensure_ascii=False))
