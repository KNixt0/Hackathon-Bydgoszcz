"""Pydantic mirror of coord/contracts/incident.md and api.md (versions 1-3).

Output models forbid extra keys so a drift from the contract fails loudly in tests.
Input models ignore unknown keys so the scraper may add fields without breaking us.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer

ModuleId = Literal[1, 2, 3]
RiskLevel = Literal["red", "orange", "green"]
RuleId = Literal[
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12a",
    "12b",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
]
Platform = Literal["web", "youtube", "instagram", "facebook", "tiktok", "x", "google_ads", "sample"]
RegistryId = Literal[
    "knf_investment_firms",
    "knf_banks_brokerage",
    "knf_brokerage_houses",
    "knf_foreign_branches",
    "knf_foreign_cross_border",
    "knf_public_warnings",
    "knf_investment_advisors",
    "kirp_legal_advisers",
    "kidp_tax_advisers",
    "uknf_cooperation_notice",
]
Severity = Literal["high", "medium", "low", "info"]


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SparseOut(Out):
    """Output model whose optional keys are omitted (not null) when unset."""

    @model_serializer(mode="wrap")
    def _drop_none(self, handler):  # type: ignore[no-untyped-def]
        return {k: v for k, v in handler(self).items() if v is not None}


class In(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------- output


class Screenshots(SparseOut):
    desktop: str | None = None
    tablet: str | None = None
    mobile: str | None = None


class Archive(Out):
    html_key: str | None = None
    screenshot_key: str | None = None  # desktop screenshot (kept for compatibility)
    screenshots: Screenshots | None = None  # contract v3: one full-page PNG per viewport

    @model_serializer(mode="wrap")
    def _drop_empty_screenshots(self, handler):  # type: ignore[no-untyped-def]
        data = handler(self)
        if data.get("screenshots") is None:
            data.pop("screenshots", None)
        return data


class Source(SparseOut):
    platform: Platform
    url: str
    fetched_at: str
    language: str
    content_hash: str
    text: str
    archive: Archive
    final_url: str | None = None  # contract v3
    redirect_chain: list[str] | None = None
    affiliate_params: list[str] | None = None


class Party(SparseOut):
    name: str
    kind: Literal[
        "investment_firm",
        "advertiser",
        "influencer",
        "pr_agency",
        "advisor",
        "lawyer",
        "company",
        "person",
    ]
    url: str | None = None
    handle: str | None = None
    country: str | None = None
    krs: str | None = None
    nip: str | None = None


class Entities(Out):
    investment_firm: Party | None
    advertiser: Party | None
    others: list[Party]


class Finding(Out):
    code: str
    severity: Severity
    text: str
    evidence_ids: list[str]


class ModuleResult(Out):
    module: ModuleId
    plugin: str
    score: float
    weight: float
    findings: list[Finding]


RuleMethod = Literal["rendered", "static", "text", "llm"]


class RuleResult(Out):
    id: RuleId
    name: str
    legal_basis: str
    status: Literal["pass", "fail", "na", "unknown"]
    confidence: float = Field(ge=0, le=1)
    explanation: str
    evidence_ids: list[str]
    method: RuleMethod = "text"  # contract v3: "rendered" only when decided from document.visual
    score: float = Field(default=0.0, ge=0, le=1)  # contract v3: violation strength


class RegistryCheck(Out):
    registry: RegistryId
    label: str
    url: str
    subject: str
    status: Literal["listed", "not_listed", "warning_listed", "inactive", "not_checked"]
    detail: str
    snapshot_date: str | None


class GraphNode(SparseOut):
    id: str
    type: Literal["company", "person", "pr_agency", "influencer", "ad", "advisor"]
    label: str
    meta: dict[str, str | int | float] | None = None


EdgeType = Literal[
    "board_member",
    "owner",
    "beneficial_owner",
    "employs",
    "contract",
    "promotes",
    "related",
    "publishes",
]


class GraphEdge(Out):
    source: str
    target: str
    type: EdgeType
    label: str
    suspicious: bool


class FlaggedPath(Out):
    node_ids: list[str]
    description: str


class Graph(Out):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    flagged_paths: list[FlaggedPath]


class TimelinePoint(Out):
    date: str
    count: int
    avg_rating: float
    new_account_share: float


class AgeBucket(Out):
    bucket: Literal["<14d", "14–90d", "3–12m", "1–3y", ">3y"]
    count: int


class Origin(Out):
    country: str
    count: int


class NamePattern(Out):
    pattern: str
    count: int
    examples: list[str]


class Accounts(Out):
    total: int
    share_younger_14d: float
    age_buckets: list[AgeBucket]
    origins: list[Origin]
    name_patterns: list[NamePattern]


class Anomaly(Out):
    type: Literal["opinion_spike", "fresh_account_cluster", "name_pattern_cluster", "foreign_origin_cluster"]
    severity: Literal["high", "medium", "low"]
    description: str


class SampleAccount(Out):
    handle: str
    created_at: str
    country: str
    text: str


class Forensics(Out):
    opinion_timeline: list[TimelinePoint]
    accounts: Accounts
    anomalies: list[Anomaly]
    sample_accounts: list[SampleAccount]


class Statement(Out):
    year: int
    revenue_pln: float | None
    net_result_pln: float | None
    filed: bool


class Financials(Out):
    company: str
    krs: str | None
    incorporated_on: str | None
    age_months: int | None
    share_capital_pln: float | None
    statements: list[Statement]
    flags: list[str]


class Claim(Out):
    id: str
    stance: Literal["for", "against"]
    text: str
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str]
    verdict: Literal["upheld", "weakened", "rejected"]
    critique: str | None


class DebateRound(Out):
    round: Literal[1, 2, 3]
    agent: str
    role: str
    summary: str
    claim_ids: list[str]


class Debate(Out):
    rounds: list[DebateRound]
    claims: list[Claim]
    arguments_for: list[str]
    arguments_against: list[str]
    arbiter_rationale: str


class Span(Out):
    start: int
    end: int


Viewport = Literal["desktop", "tablet", "mobile"]


class BBox(Out):
    """CSS px in that viewport's full-page screenshot (contract v3)."""

    viewport: Viewport
    x: float
    y: float
    w: float
    h: float


class Evidence(SparseOut):
    id: str
    kind: Literal["quote", "legal", "registry", "archive", "account", "url", "krs"]
    label: str
    quote: str | None = None
    span: Span | None = None
    legal_ref: str | None = None
    attachment: str | None = None
    url: str | None = None
    storage_key: str | None = None
    bbox: BBox | None = None  # contract v3: storage_key then points at that viewport's screenshot


class Recommendation(Out):
    action: Literal["none", "monitor", "explain", "escalate"]
    label: str
    next_step: str


class EngineInfo(Out):
    version: str
    plugins: list[str]
    llm_used: bool
    model: str | None
    duration_ms: float


class Analysis(Out):
    title: str
    summary: str
    modules: list[ModuleId]
    primary_module: ModuleId
    risk_score: float = Field(ge=0, le=100)
    compliance_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    synthetic: bool
    ground_truth: Literal["violation", "ok"] | None
    demo_case: str | None
    source: Source
    entities: Entities
    module_results: list[ModuleResult]
    rules: list[RuleResult]
    registry_checks: list[RegistryCheck]
    graph: Graph
    forensics: Forensics | None
    financials: Financials | None
    debate: Debate
    evidence: list[Evidence]
    recommendation: Recommendation
    engine: EngineInfo


# ---------------------------------------------------------------- input


class Author(In):
    name: str
    handle: str | None = None
    url: str | None = None


class FetchInfo(In):
    engine: str = "file"
    user_agent: str = ""
    proxy: str | None = None


class BBoxIn(In):
    viewport: Viewport = "desktop"
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0


class ViewportMeasureIn(In):
    """One viewport of one measured element (scraper extension of `visual`, optional)."""

    font_px: float | None = None  # rendered size: CSS px x page zoom of that device
    visible: bool = True
    occluded: bool = False
    clipped: bool = False
    contrast: float | None = None
    requires_interaction: str | None = None
    bbox: BBoxIn | None = None
    bbox_of: str | None = None
    area_share: float | None = None


class RiskElementIn(In):
    text: str
    font_px: float
    ratio_to_dominant: float | None = None
    color: str = ""
    background: str = ""
    contrast: float = 21.0
    opacity: float = 1.0
    visible: bool = True
    occluded: bool = False
    placement: Literal["body", "footer", "footnote", "legal_section"] = "body"
    requires_interaction: Literal["details", "accordion", "tooltip", "modal", "link"] | None = None
    control_text: str | None = None
    bbox: BBoxIn | None = None
    bbox_of: str | None = None
    bboxes: list[BBoxIn] = Field(default_factory=list)
    by_viewport: dict[str, ViewportMeasureIn] = Field(default_factory=dict)


class PerformanceBlockIn(In):
    text: str
    font_px: float
    area_share: float = 0.0
    bbox: BBoxIn | None = None
    by_viewport: dict[str, ViewportMeasureIn] = Field(default_factory=dict)


class ViewportIn(In):
    name: Viewport
    width: int
    height: int
    page_height: int = 0
    screenshot_key: str | None = None
    overflow_x: bool = False
    scroll_width: int | None = None
    layout_width: int | None = None
    clipped_texts: list[str] = Field(default_factory=list)
    min_risk_font_px: float | None = None


class VisualIn(In):
    """`Document.visual` (contract v3): measurements from a real browser."""

    dominant_font_px: float
    max_font_px: float | None = None
    viewports: list[ViewportIn] = Field(default_factory=list)
    risk_elements: list[RiskElementIn] = Field(default_factory=list)
    performance_blocks: list[PerformanceBlockIn] = Field(default_factory=list)


class AffiliateLinkIn(In):
    url: str
    host: str = ""
    params: list[str] = Field(default_factory=list)


class Document(In):
    url: str
    platform: Platform = "sample"
    fetched_at: str
    http_status: int = 200
    title: str = ""
    html: str = ""
    text: str = ""
    language: str | None = None
    published_at: str | None = None
    author: Author | None = None
    fetch: FetchInfo = Field(default_factory=FetchInfo)
    archive: Archive = Field(default_factory=Archive)
    # contract v3
    final_url: str | None = None
    redirect_chain: list[str] = Field(default_factory=list)
    affiliate_params: list[str] = Field(default_factory=list)
    affiliate_links: list[AffiliateLinkIn] = Field(default_factory=list)  # scraper extension: host per link
    visual: VisualIn | None = None


class StatementIn(In):
    year: int
    revenue_pln: float | None = None
    net_result_pln: float | None = None
    filed: bool = False


class CompanyIn(In):
    name: str
    krs: str | None = None
    role: Literal["investment_firm", "advertiser", "pr_agency", "other"] = "other"
    incorporated_on: str | None = None
    share_capital_pln: float | None = None
    country: str | None = None
    statements: list[StatementIn] = Field(default_factory=list)


class GraphNodeIn(In):
    id: str
    type: Literal["company", "person", "pr_agency", "influencer", "ad", "advisor"]
    label: str
    meta: dict[str, str | int | float] | None = None


class GraphEdgeIn(In):
    source: str
    target: str
    type: EdgeType
    label: str = ""


class GraphIn(In):
    nodes: list[GraphNodeIn] = Field(default_factory=list)
    edges: list[GraphEdgeIn] = Field(default_factory=list)


class CommentIn(In):
    handle: str
    account_created: str
    country: str = ""
    lang: str = ""
    text: str = ""
    posted_at: str
    rating: float | None = None


class Declared(In):
    advisor_licence_no: str | None = None
    legal_adviser_name: str | None = None
    legal_adviser_no: str | None = None
    tax_adviser_no: str | None = None


class Context(In):
    synthetic: bool | None = None
    ground_truth: Literal["violation", "ok"] | None = None
    demo_case: str | None = None
    module_hint: ModuleId | None = None
    cooperation_notified: bool | None = None
    companies: list[CompanyIn] = Field(default_factory=list)
    graph: GraphIn | None = None
    comments: list[CommentIn] = Field(default_factory=list)
    declared: Declared | None = None


class AnalyzeRequest(In):
    document: Document
    context: Context | None = None


class RegistryEntryIn(In):
    name: str
    aliases: list[str] = Field(default_factory=list)
    status: str | None = None
    detail: str | None = None
    # Optional extension (superset of the contract): official web domains of the entity,
    # used by the brand-impersonation check.
    domains: list[str] = Field(default_factory=list)


class RegistryPut(In):
    snapshot_date: str
    entries: list[RegistryEntryIn]


JsonDict = dict[str, Any]
