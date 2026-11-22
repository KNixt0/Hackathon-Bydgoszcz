"""Pydantic models: request bodies, wire shapes, and the (lenient) Analysis validation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

# contract v3: the case workflow (old closed_violation -> resolved, closed_ok -> false_positive)
Status = Literal[
    "new",
    "in_review",
    "escalation_requested",
    "escalated",
    "awaiting_correction",
    "resolved",
    "false_positive",
]
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
STATUSES: tuple[str, ...] = (
    "new",
    "in_review",
    "escalation_requested",
    "escalated",
    "awaiting_correction",  # contract v4: an intervention was recorded, the outcome is verified later
    "resolved",
    "false_positive",
)
Role = Literal["ANALYST", "SUPERVISOR"]
# contract v4: neutral paths (risk information / activity without authorisation / third-party advertising)
EscalationPath = Literal["RISK_INFORMATION", "UNLICENSED_ACTIVITY", "THIRD_PARTY_ADVERTISING"]
ResolutionAction = Literal["evidence_report", "content_removed", "content_corrected", "false_positive"]
Label = Literal["unlabeled", "true_positive", "false_positive"]


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


class PublicReportRequest(Strict):
    """POST /api/public/reports. The comment is stored as plain text and escaped wherever it is shown."""

    url: str = Field(min_length=1, max_length=2048)
    category_hint: ModuleId | None = None
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        value = value.strip()
        if not value.lower().startswith(("http://", "https://")):
            raise ValueError("only http and https addresses are accepted")
        return value

    @field_validator("comment")
    @classmethod
    def _plain(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = "".join(ch for ch in value if ch in "\n\t" or ch.isprintable()).strip()
        return cleaned or None


class StatusPatch(Strict):
    """PATCH /api/incidents/{id}: alias of the transition endpoint."""

    status: Status
    reason: str | None = Field(default=None, max_length=2000)
    escalation_path: EscalationPath | None = None
    resolution_action: ResolutionAction | None = None


class TransitionRequest(Strict):
    to: Status
    reason: str | None = Field(default=None, max_length=2000)
    escalation_path: EscalationPath | None = None
    resolution_action: ResolutionAction | None = None
    follow_up_days: int | None = Field(default=None, ge=1, le=180)  # awaiting_correction only


class LabelRequest(Strict):
    label: Label


class ThresholdsRequest(Strict):
    flag: float = Field(ge=0, le=100)
    critical: float = Field(ge=0, le=100)


class LoginRequest(Strict):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class DemoLoginRequest(Strict):
    role: Role


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
