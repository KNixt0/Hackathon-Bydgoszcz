"""Incident persistence helpers: Analysis -> row, row -> Incident / IncidentSummary."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Incident, IncidentVersion, utcnow
from app.schemas import PLATFORMS, iso

MAX_VERSIONS = 20


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def _party_name(payload: dict, key: str) -> str | None:
    party = (payload.get("entities") or {}).get(key)
    return party.get("name") if isinstance(party, dict) else None


def to_incident(row: Incident) -> dict[str, Any]:
    return {
        **row.payload,
        "id": row.id,
        "status": row.status,
        "created_at": iso(row.created_at),
        "updated_at": iso(row.updated_at),
    }


def to_summary(row: Incident) -> dict[str, Any]:
    p = row.payload
    source = p.get("source") or {}
    return {
        "id": row.id,
        "title": p.get("title", ""),
        "summary": p.get("summary", ""),
        "modules": p.get("modules") or [row.primary_module],
        "primary_module": row.primary_module,
        "risk_score": row.risk_score,
        "compliance_score": p.get("compliance_score", round(100 - row.risk_score, 2)),
        "risk_level": p.get("risk_level") or level_for(row.risk_score),
        "status": row.status,
        "created_at": iso(row.created_at),
        "updated_at": iso(row.updated_at),
        "synthetic": bool(p.get("synthetic", False)),
        "ground_truth": row.ground_truth,
        "demo_case": row.demo_case,
        "source": {
            "platform": source.get("platform", row.platform),
            "url": source.get("url", row.source_url),
        },
        "advertiser": _party_name(p, "advertiser"),
        "firm": _party_name(p, "investment_firm"),
        "failed_rules": [str(r.get("id")) for r in p.get("rules") or [] if r.get("status") == "fail"],
    }


def level_for(score: float, t_red: float = 70, t_orange: float = 35) -> str:
    return "red" if score >= t_red else "orange" if score >= t_orange else "green"


def _search_text(payload: dict) -> str:
    source = payload.get("source") or {}
    parts = [
        payload.get("title"),
        payload.get("summary"),
        _party_name(payload, "advertiser"),
        _party_name(payload, "investment_firm"),
        source.get("url"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def apply_payload(row: Incident, payload: dict) -> None:
    """Mirror the Analysis into the indexed columns."""
    source = payload.get("source") or {}
    modules = [m for m in payload.get("modules") or [] if m in (1, 2, 3)]
    primary = int(payload["primary_module"])
    platform = source.get("platform")
    row.payload = payload
    row.risk_score = float(payload["risk_score"])
    row.primary_module = primary
    row.modules_mask = sum(1 << (m - 1) for m in {*modules, primary})
    row.platform = platform if platform in PLATFORMS else "web"
    row.ground_truth = payload.get("ground_truth")
    row.demo_case = payload.get("demo_case")
    row.content_hash = str(source.get("content_hash") or "")
    row.source_url = str(source.get("url") or "")
    row.source_url_hash = url_hash(row.source_url)
    row.synthetic = bool(payload.get("synthetic", False))
    row.search_text = _search_text(payload)


def upsert_incident(
    db: Session,
    payload: dict,
    *,
    created_at: datetime | None,
    origin: str,
    fetch_url: str,
    render: bool,
    module_hint: int | None,
    meta: dict | None = None,
    context: dict | None = None,
) -> tuple[Incident, bool]:
    """Store an Analysis. Same source url -> update in place (keeps id, status, created_at) and
    record a version; `changed` on the version says whether the content hash moved (the diff)."""
    source_url = str((payload.get("source") or {}).get("url") or "")
    now = utcnow()
    row = (
        db.query(Incident)
        .filter(Incident.source_url_hash == url_hash(source_url), Incident.source_url == source_url)
        .order_by(Incident.created_at.desc())
        .first()
    )
    created = row is None
    previous_hash = None if row is None else row.content_hash
    if row is None:
        row = Incident(status="new", created_at=created_at or now)
        db.add(row)
    apply_payload(row, payload)
    row.updated_at = row.created_at if created else now
    row.origin, row.fetch_url, row.render, row.module_hint = origin, fetch_url, render, module_hint
    row.scan_meta, row.scan_context = meta or None, context or None
    db.flush()
    db.add(
        IncidentVersion(
            incident_id=row.id,
            content_hash=row.content_hash,
            risk_score=row.risk_score,
            changed=(not created) and previous_hash != row.content_hash,
            created_at=now,
        )
    )
    db.flush()
    stale = (
        db.query(IncidentVersion)
        .filter(IncidentVersion.incident_id == row.id)
        .order_by(IncidentVersion.id.desc())
        .offset(MAX_VERSIONS)
        .all()
    )
    for version in stale:
        db.delete(version)
    return row, created


def delete_incident(db: Session, row: Incident) -> None:
    db.query(IncidentVersion).filter(IncidentVersion.incident_id == row.id).delete()
    db.delete(row)


def rescan_options(row: Incident) -> dict:
    """create_job() arguments that fetch this incident's source again exactly like the first time."""
    meta = {k: v for k, v in (row.scan_meta or {}).items() if k != "detected_days_ago"}
    return {
        "fetch_url": row.fetch_url or row.source_url,
        "origin": row.origin,
        "render": row.render,
        "module_hint": row.module_hint,
        "meta": meta,
        "context": row.scan_context or {},
    }
