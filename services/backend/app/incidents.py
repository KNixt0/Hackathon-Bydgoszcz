"""Incident persistence helpers: Analysis -> row, row -> Incident / IncidentSummary."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
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


def workflow_dict(row: Incident) -> dict[str, Any]:
    """Contract v3 `Workflow`."""
    return {
        "assigned_to": row.assigned_to,
        "escalation_path": row.escalation_path,
        "resolution_action": row.resolution_action,
        "resolution_note": row.resolution_note or "",
        "label": row.label or "unlabeled",
    }


def _priority(row: Incident) -> float:
    if row.priority_score is not None:
        return row.priority_score
    from app.public_reports import priority_score

    return priority_score(row.risk_score, row.user_reports_count)


def observation_dict(row: Incident) -> dict[str, Any]:
    """Contract v4 `Observation`: publication, detection and the latest check are three different facts."""
    return {
        "published_at": row.published_at or (row.payload.get("source") or {}).get("published_at"),
        "detected_at": iso(row.created_at),
        "evidence_version_id": row.evidence_version_id,
        "content_state": row.content_state or "online",
        "last_checked_at": iso(row.last_checked_at or row.updated_at),
    }


def follow_up_dict(row: Incident) -> dict[str, Any] | None:
    if row.intervention_at is None:
        return None
    return {
        "intervention_at": iso(row.intervention_at),
        "note": row.intervention_note or "",
        "due": iso(row.follow_up_due),
        "outcome": row.follow_up_outcome,
    }


def to_incident(row: Incident) -> dict[str, Any]:
    return {
        **row.payload,
        "id": row.id,
        "status": row.status,
        "created_at": iso(row.created_at),
        "updated_at": iso(row.updated_at),
        "workflow": workflow_dict(row),
        "user_reports_count": row.user_reports_count or 0,
        "priority_score": _priority(row),
        "observation": observation_dict(row),
        "follow_up": follow_up_dict(row),
        "previous_incident_id": row.previous_incident_id,
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
        "workflow": {"assigned_to": row.assigned_to, "label": row.label or "unlabeled"},
        "user_reports_count": row.user_reports_count or 0,
        "priority_score": _priority(row),
        "in_scope": _in_scope(row),
        "content_state": row.content_state or "online",
        "follow_up": {"due": iso(row.follow_up_due), "outcome": row.follow_up_outcome}
        if row.intervention_at
        else None,
    }


def _in_scope(row: Incident) -> bool | None:
    if row.in_scope is not None:
        return row.in_scope
    scope = row.payload.get("scope")
    return scope.get("in_scope") if isinstance(scope, dict) else None


def level_for(score: float, t_red: float = 70, t_orange: float = 20) -> str:
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
    from app.public_reports import normalized_hash, priority_score

    row.norm_url_hash = normalized_hash(row.source_url)
    row.priority_score = priority_score(row.risk_score, row.user_reports_count)  # risk moved: recompute
    row.published_at = source.get("published_at") or row.published_at
    scope = payload.get("scope")
    row.in_scope = scope.get("in_scope") if isinstance(scope, dict) else None


CLOSED = {"resolved", "false_positive"}


def _latest_case(db: Session, source_url: str) -> Incident | None:
    return (
        db.query(Incident)
        .filter(Incident.source_url_hash == url_hash(source_url), Incident.source_url == source_url)
        .order_by(Incident.created_at.desc())
        .first()
    )


def _prune(db: Session, row: Incident) -> None:
    """Keep the newest MAX_VERSIONS observations, never the evidence (the frozen detection)."""
    stale = (
        db.query(IncidentVersion)
        .filter(IncidentVersion.incident_id == row.id)
        .order_by(IncidentVersion.id.desc())
        .offset(MAX_VERSIONS)
        .all()
    )
    for version in stale:
        if version.id != row.evidence_version_id:
            db.delete(version)


def _add_version(db: Session, row: Incident, **fields: Any) -> IncidentVersion:
    version = IncidentVersion(incident_id=row.id, created_at=utcnow(), **fields)
    db.add(version)
    db.flush()
    return version


def _follow_up(row: Incident, outcome: str) -> None:
    """While a case awaits correction, every check updates the outcome the analyst sees."""
    if row.status == "awaiting_correction":
        row.follow_up_outcome = outcome


@dataclass
class Stored:
    row: Incident
    created: bool  # a new case row (first detection, or a recurrence after closure)
    detected: bool  # this observation became the case's evidence (alert-worthy)
    evidence_kept: bool  # the case already had evidence: the new analysis did not overwrite it


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
    job_id: str | None = None,
    flag_threshold: float = 20.0,
) -> tuple[Incident, bool]:
    stored = store_observation(
        db,
        payload,
        created_at=created_at,
        origin=origin,
        fetch_url=fetch_url,
        render=render,
        module_hint=module_hint,
        meta=meta,
        context=context,
        job_id=job_id,
        flag_threshold=flag_threshold,
    )
    return stored.row, stored.created


def store_observation(
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
    job_id: str | None = None,
    flag_threshold: float = 20.0,
) -> Stored:
    """Store one observation of a source (contract v4: detection is not the post, nor a later check).

    - A source seen for the first time becomes a case; if its score reaches the flag threshold the
      observation is the case's evidence (`evidence_version_id`) and is frozen.
    - Later observations are appended. A case that has evidence keeps its payload (quotes, rules,
      archive keys of the detection): a corrected page never erases what was detected. Its
      `content_state` becomes `changed` / `online`, and a pending follow-up records the outcome.
    - A case without evidence (never flagged) is simply updated; if it now reaches the threshold,
      this observation becomes its evidence (a new detection).
    - A closed case whose content changed and is flagged again opens a new case linked to it.
    """
    source = payload.get("source") or {}
    source_url = str(source.get("url") or "")
    now = utcnow()
    score = float(payload["risk_score"])
    flagged = score >= flag_threshold
    row = _latest_case(db, source_url)
    previous_hash = None if row is None else row.content_hash
    new_hash = str(source.get("content_hash") or "")
    changed = row is not None and previous_hash != new_hash
    published = source.get("published_at")

    recurrence = row is not None and row.status in CLOSED and changed and flagged
    if row is None or recurrence:
        previous_id = row.id if recurrence else None
        row = Incident(status="new", created_at=created_at or now)
        db.add(row)
        apply_payload(row, payload)
        row.previous_incident_id = previous_id
        row.updated_at = row.created_at
        row.content_state, row.last_checked_at = "online", now
        _set_fetch(row, origin, fetch_url, render, module_hint, meta, context)
        db.flush()
        version = _add_version(
            db, row, content_hash=row.content_hash, risk_score=score, changed=False, outcome="content",
            http_status=200, job_id=job_id, published_at=published, payload=payload,
        )  # fmt: skip
        row.evidence_version_id = version.id if flagged else None
        return Stored(row, created=True, detected=flagged, evidence_kept=False)

    has_evidence = row.evidence_version_id is not None
    version = _add_version(
        db, row, content_hash=new_hash, risk_score=score, changed=changed, outcome="content", http_status=200,
        job_id=job_id, published_at=published, payload=payload if (changed or not has_evidence) else None,
    )  # fmt: skip
    detected = False
    if has_evidence:
        row.content_state = "changed" if new_hash != _evidence_hash(db, row) else "online"
        if row.status == "awaiting_correction":
            _follow_up(row, "persisting" if flagged or not changed else "corrected")
    else:
        apply_payload(row, payload)  # nothing to preserve yet
        _set_fetch(row, origin, fetch_url, render, module_hint, meta, context)
        row.content_state = "changed" if changed else "online"
        if flagged:
            row.evidence_version_id, detected = version.id, True
    row.published_at = row.published_at or published  # learnt later (e.g. a parser that now finds it)
    row.last_checked_at = now
    row.updated_at = now
    _prune(db, row)
    return Stored(row, created=False, detected=detected, evidence_kept=has_evidence)


def _evidence_hash(db: Session, row: Incident) -> str:
    version = db.get(IncidentVersion, row.evidence_version_id) if row.evidence_version_id else None
    return version.content_hash if version else row.content_hash


def _set_fetch(row, origin, fetch_url, render, module_hint, meta, context) -> None:
    row.origin, row.fetch_url, row.render, row.module_hint = origin, fetch_url, render, module_hint
    row.scan_meta, row.scan_context = meta or None, context or None


def record_unavailable(
    db: Session, source_url: str, http_status: int | None, job_id: str | None
) -> Incident | None:
    """A known source answered 404/410 (removed) or could not be fetched (unreachable).

    Recorded as an observation of the existing case instead of a failed job, so that removal after an
    intervention is visible. Returns None when no case exists for the URL.
    """
    row = _latest_case(db, source_url)
    if row is None:
        return None
    outcome = "removed" if http_status in (404, 410) else "unreachable"
    _add_version(
        db, row, content_hash=row.content_hash, risk_score=row.risk_score, changed=outcome == "removed",
        outcome=outcome, http_status=http_status, job_id=job_id,
    )  # fmt: skip
    row.content_state = outcome
    if outcome == "removed":
        _follow_up(row, "removed")
    row.last_checked_at = row.updated_at = utcnow()
    _prune(db, row)
    return row


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
