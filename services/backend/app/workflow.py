"""Case workflow (contract v3): allowed transitions, role checks, required reasons, side effects.

new → in_review · in_review → escalation_requested | awaiting_correction | resolved | false_positive ·
escalation_requested → escalated (SUPERVISOR) | in_review ·
escalated → awaiting_correction | resolved | false_positive ·
awaiting_correction → resolved | in_review | escalation_requested   (contract v4: follow-up)

The system detects and reports. `awaiting_correction` records that UKNF intervened (the analyst
describes how, outside this tool) and schedules a re-check of the source; the outcome of each
re-check (removed / corrected / persisting) is written by the pipeline, the analyst closes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app import audit
from app.incidents import url_hash, workflow_dict
from app.models import Incident, WatchlistItem, utcnow

TRANSITIONS: dict[str, tuple[str, ...]] = {
    "new": ("in_review",),
    "in_review": ("escalation_requested", "awaiting_correction", "resolved", "false_positive"),
    "escalation_requested": ("escalated", "in_review"),
    "escalated": ("awaiting_correction", "resolved", "false_positive"),
    "awaiting_correction": ("resolved", "in_review", "escalation_requested"),
    "resolved": (),
    "false_positive": (),
}
SUPERVISOR_ONLY = {("escalation_requested", "escalated")}
REASON_REQUIRED = {"resolved", "false_positive", "awaiting_correction"}
CLOSED = {"resolved", "false_positive"}
DEFAULT_ESCALATION_PATH = {1: "THIRD_PARTY_ADVERTISING", 2: "RISK_INFORMATION", 3: "UNLICENSED_ACTIVITY"}
MONITORING_INTERVAL_HOURS = 6.0
DEFAULT_FOLLOW_UP_DAYS = 14


class WorkflowError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class TransitionInput:
    to: str
    reason: str | None = None
    escalation_path: str | None = None
    resolution_action: str | None = None
    follow_up_days: int | None = None


def _snapshot(row: Incident) -> dict:
    return {
        "status": row.status,
        **workflow_dict(row),
        "intervention_note": row.intervention_note,
        "follow_up_due": row.follow_up_due.isoformat() if row.follow_up_due else None,
    }


def _changed(before: dict, after: dict) -> tuple[dict, dict]:
    keys = [k for k in after if before.get(k) != after.get(k)]
    return {k: before.get(k) for k in keys}, {k: after.get(k) for k in keys}


def assign(db: Session, row: Incident, actor: Any) -> None:
    if row.status in CLOSED:
        raise WorkflowError(409, "a closed case cannot be reassigned")
    previous = row.assigned_to
    row.assigned_to = actor.email
    row.updated_at = utcnow()
    row.review_started_at = row.review_started_at or row.updated_at  # taking the case starts the work
    audit.record(
        db,
        actor,
        "assign",
        incident_id=row.id,
        previous={"assigned_to": previous},
        new={"assigned_to": actor.email},
    )


def set_label(db: Session, row: Incident, actor: Any, label: str) -> None:
    previous = row.label or "unlabeled"
    row.label = None if label == "unlabeled" else label
    row.updated_at = utcnow()
    audit.record(db, actor, "label", incident_id=row.id, previous={"label": previous}, new={"label": label})


def _watch(db: Session, row: Incident) -> None:
    url = row.source_url
    if urlsplit(url).scheme not in ("http", "https"):
        raise WorkflowError(422, "the case has no http(s) source to monitor")
    item = db.query(WatchlistItem).filter(WatchlistItem.url_hash == url_hash(url)).first()
    if item is None:
        item = WatchlistItem(url=url, url_hash=url_hash(url), module_hint=row.module_hint, render=row.render)
        db.add(item)
    item.interval_hours = MONITORING_INTERVAL_HOURS


def _unwatch(db: Session, row: Incident) -> None:
    db.query(WatchlistItem).filter(WatchlistItem.url_hash == url_hash(row.source_url)).delete()


def transition(db: Session, row: Incident, actor: Any, body: TransitionInput) -> None:
    """Validates (409 edge, 403 role, 422 payload), applies, and writes one audit row."""
    current, target = row.status, body.to
    if target not in TRANSITIONS.get(current, ()):
        raise WorkflowError(409, f"transition {current} -> {target} is not allowed")
    if (current, target) in SUPERVISOR_ONLY and actor.role != "SUPERVISOR":
        raise WorkflowError(403, "only a supervisor can approve an escalation")
    reason = (body.reason or "").strip() or None
    if target in REASON_REQUIRED and reason is None:
        raise WorkflowError(422, f"a reason is required to move the case to {target}")
    if body.escalation_path is not None and target not in ("escalation_requested", "escalated"):
        raise WorkflowError(422, "escalation_path only applies to escalation_requested or escalated")
    action = body.resolution_action
    if action is not None and target not in CLOSED:
        raise WorkflowError(422, "resolution_action only applies to resolved or false_positive")
    if target == "false_positive" and action not in (None, "false_positive"):
        raise WorkflowError(422, "a false positive is closed with resolution_action false_positive")
    if target == "resolved" and action == "false_positive":
        raise WorkflowError(422, "use the false_positive status for a false positive")
    if body.follow_up_days is not None and target != "awaiting_correction":
        raise WorkflowError(422, "follow_up_days only applies to awaiting_correction")

    before = _snapshot(row)
    row.status = target
    if target == "in_review":
        if current == "new" and row.assigned_to is None:
            row.assigned_to = actor.email  # starting the review takes the case
        if current == "escalation_requested":
            row.escalation_path = None
    elif target == "escalation_requested":
        row.escalation_path = body.escalation_path or DEFAULT_ESCALATION_PATH.get(
            row.primary_module, "RISK_INFORMATION"
        )
    elif target == "escalated":
        if body.escalation_path:
            row.escalation_path = body.escalation_path
    elif target == "false_positive":
        row.resolution_action = "false_positive"
        row.resolution_note = reason
        row.label = "false_positive"
    elif target == "awaiting_correction":
        now = utcnow()
        row.intervention_at = now
        row.intervention_note = reason
        row.follow_up_due = now + timedelta(days=body.follow_up_days or DEFAULT_FOLLOW_UP_DAYS)
        row.follow_up_outcome = None
        _watch(db, row)  # re-checked by the scheduler until the case is closed
    elif target == "resolved":
        row.resolution_action = action or "evidence_report"
        row.resolution_note = reason
    if target in CLOSED and row.intervention_at is not None:
        _unwatch(db, row)  # the follow-up ends with the case
    now = utcnow()
    if row.review_started_at is None and target != "new":
        row.review_started_at = now
    row.closed_at = now if target in CLOSED else None
    row.updated_at = utcnow()
    previous, new = _changed(before, _snapshot(row))
    previous["status"], new["status"] = current, target
    audit.record(db, actor, "transition", incident_id=row.id, previous=previous, new=new, reason=reason)
