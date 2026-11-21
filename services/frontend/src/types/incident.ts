// Mirrors coord/contracts/incident.md (version 1). Do not extend here: the contract is the source of truth.

export type ModuleId = 1 | 2 | 3;
export type RiskLevel = "red" | "orange" | "green";
// Contract v3: the case workflow (old closed_violation → resolved, closed_ok → false_positive).
// Contract v4: awaiting_correction = an intervention was recorded, the source is re-checked.
export type Status =
  | "new" | "in_review" | "escalation_requested" | "escalated" | "awaiting_correction" | "resolved" | "false_positive";
export type Role = "ANALYST" | "SUPERVISOR";
// Contract v4: neutral paths; the system detects and reports, it drafts no formal motions.
export type EscalationPath = "RISK_INFORMATION" | "UNLICENSED_ACTIVITY" | "THIRD_PARTY_ADVERTISING";
export type ResolutionAction = "evidence_report" | "content_removed" | "content_corrected" | "false_positive";
export type CaseLabel = "unlabeled" | "true_positive" | "false_positive";

export interface Workflow {
  assigned_to: string | null;
  escalation_path: EscalationPath | null;
  resolution_action: ResolutionAction | null;
  resolution_note: string;
  label: CaseLabel;
}
export type RuleId =
  | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11"
  | "12a" | "12b" | "13" | "14" | "15" | "16" | "17" | "18";
export type GroundTruth = "violation" | "ok";
export type Platform = "web" | "youtube" | "instagram" | "facebook" | "tiktok" | "x" | "google_ads" | "sample";

export interface Source {
  platform: Platform;
  url: string;
  fetched_at: string;
  language: string;
  content_hash: string;
  text: string;
  archive: {
    html_key: string | null;
    screenshot_key: string | null;
    // Contract v3: one full-page screenshot per viewport (screenshot_key = desktop).
    screenshots?: Partial<Record<Viewport, string>>;
  };
  // Contract v3: what the scraper saw while fetching.
  final_url?: string;
  redirect_chain?: string[];
  affiliate_params?: string[];
  /** Contract v4: when the material was published (the post), not when it was detected. */
  published_at?: string | null;
}

// Contract v3: rendered visual audit.
export type Viewport = "desktop" | "tablet" | "mobile";
/** CSS px in that viewport's full-page screenshot. */
export interface BBox {
  viewport: Viewport;
  x: number;
  y: number;
  w: number;
  h: number;
}
export type RuleMethod = "rendered" | "static" | "text" | "llm";

export interface Party {
  name: string;
  kind: "investment_firm" | "advertiser" | "influencer" | "pr_agency" | "advisor" | "lawyer" | "company" | "person";
  url?: string;
  handle?: string;
  country?: string;
  krs?: string;
  nip?: string;
}

export interface Entities {
  investment_firm: Party | null;
  advertiser: Party | null;
  others: Party[];
}

export interface Finding {
  code: string;
  severity: "high" | "medium" | "low" | "info";
  text: string;
  evidence_ids: string[];
}

export interface ModuleResult {
  module: ModuleId;
  plugin: string;
  score: number;
  weight: number;
  findings: Finding[];
}

export type RuleStatus = "pass" | "fail" | "na" | "unknown";

export interface RuleResult {
  id: RuleId;
  name: string;
  legal_basis: string;
  status: RuleStatus;
  confidence: number;
  explanation: string;
  evidence_ids: string[];
  // Contract v3: how the verdict was reached and its 0–1 violation strength.
  method?: RuleMethod;
  score?: number;
}

export type RegistryStatus = "listed" | "not_listed" | "warning_listed" | "inactive" | "not_checked";

export interface RegistryCheck {
  registry:
    | "knf_investment_firms" | "knf_banks_brokerage" | "knf_brokerage_houses"
    | "knf_foreign_branches" | "knf_foreign_cross_border" | "knf_public_warnings"
    | "knf_investment_advisors" | "kirp_legal_advisers" | "kidp_tax_advisers" | "uknf_cooperation_notice";
  label: string;
  url: string;
  subject: string;
  status: RegistryStatus;
  detail: string;
  snapshot_date: string | null;
}

export type GraphNodeType = "company" | "person" | "pr_agency" | "influencer" | "ad" | "advisor";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  meta?: Record<string, string | number>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "board_member" | "owner" | "beneficial_owner" | "employs" | "contract" | "promotes" | "related" | "publishes";
  label: string;
  suspicious: boolean;
}

export interface FlaggedPath {
  node_ids: string[];
  description: string;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  flagged_paths: FlaggedPath[];
}

export interface Forensics {
  opinion_timeline: { date: string; count: number; avg_rating: number; new_account_share: number }[];
  accounts: {
    total: number;
    share_younger_14d: number;
    age_buckets: { bucket: "<14d" | "14–90d" | "3–12m" | "1–3y" | ">3y"; count: number }[];
    origins: { country: string; count: number }[];
    name_patterns: { pattern: string; count: number; examples: string[] }[];
  };
  anomalies: {
    type: "opinion_spike" | "fresh_account_cluster" | "name_pattern_cluster" | "foreign_origin_cluster";
    severity: "high" | "medium" | "low";
    description: string;
  }[];
  sample_accounts: { handle: string; created_at: string; country: string; text: string }[];
}

export interface Financials {
  company: string;
  krs: string | null;
  incorporated_on: string | null;
  age_months: number | null;
  share_capital_pln: number | null;
  statements: { year: number; revenue_pln: number | null; net_result_pln: number | null; filed: boolean }[];
  flags: string[];
}

export interface Claim {
  id: string;
  stance: "for" | "against";
  text: string;
  confidence: number;
  evidence_ids: string[];
  verdict: "upheld" | "weakened" | "rejected";
  critique: string | null;
}

export interface DebateRound {
  round: 1 | 2 | 3;
  agent: string;
  role: string;
  summary: string;
  claim_ids: string[];
}

export interface Debate {
  rounds: DebateRound[];
  claims: Claim[];
  arguments_for: string[];
  arguments_against: string[];
  arbiter_rationale: string;
}

export type EvidenceKind = "quote" | "legal" | "registry" | "archive" | "account" | "url" | "krs";

export interface Evidence {
  id: string;
  kind: EvidenceKind;
  label: string;
  quote?: string;
  span?: { start: number; end: number };
  legal_ref?: string;
  attachment?: string;
  url?: string;
  storage_key?: string;
  /** Contract v3: location on the screenshot of `bbox.viewport` (storage_key points at it). */
  bbox?: BBox;
}

export interface Recommendation {
  action: "none" | "monitor" | "explain" | "escalate";
  label: string;
  next_step: string;
}

export interface EngineInfo {
  version: string;
  plugins: string[];
  llm_used: boolean;
  model: string | null;
  duration_ms: number;
}

export interface Analysis {
  title: string;
  summary: string;
  modules: ModuleId[];
  primary_module: ModuleId;
  risk_score: number;
  compliance_score: number;
  risk_level: RiskLevel;
  synthetic: boolean;
  ground_truth: GroundTruth | null;
  demo_case: string | null;
  source: Source;
  entities: Entities;
  module_results: ModuleResult[];
  rules: RuleResult[];
  registry_checks: RegistryCheck[];
  graph: Graph;
  forensics: Forensics | null;
  financials: Financials | null;
  debate: Debate;
  evidence: Evidence[];
  recommendation: Recommendation;
  engine: EngineInfo;
  /** Contract v4: is the material within UKNF's remit as covered by modules 1-3? */
  scope?: Scope | null;
}

export type ScopeCategory =
  | "investment" | "consumer_credit" | "deposit" | "crypto" | "insurance" | "tax_legal" | "foreign_market" | "no_financial_offer";
export interface Scope {
  in_scope: boolean;
  category: ScopeCategory;
  basis: "supervised_entity" | "warning_listed" | "investment_offer" | "out_of_scope";
  reason: string;
  authority_hint?: string | null;
}

// Contract v4: publication, detection and later checks are three different facts.
export type ContentState = "online" | "changed" | "removed" | "unreachable";
export type FollowUpOutcome = "removed" | "corrected" | "persisting";
export interface Observation {
  published_at: string | null;
  detected_at: string;
  evidence_version_id: number | null;
  content_state: ContentState;
  last_checked_at: string;
}
export interface FollowUp {
  intervention_at: string;
  note: string;
  due: string | null;
  outcome: FollowUpOutcome | null;
}
export interface ObservationVersion {
  id: number;
  content_hash: string;
  risk_score: number;
  changed: boolean;
  created_at: string;
  outcome: "content" | "removed" | "unreachable";
  http_status: number | null;
  published_at: string | null;
  is_evidence: boolean;
  has_snapshot: boolean;
}

export interface Incident extends Analysis {
  id: string;
  status: Status;
  created_at: string;
  updated_at: string;
  workflow: Workflow;
  /** Contract v3: public reports linked to the case, and risk × reports (server-computed, threshold-free). */
  user_reports_count: number;
  priority_score: number;
  /** Contract v4 (optional: older backends and fixtures omit them). */
  observation?: Observation;
  follow_up?: FollowUp | null;
  previous_incident_id?: string | null;
}

export type IncidentSummary = Pick<
  Incident,
  | "id" | "title" | "summary" | "modules" | "primary_module" | "risk_score" | "compliance_score"
  | "risk_level" | "status" | "created_at" | "updated_at" | "synthetic" | "ground_truth" | "demo_case"
> & {
  source: Pick<Source, "platform" | "url">;
  advertiser: string | null;
  firm: string | null;
  failed_rules: RuleId[];
  workflow: Pick<Workflow, "assigned_to" | "label">;
  user_reports_count: number;
  priority_score: number;
  /** Contract v4 */
  in_scope?: boolean | null;
  content_state?: ContentState;
  follow_up?: { due: string | null; outcome: FollowUpOutcome | null } | null;
};
