"""Bounded end-to-end workload: real captured inputs, actual local model, isolated SQLite.

Six persisted jobs replay three captures twice, with two workers. The capture transport
is the only replaced boundary; the AI HTTP client, model, database, archive, APIs and
case workflow execute normally. This is a smoke workload, not a capacity benchmark.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.main import api
from app.pipeline import process_job
from validation.captured_input import CapturedFetcher

out = Path(os.environ.get("VALIDATION_OUTPUT", "validation-results"))
out.mkdir(parents=True, exist_ok=True)
capture = Path(os.environ["CAPTURE_DIRECTORY"])
documents = json.loads((capture / "live-documents.json").read_text())
assert len(documents) == 3
fetcher = CapturedFetcher(documents)
report = {"model": os.environ["OLLAMA_MODEL"], "workers": 2, "jobs": [], "checks": [], "incidents": []}


def timed_job(job_id):
    start = time.perf_counter()
    delay = process_job(job_id)
    return {"id": job_id, "elapsed_ms": round((time.perf_counter() - start) * 1000), "retry_delay": delay}


def request(client, method, url, expected=200, **kwargs):
    response = client.request(method, url, **kwargs)
    assert response.status_code == expected, (url, response.status_code, response.text[:500])
    return response


with (
    TestClient(api) as client,
    patch("app.api.scans.dispatch"),
    patch("app.pipeline.get_fetcher", return_value=fetcher),
):
    request(client, "POST", "/api/auth/demo", json={"role": "SUPERVISOR"})
    health = request(client, "GET", "/api/health").json()
    assert health["ai"]["llm_available"], health
    # Prove that the model actually generated text, rather than silently using fallback.
    warmup = httpx.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": report["model"],
            "prompt": "Reply with OK.",
            "stream": False,
            "options": {"num_predict": 8},
        },
        timeout=120,
    )
    warmup.raise_for_status()
    result = warmup.json()
    assert result.get("response", "").strip(), result
    report["model_warmup"] = {
        key: result.get(key) for key in ("model", "done", "eval_count", "eval_duration", "load_duration")
    }
    started = time.perf_counter()
    for wave in range(2):
        ids = [
            request(client, "POST", "/api/scans", 202, json={"url": d["url"]}).json()["job_id"]
            for d in documents
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            report["jobs"].extend(pool.map(timed_job, ids))
        jobs = request(client, "GET", "/api/scans").json()["items"]
        for job in jobs:
            assert job["state"] == "done", job
        listing = request(client, "GET", "/api/incidents").json()
        assert listing["total"] == 3, "Replays created duplicate cases"
        if wave == 0:
            first = listing["items"][0]["id"]
            assigned = request(client, "POST", f"/api/incidents/{first}/assign").json()
            processing_start = assigned["workflow"]["processing_started_at"]
            assert processing_start
            request(client, "POST", f"/api/incidents/{first}/transition", json={"to": "in_review"})
    report["workload_elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    for summary in listing["items"]:
        case = request(client, "GET", f"/api/incidents/{summary['id']}").json()
        assert len(case["rules"]) == 19
        versions = request(client, "GET", f"/api/incidents/{case['id']}/versions").json()["items"]
        assert len(versions) == 2
        key = case["source"]["archive"]["html_key"]
        archive = request(client, "GET", f"/api/evidence/{key}")
        assert archive.headers["content-type"].startswith("text/plain")
        exported = request(client, "GET", f"/api/incidents/{case['id']}/export.csv")
        assert len(exported.content) > 100
        pdf = request(client, "GET", f"/api/incidents/{case['id']}/export.pdf")
        assert pdf.content.startswith(b"%PDF")
        report["incidents"].append(
            {
                "url": case["source"]["url"],
                "firm": case["entities"]["investment_firm"],
                "engine": case["engine"],
                "versions": len(versions),
            }
        )
    repeated = request(client, "GET", f"/api/incidents/{first}").json()
    assert repeated["workflow"]["processing_started_at"] == processing_start
    assert repeated["status"] == "in_review"
    request(client, "POST", f"/api/incidents/{first}/transition", 422, json={"to": "resolved"})
    closed = request(
        client,
        "POST",
        f"/api/incidents/{first}/transition",
        json={"to": "resolved", "reason": "Zamknięcie wyłącznie w izolowanej symulacji."},
    ).json()
    assert closed["workflow"]["processing_finished_at"]
    request(client, "PUT", "/api/settings/thresholds", json={"flag": 25, "critical": 75})
    supervisor_notice = request(client, "GET", "/api/notifications").json()["items"][0]
    request(client, "POST", f"/api/notifications/{supervisor_notice['id']}/read")
    audit = request(client, "GET", "/api/audit?action=thresholds&sort=at&order=asc").json()
    assert audit["total"] == 1
    request(client, "GET", "/api/audit?from=2099-01-01", 422)
    request(client, "POST", "/api/auth/logout", 204)
    request(client, "POST", "/api/auth/demo", json={"role": "ANALYST"})
    analyst_notice = request(client, "GET", "/api/notifications").json()["items"][0]
    assert analyst_notice["read_at"] is None
    request(client, "POST", f"/api/notifications/{supervisor_notice['id']}/read", 404)
    request(client, "PUT", "/api/settings/thresholds", 403, json={"flag": 20, "critical": 70})
    request(client, "GET", "/api/audit", 403)
    report["checks"] = [
        "six_jobs_completed",
        "three_cases_deduplicated",
        "nineteen_rule_rows",
        "two_versions_each",
        "archive_read",
        "csv_export",
        "pdf_export",
        "assignment_survives_rescan",
        "closure_time_saved",
        "reason_required",
        "audit_filter_sort",
        "future_date_rejected",
        "per_user_notification_read_state",
        "supervisor_permissions",
    ]
times = [job["elapsed_ms"] for job in report["jobs"]]
report["latency_ms"] = {"median": statistics.median(times), "max": max(times)}
report["llm_used_cases"] = sum(case["engine"]["llm_used"] for case in report["incidents"])
(out / "model-workload.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
print("WATCHIT_WORKLOAD|" + json.dumps(report, ensure_ascii=False))
assert report["llm_used_cases"] > 0, "The model answered but every analysis rejected or timed out its output"
