"""Run the engine over sample files (the "pendrive" format) and print scores.

Usage:
    python scripts/run_eval.py                      # cases + calibration set summary
    python scripts/run_eval.py --dir ../../samples/cases --verbose

It builds the same `Document` the backend scraper would send to POST /analyze, so the
numbers equal what the full pipeline produces.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.engine import Engine  # noqa: E402
from app.schemas import AnalyzeRequest  # noqa: E402

SAMPLES = ROOT.parent.parent / "samples"
FETCHED_AT = "2026-11-21T12:00:00Z"


def load_sample(path: Path, fetched_at: str = FETCHED_AT) -> dict:
    """Sample JSON -> {"document": ..., "context": ...} request body."""
    sample = json.loads(path.read_text(encoding="utf-8"))
    meta = sample.get("meta", {})
    html = ""
    if sample.get("html_file"):
        html = (path.parent / sample["html_file"]).read_text(encoding="utf-8")
    document = {
        "url": meta.get("url", f"file://{path.name}"),
        "platform": meta.get("platform", "sample"),
        "fetched_at": fetched_at,
        "http_status": 200,
        "title": meta.get("title", ""),
        "html": html,
        "text": sample.get("text", ""),
        "published_at": meta.get("published_at"),
        "author": meta.get("author"),
        "fetch": {"engine": "file", "user_agent": "investwatch-eval", "proxy": None},
        "archive": {"html_key": None, "screenshot_key": None},
    }
    return {"document": document, "context": sample.get("context", {})}


async def analyze_file(engine: Engine, path: Path):
    request = AnalyzeRequest.model_validate(load_sample(path))
    return await engine.analyze(request.document, request.context)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, action="append")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--threshold", type=float, default=35.0)
    ap.add_argument("--only", action="append", help="only samples whose file name contains this text")
    args = ap.parse_args()
    engine = Engine(load_settings())
    dirs = args.dir or [SAMPLES / "cases", SAMPLES / "eval"]
    by_label: dict[str, list[float]] = {"violation": [], "ok": []}
    for directory in dirs:
        for path in sorted(directory.glob("*.json")):
            if args.only and not any(o in path.name for o in args.only):
                continue
            a = await analyze_file(engine, path)
            failed = ",".join(r.id for r in a.rules if r.status == "fail")
            label = a.ground_truth or "-"
            print(
                f"{path.stem:44s} risk={a.risk_score:5.1f} compl={a.compliance_score:5.1f} {a.risk_level:6s} "
                f"gt={label:9s} M{a.primary_module} {a.recommendation.action:8s} fail=[{failed}] "
                f"{a.engine.duration_ms:.0f}ms"
            )
            if a.ground_truth:
                by_label[a.ground_truth].append(a.risk_score)
            if args.verbose:
                for m in a.module_results:
                    print(f"    {m.plugin}: score={m.score} w={m.weight}")
                for c in a.debate.claims:
                    print(f"    [{c.stance:7s} {c.verdict:8s} {c.confidence:.2f}] {c.text[:110]}")
                for r in a.rules:
                    print(f"    rule {r.id:>3s} {r.status:7s} {r.confidence:.2f} {r.explanation[:100]}")
    if any(by_label.values()):
        t = args.threshold
        print("\nCalibration set (risk_score):")
        for label, scores in by_label.items():
            if scores:
                q = statistics.quantiles(scores, n=4) if len(scores) >= 4 else scores
                print(
                    f"  {label:9s} n={len(scores):2d} min={min(scores):5.1f} q1={q[0]:5.1f} "
                    f"median={statistics.median(scores):5.1f} q3={q[-1]:5.1f} max={max(scores):5.1f}"
                )
        tp = sum(s >= t for s in by_label["violation"])
        fn = len(by_label["violation"]) - tp
        fp = sum(s >= t for s in by_label["ok"])
        tn = len(by_label["ok"]) - fp
        print(f"  threshold {t:.0f}: TP={tp} FN={fn} FP={fp} TN={tn}")


if __name__ == "__main__":
    asyncio.run(main())
