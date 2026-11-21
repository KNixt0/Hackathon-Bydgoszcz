"""Public reports: URL normalisation, reporter hashing, limits, priority score and report linking.

Privacy: the client IP is only ever used as input of a salted HMAC (`reporter_hash`) that limits
abuse. Nothing else about the browser is read (no fingerprinting).
"""

from __future__ import annotations

import hashlib
import hmac
import math
import threading
import time
from collections import defaultdict, deque
from types import SimpleNamespace
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session

from app import audit
from app.config import get_settings
from app.incidents import url_hash
from app.models import Incident, ScanJob, UserReport

MAX_URL_LENGTH = 2048
MAX_COMMENT_LENGTH = 500
DAY_SECONDS = 24 * 3600
ACTIVE_JOB_STATES = ("queued", "scraping", "analyzing")

# Query parameters that only track the click, never identify the resource.
TRACKING_PARAMS = frozenset(
    {
        "fbclid", "gclid", "dclid", "gbraid", "wbraid", "msclkid", "yclid", "twclid", "ttclid",
        "mc_eid", "mc_cid", "igshid", "igsh", "si", "_hsenc", "_hsmi", "mkt_tok", "vero_id",
        "oly_enc_id", "oly_anon_id", "_ga", "_gl", "s_cid", "spm",
    }
)  # fmt: skip
TRACKING_PREFIXES = ("utm_",)

PUBLIC_ACTOR = SimpleNamespace(email="public", role="PUBLIC")


class InvalidReportURL(ValueError):
    pass


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES)


def normalize_url(raw: str) -> str:
    """Canonical form used to recognise the same page: lower-case scheme and host, default port and
    fragment dropped, tracking parameters removed, remaining parameters sorted."""
    try:
        parts = urlsplit(raw.strip())
        port = parts.port
    except ValueError as exc:
        raise InvalidReportURL("invalid url") from exc
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise InvalidReportURL("only http and https urls are allowed")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise InvalidReportURL("url has no host")
    if parts.username or parts.password:
        raise InvalidReportURL("credentials in url are not allowed")
    if ":" in host:
        host = f"[{host}]"
    if port and not (port == 80 and scheme == "http") and not (port == 443 and scheme == "https"):
        host = f"{host}:{port}"
    pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k)]
    query = urlencode(sorted(pairs), quote_via=quote)
    return urlunsplit((scheme, host, parts.path or "/", query, ""))


def normalized_hash(url: str) -> str:
    """sha256 of the normalised URL (falls back to the stripped text for odd stored URLs)."""
    try:
        return url_hash(normalize_url(url))
    except InvalidReportURL:
        return url_hash(url)


def priority_score(risk_score: float, reports: int | None) -> float:
    """contract v3: min(100, risk * (1 + 0.25 * log2(1 + reports)))."""
    return round(min(100.0, float(risk_score) * (1 + 0.25 * math.log2(1 + max(0, reports or 0)))), 2)


def reporter_hash(ip: str) -> str:
    settings = get_settings()
    salt = settings.public_reports_salt.strip()
    if not salt:
        from app.auth.tokens import get_secret

        salt = get_secret()
    key = hashlib.sha256(f"public-reports:{salt}".encode()).digest()
    return hmac.new(key, ip.encode("utf-8"), hashlib.sha256).hexdigest()


class ReportThrottle:
    """Reports per reporter in a sliding hour (in-memory, per API process like the login throttle)."""

    WINDOW = 3600.0

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, reporter: str) -> int:
        """Record an attempt. Returns 0 when allowed, else the seconds to wait."""
        limit = get_settings().public_reports_per_hour
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[reporter]
            while bucket and bucket[0] <= now - self.WINDOW:
                bucket.popleft()
            if len(bucket) >= limit:
                return int(bucket[0] + self.WINDOW - now) + 1
            bucket.append(now)
            if len(self._hits) > 10_000:  # forget idle reporters
                for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - self.WINDOW]:
                    self._hits.pop(key, None)
            return 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


report_throttle = ReportThrottle()


def queued_report_scans(db: Session) -> int:
    """Scans started by reports that have not finished yet (the cap PUBLIC_REPORTS_MAX_QUEUED)."""
    return (
        db.query(UserReport.job_id)
        .join(ScanJob, ScanJob.id == UserReport.job_id)
        .filter(UserReport.incident_id.is_(None), ScanJob.state.in_(ACTIVE_JOB_STATES))
        .distinct()
        .count()
    )


def active_pending_job(db: Session, hash_: str) -> str | None:
    """A scan already running for this URL because of an earlier report."""
    row = (
        db.query(UserReport.job_id)
        .join(ScanJob, ScanJob.id == UserReport.job_id)
        .filter(
            UserReport.url_hash == hash_,
            UserReport.incident_id.is_(None),
            ScanJob.state.in_(ACTIVE_JOB_STATES),
        )
        .first()
    )
    return row[0] if row else None


def find_incident(db: Session, hash_: str) -> Incident | None:
    return (
        db.query(Incident)
        .filter(Incident.norm_url_hash == hash_)
        .order_by(Incident.created_at.desc(), Incident.id)
        .first()
    )


def is_viral(count: int, risk_score: float, critical: float) -> bool:
    return count >= get_settings().public_reports_viral_threshold and risk_score >= critical


def crossed_viral(old: int, new: int) -> bool:
    n = get_settings().public_reports_viral_threshold
    return old < n <= new


def set_count(db: Session, row: Incident, count: int, *, audit_change: bool = True) -> None:
    """Set the report count, recompute the priority and leave an audit row (no personal data)."""
    before = {"user_reports_count": row.user_reports_count or 0, "priority_score": row.priority_score}
    row.user_reports_count = count
    row.priority_score = priority_score(row.risk_score, count)
    if audit_change:
        audit.record(
            db,
            PUBLIC_ACTOR,
            "public_report",
            incident_id=row.id,
            previous=before,
            new={"user_reports_count": count, "priority_score": row.priority_score},
        )


def link_pending(db: Session, row: Incident, job_id: str | None = None) -> tuple[int, int] | None:
    """After a scan stored `row`: attach the reports waiting for it and count them.
    Returns (old_count, new_count) when something was linked."""
    query = db.query(UserReport).filter(UserReport.incident_id.is_(None))
    if job_id:
        from sqlalchemy import or_

        query = query.filter(or_(UserReport.url_hash == row.norm_url_hash, UserReport.job_id == job_id))
    else:
        query = query.filter(UserReport.url_hash == row.norm_url_hash)
    pending = query.all()
    if not pending:
        return None
    for report in pending:
        report.incident_id = row.id
    old = row.user_reports_count or 0
    set_count(db, row, old + len(pending))
    return old, old + len(pending)
