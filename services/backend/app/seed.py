"""Offline demo seed: push every sample (meta.seed != false) through the real pipeline.

python -m app.seed [--force]
"""

from __future__ import annotations

import argparse
import logging

from app.config import get_settings
from app.db import init_db, session_scope
from app.jobs import create_sample_job, dispatch
from app.log import setup_logging
from app.models import Incident, ScanJob
from app.samples import discover

log = logging.getLogger(__name__)


def import_samples(subdir: str | None = None, include_unseeded: bool = False) -> list[str]:
    """Queue the samples under SAMPLES_DIR[/subdir]. Returns the job ids."""
    samples = [s for s in discover(subdir) if include_unseeded or s.seed]
    job_ids = [create_sample_job(sample) for sample in samples]
    for job_id in job_ids:
        dispatch(job_id)
    return job_ids


def seed_if_empty(force: bool = False) -> list[str]:
    """Seed only a fresh database (no incidents and no jobs yet), unless forced."""
    if not force:
        with session_scope() as db:
            if db.query(Incident.id).first() or db.query(ScanJob.id).first():
                return []
    job_ids = import_samples()
    log.info("seed queued", extra={"jobs": len(job_ids)})
    return job_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed #InvestWatch with the samples in SAMPLES_DIR")
    parser.add_argument("--force", action="store_true", help="seed even if the database is not empty")
    args = parser.parse_args()
    setup_logging(get_settings().log_level)
    init_db()
    job_ids = seed_if_empty(force=args.force)
    print(f"queued {len(job_ids)} sample(s)")  # noqa: T201


if __name__ == "__main__":
    main()
