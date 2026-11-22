"""Re-extract existing captured HTML through the current parser without fetching it again."""

import json
import os
from pathlib import Path

from app.models import ScanJob
from app.pipeline import build_document
from validation.captured_input import CapturedFetcher

output = Path(os.environ.get("VALIDATION_OUTPUT", "validation-results"))
path = output / "live-documents.json"
documents = json.loads(path.read_text())
fetcher = CapturedFetcher(documents)
updated = []
for index, document in enumerate(documents):
    url = document["url"]
    job = ScanJob(id=f"replay-{index}", url=url, fetch_url=url, origin="scan", meta={}, context={})
    updated.append(build_document(job, fetcher.fetch(url), fetcher))
path.write_text(json.dumps(updated, ensure_ascii=False))
print(json.dumps({"reextracted_publishers": [{"url": d["url"], "author": d.get("author")} for d in updated]}))
