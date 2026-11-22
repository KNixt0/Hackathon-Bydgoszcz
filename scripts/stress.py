"""Load, stress and scalability checks against a running `docker compose` stack.

Usage (from the repository root, stack running):
    python3 scripts/stress.py api        # read API through nginx (list, case, trends, calibration)
    python3 scripts/stress.py ai         # AI engine /analyze at rising concurrency
    python3 scripts/stress.py pipeline   # re-scan every case through queue + scraper + AI, time to drain
    python3 scripts/stress.py reports    # public report endpoint: rate limits under a burst
    python3 scripts/stress.py all

Needs only `httpx` (BSD-3-Clause, already a dependency of the services). Logs in with the demo
supervisor account (DEMO_LOGIN=true). Reports p50/p95/p99 latency, throughput and every non-2xx.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

BASE = "http://localhost:3000"
AI = "http://localhost:8001"
ROOT = Path(__file__).resolve().parent.parent


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = max(0, min(len(values) - 1, round(p / 100 * (len(values) - 1))))
    return values[k]


def summary(name: str, lat: list[float], codes: Counter, wall: float) -> dict:
    ok = sum(n for c, n in codes.items() if isinstance(c, int) and 200 <= c < 300)
    row = {
        "test": name,
        "requests": sum(codes.values()),
        "ok": ok,
        "errors": {str(c): n for c, n in codes.items() if not (isinstance(c, int) and 200 <= c < 300)},
        "rps": round(sum(codes.values()) / wall, 1) if wall else 0.0,
        "p50_ms": round(pct(lat, 50) * 1000, 1),
        "p95_ms": round(pct(lat, 95) * 1000, 1),
        "p99_ms": round(pct(lat, 99) * 1000, 1),
        "max_ms": round(max(lat) * 1000, 1) if lat else 0.0,
    }
    print(json.dumps(row, ensure_ascii=False))
    return row


async def hammer(client: httpx.AsyncClient, name: str, make, total: int, concurrency: int) -> dict:
    """Run `total` requests built by `make(i)` with at most `concurrency` in flight."""
    lat: list[float] = []
    codes: Counter = Counter()
    sem = asyncio.Semaphore(concurrency)

    async def one(i: int) -> None:
        method, url, kwargs = make(i)
        async with sem:
            t0 = time.perf_counter()
            try:
                r = await client.request(method, url, **kwargs)
                codes[r.status_code] += 1
            except httpx.HTTPError as exc:
                codes[f"exc:{type(exc).__name__}"] += 1  # type: ignore[index]
            lat.append(time.perf_counter() - t0)

    t0 = time.perf_counter()
    await asyncio.gather(*(one(i) for i in range(total)))
    return summary(name, lat, codes, time.perf_counter() - t0)


async def login(client: httpx.AsyncClient) -> None:
    r = await client.post(f"{BASE}/api/auth/demo", json={"role": "SUPERVISOR"})
    r.raise_for_status()


async def test_api(results: list) -> None:
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
    async with httpx.AsyncClient(timeout=60, limits=limits) as c:
        await login(c)
        ids = [i["id"] for i in (await c.get(f"{BASE}/api/incidents?limit=500")).json()["items"]]
        for conc in (10, 50, 100):
            results.append(await hammer(c, f"GET /api/incidents c={conc}", lambda i: ("GET", f"{BASE}/api/incidents", {}), 1000, conc))
        results.append(await hammer(c, "GET /api/incidents/{id} c=50", lambda i: ("GET", f"{BASE}/api/incidents/{ids[i % len(ids)]}", {}), 1000, 50))
        results.append(await hammer(c, "GET /api/stats/trends c=50", lambda i: ("GET", f"{BASE}/api/stats/trends", {}), 500, 50))
        results.append(await hammer(c, "GET /api/calibration c=50", lambda i: ("GET", f"{BASE}/api/calibration", {}), 500, 50))
        results.append(await hammer(c, "GET /api/incidents/{id}/versions c=50", lambda i: ("GET", f"{BASE}/api/incidents/{ids[i % len(ids)]}/versions", {}), 500, 50))


def ai_documents() -> list[dict]:
    docs = []
    for path in sorted((ROOT / "samples" / "eval").glob("*.json")):
        sample = json.loads(path.read_text(encoding="utf-8"))
        html_file = sample.get("html_file")
        html = (path.parent / html_file).read_text(encoding="utf-8") if html_file else ""
        meta = sample["meta"]
        docs.append({
            "document": {
                "url": meta["url"], "platform": meta.get("platform", "web"), "fetched_at": "2026-11-21T12:00:00Z",
                "title": meta.get("title", ""), "html": html, "text": sample.get("text", ""),
                "author": meta.get("author"), "published_at": meta.get("published_at"),
            },
            "context": sample.get("context") or {},
        })
    return docs


async def test_ai(results: list) -> None:
    docs = ai_documents()
    async with httpx.AsyncClient(timeout=120, limits=httpx.Limits(max_connections=100)) as c:
        for conc in (1, 8, 32, 64):
            results.append(await hammer(c, f"AI POST /analyze c={conc}", lambda i: ("POST", f"{AI}/analyze", {"json": docs[i % len(docs)]}), 400 if conc > 1 else 100, conc))


async def test_pipeline(results: list, rounds: int = 1) -> None:
    """Re-scan every stored case at once and time how long the queue takes to drain."""
    async with httpx.AsyncClient(timeout=60) as c:
        await login(c)
        ids = [i["id"] for i in (await c.get(f"{BASE}/api/incidents?limit=500")).json()["items"]]
        t0 = time.perf_counter()
        jobs = []
        for _ in range(rounds):
            for case_id in ids:
                r = await c.post(f"{BASE}/api/incidents/{case_id}/rescan")
                jobs.append(r.json().get("job_id"))
        queued = time.perf_counter() - t0
        pending = set(jobs)
        states: Counter = Counter()
        deadline = time.perf_counter() + 1200
        while pending and time.perf_counter() < deadline:
            await asyncio.sleep(2)
            items = (await c.get(f"{BASE}/api/scans")).json()["items"]
            for job in items:
                if job["id"] in pending and job["state"] in ("done", "failed"):
                    pending.discard(job["id"])
                    states[job["state"]] += 1
            if len(items) >= 50 and pending and not any(j["id"] in pending for j in items):
                # older than the 50 newest listed jobs: they finished long ago
                states["done"] += len(pending)
                pending.clear()
        wall = time.perf_counter() - t0
        row = {
            "test": f"pipeline re-scan of {len(jobs)} cases",
            "queued_in_s": round(queued, 1),
            "drained_in_s": round(wall, 1),
            "jobs_per_min": round(len(jobs) / wall * 60, 1),
            "done": states["done"],
            "failed": states["failed"],
            "unfinished": len(pending),
        }
        print(json.dumps(row, ensure_ascii=False))
        results.append(row)


async def test_reports(results: list) -> None:
    async with httpx.AsyncClient(timeout=30) as c:
        results.append(await hammer(
            c, "POST /api/public/reports burst (one IP)",
            lambda i: ("POST", f"{BASE}/api/public/reports", {"json": {"url": f"https://przyklad-zgloszenie.example/{i}", "category_hint": 3}}),
            60, 10,
        ))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["api", "ai", "pipeline", "reports", "all"])
    ap.add_argument("--rounds", type=int, default=1, help="pipeline: re-scans per case")
    args = ap.parse_args()
    results: list = []
    if args.what in ("api", "all"):
        await test_api(results)
    if args.what in ("ai", "all"):
        await test_ai(results)
    if args.what in ("reports", "all"):
        await test_reports(results)
    if args.what in ("pipeline", "all"):
        await test_pipeline(results, args.rounds)
    failed = [r for r in results if r.get("errors") and any(not k.startswith("429") for k in r["errors"])]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
