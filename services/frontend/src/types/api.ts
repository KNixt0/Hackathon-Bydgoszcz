// Mirrors coord/contracts/api.md (version 1).
import type { GroundTruth, IncidentSummary, ModuleId } from "./incident";

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
