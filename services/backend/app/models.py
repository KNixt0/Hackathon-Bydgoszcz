"""Tables. The full Analysis lives in `payload` (JSONB); filterable fields are mirrored in indexed columns."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, JSONType


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, index=True)
    primary_module: Mapped[int] = mapped_column(Integer, index=True)
    modules_mask: Mapped[int] = mapped_column(Integer, default=0)  # bit n-1 set = module n has findings
    platform: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ground_truth: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    demo_case: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_url_hash: Mapped[str] = mapped_column(String(64), index=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    search_text: Mapped[str] = mapped_column(Text, default="")
    # how to fetch it again (periodic re-scan)
    origin: Mapped[str] = mapped_column(String(16), default="scan")  # scan | sample | watchlist
    fetch_url: Mapped[str] = mapped_column(Text, default="")
    render: Mapped[bool] = mapped_column(Boolean, default=False)
    module_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scan_meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)  # sample meta
    scan_context: Mapped[dict | None] = mapped_column(JSONType, nullable=True)  # AI Context sent with it
    # case workflow (contract v3 `Workflow`); all nullable so existing volumes are upgraded in place
    assigned_to: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    escalation_path: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)  # None = unlabeled


class IncidentVersion(Base):
    __tablename__ = "incident_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64))
    risk_score: Mapped[float] = mapped_column(Float)
    changed: Mapped[bool] = mapped_column(Boolean, default=False)  # content differs from previous version
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    url: Mapped[str] = mapped_column(Text)  # canonical url shown to the user
    fetch_url: Mapped[str] = mapped_column(Text)  # what the scraper really requests
    state: Mapped[str] = mapped_column(String(16), index=True, default="queued")
    incident_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    origin: Mapped[str] = mapped_column(String(16), default="scan")
    render: Mapped[bool] = mapped_column(Boolean, default=False)
    module_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)  # sample meta
    context: Mapped[dict] = mapped_column(JSONType, default=dict)  # AI Context
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Blob(Base):
    """Object-storage fallback when S3 is unreachable."""

    __tablename__ = "blobs"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    content_type: Mapped[str] = mapped_column(String(64))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True)
    module_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    render: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # minimum hours between scheduled re-scans (None = every RESCAN_CRON run); 6 for enhanced monitoring
    interval_hours: Mapped[float | None] = mapped_column(Float, nullable=True)


class RegistrySnapshot(Base):
    """Last successfully scraped KNF register (kept when a refresh fails)."""

    __tablename__ = "registry_snapshots"

    name: Mapped[str] = mapped_column("registry", String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    snapshot_date: Mapped[str] = mapped_column(String(32))
    entries: Mapped[list] = mapped_column(JSONType, default=list)
    pushed_to_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DiscoverySource(Base):
    """A seed page (search results, ad library, channel/listing page) scanned for new material."""

    __tablename__ = "discovery_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True)
    module_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keywords: Mapped[list] = mapped_column(JSONType, default=list)  # empty = every link is a candidate
    max_links: Mapped[int] = mapped_column(Integer, default=20)
    render: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class DiscoveredLink(Base):
    """Every link discovery has already queued (so it is queued only once)."""

    __tablename__ = "discovered_links"

    url_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppLock(Base):
    """Cross-container mutex (e.g. only one process runs the startup seed)."""

    __tablename__ = "app_locks"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True)  # stored lower-case
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))  # ANALYST | SUPERVISOR
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    """Append-only: rows are only ever inserted (an ORM guard below and, on PostgreSQL, a trigger
    reject UPDATE and DELETE). No foreign key: the trail outlives a deleted incident."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utcnow)
    actor_email: Mapped[str] = mapped_column(String(255), index=True)
    actor_role: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(32), index=True)
    incident_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    previous: Mapped[Any] = mapped_column(JSONType, nullable=True)
    new: Mapped[Any] = mapped_column(JSONType, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


@event.listens_for(AuditLog, "before_update")
@event.listens_for(AuditLog, "before_delete")
def _audit_is_append_only(*_: object) -> None:
    raise PermissionError("audit_logs is append-only")


class AppSetting(Base):
    """Global settings edited in the UI (e.g. thresholds), one JSON value per key."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONType, default=dict)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


Index("ix_incidents_score_created", Incident.risk_score.desc(), Incident.created_at.desc())
