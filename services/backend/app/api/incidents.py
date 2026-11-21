"""Incidents: list/filter, detail, status change, stats, calibration, exports."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Query as SAQuery
from sqlalchemy.orm import Session

from app import events
from app.db import get_db
from app.exports import csv_export
from app.incidents import rescan_options, to_incident, to_summary
from app.jobs import create_job, dispatch
from app.models import Incident, IncidentVersion, utcnow
from app.schemas import PLATFORMS, STATUSES, StatusPatch, iso

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
    ) -> None:
        if source is not None and source not in PLATFORMS:
            raise HTTPException(422, f"'source' must be one of: {', '.join(PLATFORMS)}")
        if status is not None and status not in STATUSES:
            raise HTTPException(422, f"'status' must be one of: {', '.join(STATUSES)}")
        self.module, self.source, self.status, self.q = module, source, status, q
        self.start = _parse_bound(from_, "from", end=False)
        self.end = _parse_bound(to, "to", end=True)
        self.end_inclusive = bool(to) and len(to or "") > 10

    def apply(self, query: SAQuery) -> SAQuery:
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
        if self.q and self.q.strip():
            needle = self.q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(Incident.search_text.like(f"%{needle}%", escape="\\"))
        return query


def _ordered(query: SAQuery) -> SAQuery:
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
    rows = _ordered(query).offset(offset).limit(limit).all()
    return {"items": [to_summary(row) for row in rows], "total": total}


# declared before /incidents/{incident_id} so "export.csv" is not taken for an id
@router.get("/incidents/export.csv")
def export_list_csv(db: Db, filters: Annotated[IncidentFilters, Depends()]) -> Response:
    rows = _ordered(filters.apply(db.query(Incident))).limit(5000).all()
    body = csv_export.incidents_csv(to_summary(row) for row in rows)
    return _csv_response(body, f"investwatch-incydenty-{utcnow():%Y%m%d}.csv")


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, db: Db) -> dict:
    return to_incident(_get_or_404(db, incident_id))


@router.patch("/incidents/{incident_id}")
def patch_incident(incident_id: str, body: StatusPatch, db: Db) -> dict:
    row = _get_or_404(db, incident_id)
    row.status = body.status
    row.updated_at = utcnow()
    db.commit()
    events.emit("incident:updated", to_summary(row))
    return to_incident(row)


@router.post("/incidents/{incident_id}/rescan", status_code=202)
def rescan_incident(incident_id: str, db: Db) -> dict:
    """Extra: fetch the same source again through the pipeline (periodic update on demand). The
    incident is updated in place; a changed content hash is recorded in its version history."""
    row = _get_or_404(db, incident_id)
    url, options = row.source_url, rescan_options(row)
    db.close()
    job_id = create_job(url, **options)
    dispatch(job_id)
    return {"job_id": job_id}


@router.get("/incidents/{incident_id}/versions")
def incident_versions(incident_id: str, db: Db) -> dict:
    """Extra (not in the contract): re-scan history used for diffing."""
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
                "content_hash": v.content_hash,
                "risk_score": v.risk_score,
                "changed": v.changed,
                "created_at": iso(v.created_at),
            }
            for v in versions
        ]
    }


@router.get("/incidents/{incident_id}/export.csv")
def export_incident_csv(incident_id: str, db: Db) -> Response:
    row = _get_or_404(db, incident_id)
    return _csv_response(csv_export.incident_csv(to_incident(row)), f"investwatch-{row.id}.csv")


@router.get("/incidents/{incident_id}/export.pdf")
def export_incident_pdf(incident_id: str, db: Db) -> Response:
    from app.exports.pdf import render_pdf
    from app.scraper.browser import BrowserUnavailable

    row = _get_or_404(db, incident_id)
    incident = to_incident(row)
    db.close()  # do not hold a connection while Chromium renders
    try:
        pdf = render_pdf(incident)
    except BrowserUnavailable as exc:
        raise HTTPException(503, "PDF renderer is not available") from exc
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="investwatch-{incident["id"]}.pdf"'},
    )


@router.get("/stats/trends")
def trends(db: Db, days: Annotated[int, Query(ge=1, le=366)] = 30) -> dict:
    today = utcnow().date()
    first = today - timedelta(days=days - 1)
    start = datetime.combine(first, time.min, tzinfo=UTC)
    rows = (
        db.query(Incident.id, Incident.risk_score, Incident.primary_module, Incident.created_at)
        .filter(Incident.created_at >= start)
        .order_by(Incident.created_at)
        .all()
    )
    buckets: dict[str, list[dict]] = {(first + timedelta(days=n)).isoformat(): [] for n in range(days)}
    for incident_id, score, module, created_at in rows:
        moment = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
        key = moment.astimezone(UTC).date().isoformat()
        if key in buckets:
            buckets[key].append({"id": incident_id, "risk_score": score, "module": module})
    return {"days": [{"date": key, "items": items} for key, items in buckets.items()]}


@router.get("/calibration")
def calibration(db: Db) -> dict:
    rows = _ordered(db.query(Incident).filter(Incident.ground_truth.in_(("violation", "ok")))).all()
    return {
        "items": [
            {
                "id": row.id,
                "title": row.payload.get("title", ""),
                "risk_score": row.risk_score,
                "ground_truth": row.ground_truth,
                "module": row.primary_module,
            }
            for row in rows
        ]
    }


def _csv_response(body: bytes, filename: str) -> Response:
    return Response(
        body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
