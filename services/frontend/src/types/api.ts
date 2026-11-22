// Mirrors coord/contracts/api.md (version 1).
import type { EscalationPath, GroundTruth, IncidentSummary, ModuleId, ResolutionAction, Role, Status } from "./incident";

export interface IncidentList {
  items: IncidentSummary[];
  total: number;
}

export interface TrendItem {
  id: string;
  risk_score: number;
  module: ModuleId;
}
export interface TrendDay {
  date: string;
  items: TrendItem[];
}
export interface Trends {
  days: TrendDay[];
}

export interface CalibrationItem {
  id: string;
  title: string;
  risk_score: number;
  ground_truth: GroundTruth;
  module: ModuleId;
  /** "analyst": labelled by an analyst in the case workflow; "sample": seeded ground truth. */
  label_source?: "sample" | "analyst";
}
export interface CalibrationSet {
  items: CalibrationItem[];
}

export type ScanState = "queued" | "scraping" | "analyzing" | "done" | "failed";
export interface ScanJob {
  id: string;
  url: string;
  state: ScanState;
  incident_id: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface ScanRequest {
  url: string;
  module_hint?: ModuleId;
  render?: boolean;
}

export interface Health {
  status: string;
  ai: { reachable: boolean; llm_available: boolean; model: string | null };
  queue: boolean;
  storage: boolean;
}

// ── Contract v3: authentication, workflow, settings, audit

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
}

export interface AuthConfig {
  demo_login: boolean;
  /** Additive to the contract: lets the client skip /api/auth/me (and its 401) when there is no session. */
  authenticated?: boolean;
}

export interface TransitionRequest {
  to: Status;
  reason?: string;
  escalation_path?: EscalationPath;
  resolution_action?: ResolutionAction;
}

/** A calibration change, one per user with its own read state (GET /api/notifications). */
export interface CalibrationNotification {
  id: number;
  created_at: string;
  read_at: string | null;
  message: string;
  details: Record<string, unknown>;
}

export interface ThresholdSettings {
  flag: number;
  critical: number;
  updated_by: string | null;
  updated_at: string | null;
}

export type AuditAction =
  | "login" | "assign" | "transition" | "label" | "thresholds" | "calibration_preview" | "export" | "rescan" | "public_report";

export interface AuditEntry {
  id: number | string;
  at: string;
  actor_email: string;
  actor_role: Role;
  action: AuditAction;
  incident_id: string | null;
  previous: unknown;
  new: unknown;
  reason: string | null;
  /** WatchIT: title of the case the entry refers to (audit log list only) */
  incident_title?: string | null;
}

// ── Contract v3: public reports

/** 1 = influencer / third-party ad, 2 = investment firm material, 3 = advice without a licence, null = unknown. */
export type ReportCategory = 1 | 2 | 3;

export interface PublicReportRequest {
  url: string;
  category_hint?: ReportCategory | null;
  comment?: string;
}

export interface PublicReportAccepted {
  status: "accepted";
  known: boolean;
}

/** GET /api/incidents/{id}/reports (logged in only). */
export interface CaseReport {
  created_at: string;
  category_hint: ReportCategory | null;
  comment: string | null;
}
