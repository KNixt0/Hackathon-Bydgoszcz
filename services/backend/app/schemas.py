"""Pydantic models: request bodies, wire shapes, and the (lenient) Analysis validation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

Status = Literal["new", "in_review", "escalated", "closed_violation", "closed_ok"]
ModuleId = Literal[1, 2, 3]
Platform = Literal["web", "youtube", "instagram", "facebook", "tiktok", "x", "google_ads", "sample"]
PLATFORMS: tuple[str, ...] = (
    "web",
    "youtube",
    "instagram",
    "facebook",
    "tiktok",
    "x",
    "google_ads",
    "sample",
)
STATUSES: tuple[str, ...] = ("new", "in_review", "escalated", "closed_violation", "closed_ok")


def iso(value: datetime | None) -> str | None:
    """ISO 8601 UTC with a Z suffix; naive values (SQLite) are taken as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScanRequest(Strict):
    url: AnyHttpUrl
    module_hint: ModuleId | None = None
    render: bool = False

    @field_validator("url")
    @classmethod
    def _length(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if len(str(value)) > 2048:
            raise ValueError("url too long")
        return value


class StatusPatch(Strict):
    status: Status


class ImportRequest(Strict):
    path: str | None = Field(default=None, max_length=512)


class DemoTriggerRequest(Strict):
    case: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")


class WatchlistRequest(ScanRequest):
    pass


class DiscoverySourceRequest(ScanRequest):
    keywords: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=30
    )
    max_links: int | None = Field(default=None, ge=1, le=100)


# ---- AI service response (only what the backend relies on is enforced; the rest passes through) ----


class _SourceIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    platform: str = "web"
    url: str = ""
    content_hash: str = ""


class AnalysisIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    summary: str = ""
    modules: list[ModuleId] = Field(default_factory=list)
    primary_module: ModuleId
    risk_score: float = Field(ge=0, le=100)
    synthetic: bool = False
    ground_truth: Literal["violation", "ok"] | None = None
    demo_case: str | None = None
    source: _SourceIn
    entities: dict[str, Any] = Field(default_factory=dict)
    rules: list[dict[str, Any]] = Field(default_factory=list)
