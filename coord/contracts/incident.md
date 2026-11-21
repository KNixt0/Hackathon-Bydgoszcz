version: 1

# Incident: the one schema every module ends in

The AI service returns an `Analysis`. The backend stores it, adds `id`, `status` and timestamps, and serves it as an `Incident`. The frontend renders only this shape. Types are written TypeScript-style; JSON on the wire uses exactly these keys.

## Score semantics (read first)

- `risk_score`: continuous `0–100`, **higher = more dangerous**. This is the raw engine output and the only number the threshold slider works on.
- `compliance_score = 100 - risk_score`, shown as "Compliance Score" (so the green demo case shows 92/100, the red one 11/100).
- `risk_level` is derived, never stored as truth: `red` if `risk_score >= T_red`, `orange` if `>= T_orange`, else `green`. Defaults `T_red = 70`, `T_orange = 35`. The dashboard recomputes levels client-side from `risk_score` whenever the slider moves.

## Types

```ts
type ModuleId = 1 | 2 | 3;
type RiskLevel = "red" | "orange" | "green";
type Status = "new" | "in_review" | "escalated" | "closed_violation" | "closed_ok";
type RuleId = "1"|"2"|"3"|"4"|"5"|"6"|"7"|"8"|"9"|"10"|"11"|"12a"|"12b"|"13"|"14"|"15"|"16"|"17"|"18";

interface Analysis {
  title: string;                 // short, human readable
  summary: string;               // 1–2 sentences, Polish
  modules: ModuleId[];           // every module that produced findings
  primary_module: ModuleId;
  risk_score: number;            // 0–100, continuous
  compliance_score: number;      // 100 - risk_score
  risk_level: RiskLevel;         // at default thresholds
  synthetic: boolean;            // true for seeded/fabricated demo material
  ground_truth: "violation" | "ok" | null;   // label, only for the calibration set
  demo_case: string | null;      // "case1" | "case2" | "case3" | null
  source: Source;
  entities: Entities;
  module_results: ModuleResult[];
  rules: RuleResult[];           // always all 19 rows (ids 1–18, 12 split into 12a/12b)
  registry_checks: RegistryCheck[];
  graph: Graph;                  // may be empty: {nodes:[],edges:[],flagged_paths:[]}
  forensics: Forensics | null;
  financials: Financials | null;
  debate: Debate;
  evidence: Evidence[];
  recommendation: Recommendation;
  engine: EngineInfo;
}

interface Incident extends Analysis {
  id: string;                    // uuid
  status: Status;
  created_at: string;            // ISO 8601 UTC, when detected
  updated_at: string;
}

// List rows and socket payloads use this subset.
type IncidentSummary = Pick<Incident,
  "id"|"title"|"summary"|"modules"|"primary_module"|"risk_score"|"compliance_score"|
  "risk_level"|"status"|"created_at"|"updated_at"|"synthetic"|"ground_truth"|"demo_case"> & {
  source: Pick<Source, "platform"|"url">;
  advertiser: string | null;     // entities.advertiser.name
  firm: string | null;           // entities.investment_firm.name
  failed_rules: RuleId[];
};

interface Source {
  platform: "web"|"youtube"|"instagram"|"facebook"|"tiktok"|"x"|"google_ads"|"sample";
  url: string;
  fetched_at: string;
  language: string;              // "pl", "en", …
  content_hash: string;          // sha256 of normalized text
  text: string;                  // normalized text the analysis ran on
  archive: { html_key: string | null; screenshot_key: string | null };  // object-storage keys
}

interface Party {
  name: string;
  kind: "investment_firm"|"advertiser"|"influencer"|"pr_agency"|"advisor"|"lawyer"|"company"|"person";
  url?: string; handle?: string; country?: string; krs?: string; nip?: string;
}
interface Entities {
  investment_firm: Party | null; // the firm being advertised / offering the service
  advertiser: Party | null;      // who published the material
  others: Party[];
}

interface ModuleResult {
  module: ModuleId;
  plugin: string;                // plugin id, e.g. "m1_finfluencer"
  score: number;                 // 0–100 risk from this module alone
  weight: number;                // weight used by the aggregator
  findings: Finding[];
}
interface Finding {
  code: string;                  // e.g. "RULE_6", "REGISTRY_NOT_LISTED", "ADVISORY_PHRASE", "PR_CONFLICT_PATH"
  severity: "high"|"medium"|"low"|"info";
  text: string;
  evidence_ids: string[];
}

interface RuleResult {
  id: RuleId;
  name: string;                  // from the UKNF criteria attachment
  legal_basis: string;           // e.g. "art. 44 ust. 2 lit. e rozp. del. 2017/565"
  status: "pass"|"fail"|"na"|"unknown";   // "na" = rule does not apply; "unknown" = needs visual/manual check
  confidence: number;            // 0–1
  explanation: string;
  evidence_ids: string[];
}

interface RegistryCheck {
  registry: "knf_investment_firms"|"knf_banks_brokerage"|"knf_brokerage_houses"|
            "knf_foreign_branches"|"knf_foreign_cross_border"|"knf_public_warnings"|
            "knf_investment_advisors"|"kirp_legal_advisers"|"kidp_tax_advisers"|"uknf_cooperation_notice";
  label: string;                 // Polish display name
  url: string;                   // official register URL
  subject: string;               // name / licence number that was looked up
  status: "listed"|"not_listed"|"warning_listed"|"inactive"|"not_checked";
  detail: string;                // e.g. "Nie wykonuje zawodu", matched entry name
  snapshot_date: string | null;  // date of the register snapshot used
}

interface GraphNode { id: string; type: "company"|"person"|"pr_agency"|"influencer"|"ad"|"advisor"; label: string; meta?: Record<string,string|number>; }
interface GraphEdge { source: string; target: string; type: "board_member"|"owner"|"beneficial_owner"|"employs"|"contract"|"promotes"|"related"|"publishes"; label: string; suspicious: boolean; }
interface Graph {
  nodes: GraphNode[]; edges: GraphEdge[];
  flagged_paths: { node_ids: string[]; description: string }[];  // e.g. board → PR agency → influencer
}

interface Forensics {
  opinion_timeline: { date: string; count: number; avg_rating: number; new_account_share: number }[];
  accounts: {
    total: number;
    share_younger_14d: number;                       // 0–1
    age_buckets: { bucket: "<14d"|"14–90d"|"3–12m"|"1–3y"|">3y"; count: number }[];
    origins: { country: string; count: number }[];
    name_patterns: { pattern: string; count: number; examples: string[] }[];
  };
  anomalies: { type: "opinion_spike"|"fresh_account_cluster"|"name_pattern_cluster"|"foreign_origin_cluster"; severity: "high"|"medium"|"low"; description: string }[];
  sample_accounts: { handle: string; created_at: string; country: string; text: string }[];
}

interface Financials {
  company: string; krs: string | null;
  incorporated_on: string | null; age_months: number | null;
  share_capital_pln: number | null;
  statements: { year: number; revenue_pln: number | null; net_result_pln: number | null; filed: boolean }[];
  flags: string[];               // e.g. "Spółka młodsza niż 12 miesięcy"
}

interface Claim {
  id: string;
  stance: "for" | "against";     // for = supports a violation; against = mitigating / exculpatory
  text: string;
  confidence: number;            // 0–1 after critique
  evidence_ids: string[];
  verdict: "upheld" | "weakened" | "rejected";
  critique: string | null;       // what the critic said about it
}
interface Debate {
  rounds: { round: 1 | 2 | 3; agent: string; role: string; summary: string; claim_ids: string[] }[];
  claims: Claim[];
  arguments_for: string[];       // claim ids kept after critique, stance "for"
  arguments_against: string[];   // claim ids, stance "against"
  arbiter_rationale: string;
}

interface Evidence {
  id: string;
  kind: "quote"|"legal"|"registry"|"archive"|"account"|"url"|"krs";
  label: string;
  quote?: string;                // exact substring of source.text for kind "quote"
  span?: { start: number; end: number };   // offsets into source.text
  legal_ref?: string;            // "art. 76 ustawy o obrocie instrumentami finansowymi"
  attachment?: string;           // which organiser file it comes from
  url?: string;
  storage_key?: string;          // object-storage key (html / screenshot)
}

interface Recommendation { action: "none"|"monitor"|"explain"|"escalate"; label: string; next_step: string; }
interface EngineInfo { version: string; plugins: string[]; llm_used: boolean; model: string | null; duration_ms: number; }
```

## Invariants (tested)

1. Every `evidence` item of kind `quote` is an exact substring of `source.text` (no invented quotes).
2. Every `evidence_ids` entry resolves to an `evidence` item.
3. `rules` has exactly 19 rows in attachment order.
4. `risk_score` is computed by the engine from findings; no score is hard-coded per sample.
