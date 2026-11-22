"""Incidents: list/filter, detail, workflow, history, stats, calibration, exports."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Query as SAQuery
from sqlalchemy.orm import Session

from app import audit, events
from app.auth import Actor
from app.config import get_settings
from app.date_bounds import check_bound, window
from app.db import get_db, session_scope
from app.exports import csv_export
from app.incidents import rescan_options, to_incident, to_summary
from app.jobs import create_job, dispatch
from app.models import Incident, IncidentVersion, UserReport, utcnow
from app.schemas import PLATFORMS, STATUSES, LabelRequest, StatusPatch, TransitionRequest, iso
from app.workflow import TransitionInput, WorkflowError, set_label, transition
from app.workflow import assign as assign_case

router = APIRouter(prefix="/api", tags=["incidents"])
Db = Annotated[Session, Depends(get_db)]


def _parse_bound(value: str | None, name: str, end: bool) -> datetime | None:
    """ISO date or datetime. A bare date as `to` covers that whole day."""
    if value is None or value == "":
        return None
    try:
        if len(value) <= 10:
            day = date.fromisoformat(value)
            moment = datetime.combine(day, time.min, tzinfo=UTC)
            return moment + timedelta(days=1) if end else moment
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(422, f"'{name}' must be an ISO date (YYYY-MM-DD) or datetime") from exc
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


class IncidentFilters:
    def __init__(
        self,
        module: Annotated[int | None, Query(ge=1, le=3)] = None,
        source: Annotated[str | None, Query(max_length=32)] = None,
        status: Annotated[str | None, Query(max_length=32)] = None,
        from_: Annotated[str | None, Query(alias="from", max_length=40)] = None,
        to: Annotated[str | None, Query(max_length=40)] = None,
        q: Annotated[str | None, Query(max_length=200)] = None,
        sort: Annotated[str, Query(max_length=16)] = "risk",
        min_reports: Annotated[int, Query(ge=0, le=100000)] = 0,
    ) -> None:
        if sort not in ("risk", "priority"):
            raise HTTPException(422, "'sort' must be one of: risk, priority")
        self.sort, self.min_reports = sort, min_reports
        if source is not None and source not in PLATFORMS:
            raise HTTPException(422, f"'source' must be one of: {', '.join(PLATFORMS)}")
        if status is not None and status not in STATUSES:
            raise HTTPException(422, f"'status' must be one of: {', '.join(STATUSES)}")
        self.module, self.source, self.status, self.q = module, source, status, q
        self.start = _parse_bound(from_, "from", end=False)
        self.end = _parse_bound(to, "to", end=True)
        check_bound(from_, self.start, lower=True)
        check_bound(to, self.end, lower=False)
        self.end_inclusive = bool(to) and len(to or "") > 10

    def apply(self, query: SAQuery) -> SAQuery:
        # WatchIt analyses only entities under UKNF's remit: material outside it is not listed or counted
        query = query.filter(or_(Incident.in_scope.is_(None), Incident.in_scope.is_(True)))
        if self.module is not None:
            # an incident shows under every module that produced findings, not only the primary one
            query = query.filter(Incident.modules_mask.bitwise_and(1 << (self.module - 1)) != 0)
        if self.source:
            query = query.filter(Incident.platform == self.source)
        if self.status:
            query = query.filter(Incident.status == self.status)
        if self.start:
            query = query.filter(Incident.created_at >= self.start)
        if self.end:
            query = query.filter(
                Incident.created_at <= self.end if self.end_inclusive else Incident.created_at < self.end
            )
        if self.min_reports:
            query = query.filter(func.coalesce(Incident.user_reports_count, 0) >= self.min_reports)
        if self.q and self.q.strip():
            needle = self.q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(Incident.search_text.like(f"%{needle}%", escape="\\"))
        return query


def _ordered(query: SAQuery, sort: str = "risk") -> SAQuery:
    if sort == "priority":
        return query.order_by(
            func.coalesce(Incident.priority_score, Incident.risk_score).desc(),
            Incident.risk_score.desc(),
            Incident.created_at.desc(),
            Incident.id,
        )
    return query.order_by(Incident.risk_score.desc(), Incident.created_at.desc(), Incident.id)


def _get_or_404(db: Session, incident_id: str) -> Incident:
    row = db.get(Incident, incident_id) if len(incident_id) <= 36 else None
    if row is None:
        raise HTTPException(404, "incident not found")
    return row


@router.get("/incidents")
def list_incidents(
    db: Db,
    filters: Annotated[IncidentFilters, Depends()],
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    query = filters.apply(db.query(Incident))
    total = query.count()
    rows = _ordered(query, filters.sort).offset(offset).limit(limit).all()
    return {"items": [to_summary(row) for row in rows], "total": total}


# declared before /incidents/{incident_id} so "export.csv" is not taken for an id
@router.get("/incidents/export.csv")
def export_list_csv(db: Db, user: Actor, filters: Annotated[IncidentFilters, Depends()]) -> Response:
    rows = _ordered(filters.apply(db.query(Incident)), filters.sort).limit(5000).all()
    body = csv_export.incidents_csv(to_summary(row) for row in rows)
    audit.record(db, user, "export", new={"format": "csv", "scope": "list", "rows": len(rows)})
    return _csv_response(body, f"investwatch-incydenty-{utcnow():%Y%m%d}.csv")


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, db: Db) -> dict:
    return to_incident(_get_or_404(db, incident_id))


def _commit_and_announce(db: Session, row: Incident) -> dict:
    """The change and its audit row commit together; clients hear about it only afterwards."""
    db.commit()
    events.emit("incident:updated", to_summary(row))
    return to_incident(row)


def _workflow(fn: Callable[..., None], *args: object) -> None:
    try:
        fn(*args)
    except WorkflowError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/incidents/{incident_id}/transition")
def transition_incident(incident_id: str, body: TransitionRequest, db: Db, user: Actor) -> dict:
    row = _get_or_404(db, incident_id)
    _workflow(transition, db, row, user, TransitionInput(**body.model_dump()))
    return _commit_and_announce(db, row)


@router.patch("/incidents/{incident_id}")
def patch_incident(incident_id: str, body: StatusPatch, db: Db, user: Actor) -> dict:
    """Alias of POST .../transition (kept from contract v1)."""
    row = _get_or_404(db, incident_id)
    fields = body.model_dump()
    _workflow(transition, db, row, user, TransitionInput(to=fields.pop("status"), **fields))
    return _commit_and_announce(db, row)


@router.post("/incidents/{incident_id}/assign")
def assign_incident(incident_id: str, db: Db, user: Actor) -> dict:
    row = _get_or_404(db, incident_id)
    _workflow(assign_case, db, row, user)
    return _commit_and_announce(db, row)


@router.post("/incidents/{incident_id}/label")
def label_incident(incident_id: str, body: LabelRequest, db: Db, user: Actor) -> dict:
    row = _get_or_404(db, incident_id)
    set_label(db, row, user, body.label)
    return _commit_and_announce(db, row)


def _report_items(db: Session, incident_id: str, limit: int = 50) -> list[dict]:
    reports = (
        db.query(UserReport)
        .filter(UserReport.incident_id == incident_id)
        .order_by(UserReport.created_at.desc(), UserReport.id)
        .limit(limit)
        .all()
    )
    return [
        {"created_at": iso(r.created_at), "category_hint": r.category_hint, "comment": r.comment}
        for r in reports
    ]


@router.get("/incidents/{incident_id}/history")
def incident_history(incident_id: str, db: Db) -> dict:
    row = _get_or_404(db, incident_id)
    return {"items": audit.incident_history(db, row.id)}


@router.post("/incidents/{incident_id}/rescan", status_code=202)
def rescan_incident(incident_id: str, db: Db, user: Actor) -> dict:
    """Extra: fetch the same source again through the pipeline (periodic update on demand). The
    incident is updated in place; a changed content hash is recorded in its version history."""
    row = _get_or_404(db, incident_id)
    url, options = row.source_url, rescan_options(row)
    audit.record(db, user, "rescan", incident_id=row.id, new={"url": url})
    db.commit()
    db.close()
    job_id = create_job(url, **options)
    dispatch(job_id)
    return {"job_id": job_id}


@router.get("/incidents/{incident_id}/versions")
def incident_versions(incident_id: str, db: Db) -> dict:
    """Contract v4: observations of the source, newest first. `is_evidence` marks the frozen detection."""
    row = _get_or_404(db, incident_id)
    versions = (
        db.query(IncidentVersion)
        .filter(IncidentVersion.incident_id == row.id)
        .order_by(IncidentVersion.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": v.id,
                "content_hash": v.content_hash,
                "risk_score": v.risk_score,
                "changed": v.changed,
                "created_at": iso(v.created_at),
                "outcome": v.outcome or "content",
                "http_status": v.http_status,
                "published_at": v.published_at,
                "is_evidence": v.id == row.evidence_version_id,
                "has_snapshot": v.payload is not None,
            }
            for v in versions
        ]
    }


@router.get("/incidents/{incident_id}/versions/{version_id}")
def incident_version(incident_id: str, version_id: int, db: Db) -> dict:
    """Contract v4: one stored observation with its full analysis (for a before / after comparison)."""
    row = _get_or_404(db, incident_id)
    version = db.get(IncidentVersion, version_id)
    if version is None or version.incident_id != row.id or version.payload is None:
        raise HTTPException(404, "observation not found")
    return {
        "id": version.id,
        "created_at": iso(version.created_at),
        "is_evidence": version.id == row.evidence_version_id,
        "analysis": version.payload,
    }


@router.get("/incidents/{incident_id}/export.csv")
def export_incident_csv(incident_id: str, db: Db, user: Actor) -> Response:
    row = _get_or_404(db, incident_id)
    body = csv_export.incident_csv(to_incident(row), _report_items(db, row.id))
    audit.record(db, user, "export", incident_id=row.id, new={"format": "csv"})
    return _csv_response(body, f"investwatch-{row.id}.csv")


def _render(incident_id: str, db: Session, user: Actor) -> Response:
    from app.exports.pdf import render_pdf
    from app.scraper.browser import BrowserUnavailable

    row = _get_or_404(db, incident_id)
    incident = to_incident(row)
    history = audit.incident_history(db, row.id, audit.DECISION_ACTIONS)
    reports = _report_items(db, row.id, 20)
    db.close()  # do not hold a connection while Chromium renders
    try:
        pdf = render_pdf(incident, history, reports)
    except BrowserUnavailable as exc:
        raise HTTPException(503, "PDF renderer is not available") from exc
    with session_scope() as audit_db:  # only a document that was really produced is logged
        audit.record(
            audit_db,
            user,
            "export",
            incident_id=incident["id"],
            new={"format": "pdf", "document": "detection_report"},
        )
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="raport-z-wykrycia-{incident["id"]}.pdf"'},
    )


@router.get("/incidents/{incident_id}/export.pdf")
def export_incident_pdf(incident_id: str, db: Db, user: Actor) -> Response:
    """Contract v4: the detection report (replaces the evidence package; no warning-list request)."""
    return _render(incident_id, db, user)


@router.get("/stats/date-bounds")
def date_bounds() -> dict:
    """The range every date filter accepts: system start date to now."""
    return window()


@router.get("/stats/trends")
def trends(
    db: Db,
    days: Annotated[int, Query(ge=1, le=366)] = 30,
    hours: Annotated[int | None, Query(ge=1, le=168)] = None,
    from_: Annotated[str | None, Query(alias="from", max_length=40)] = None,
    to: Annotated[str | None, Query(max_length=40)] = None,
) -> dict:
    """Raw scores by hour/day in a bounded range; partial first/last buckets are retained."""
    now = utcnow()
    system_start = get_settings().system_start
    start = _parse_bound(from_, "from", end=False)
    end = _parse_bound(to, "to", end=True)
    check_bound(from_, start, lower=True)
    check_bound(to, end, lower=False)
    end = min(end or now, now)
    custom = start is not None or to is not None
    hourly = bool(hours) or (custom and start is not None and end - start <= timedelta(days=1))
    step = timedelta(hours=1) if hourly else timedelta(days=1)
    if start is None:
        count = hours or days
        start = (
            now.replace(minute=0, second=0, microsecond=0)
            if hourly
            else datetime.combine(now.date(), time.min, tzinfo=UTC)
        ) - step * (count - 1)
    start = max(start, system_start)
    if start > end:
        raise HTTPException(422, "Początek zakresu nie może być późniejszy niż jego koniec.")
    if end - start > timedelta(days=366):
        raise HTTPException(422, "Wybierz zakres nie dłuższy niż 366 dni.")
    first = (
        start.replace(minute=0, second=0, microsecond=0)
        if hourly
        else start.replace(hour=0, minute=0, second=0, microsecond=0)
    )
    # Bare end dates are exclusive; exact timestamps are inclusive.
    exclusive = bool(to) and len(to or "") <= 10 and _parse_bound(to, "to", end=True) <= now
    last = end - timedelta(microseconds=1) if exclusive else end
    count = max(1, int((last - first) // step) + 1)
    query = db.query(Incident.id, Incident.risk_score, Incident.primary_module, Incident.created_at).filter(
        Incident.created_at >= start,
        or_(Incident.in_scope.is_(None), Incident.in_scope.is_(True)),
    )
    query = query.filter(Incident.created_at < end if exclusive else Incident.created_at <= end)
    fmt = "%Y-%m-%dT%H:00:00Z" if hourly else "%Y-%m-%d"
    buckets: dict[str, list[dict]] = {(first + step * n).strftime(fmt): [] for n in range(count)}
    for incident_id, score, module, created_at in query.order_by(Incident.created_at).all():
        moment = (created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)).astimezone(UTC)
        key = moment.strftime(fmt)
        if key in buckets:
            buckets[key].append({"id": incident_id, "risk_score": score, "module": module})
    return {"days": [{"date": key, "items": items} for key, items in buckets.items()]}


ANALYST_TRUTH = {"true_positive": "violation", "false_positive": "ok"}


@router.get("/calibration")
def calibration(db: Db) -> dict:
    """Seeded ground truth plus analyst labels; an analyst's verdict wins over the sample label."""
    query = db.query(Incident).filter(
        or_(Incident.ground_truth.in_(("violation", "ok")), Incident.label.in_(tuple(ANALYST_TRUTH)))
    )
    items = []
    for row in _ordered(query).all():
        analyst = ANALYST_TRUTH.get(row.label or "")
        items.append(
            {
                "id": row.id,
                "title": row.payload.get("title", ""),
                "risk_score": row.risk_score,
                "ground_truth": analyst or row.ground_truth,
                "module": row.primary_module,
                "label_source": "analyst" if analyst else "sample",
            }
        )
    return {"items": items}


def _csv_response(body: bytes, filename: str) -> Response:
    return Response(
        body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
