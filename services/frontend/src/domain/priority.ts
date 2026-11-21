import type { IncidentSummary } from "../types/incident";
import type { Thresholds } from "./levels";

/** Reports needed before a case counts as "reported by users" (contract: N = 5). */
export const REPORTS_N = 5;

export type PriorityTier = "critical_viral" | "high_risk_early" | "crowd_anomaly" | "low_watch";
export const TIERS: PriorityTier[] = ["critical_viral", "high_risk_early", "crowd_anomaly", "low_watch"];

/**
 * Derived on the client like the risk level, with T = T_orange and N = 5 (contract v3):
 * crowd_anomaly = the model scored it low but many people reported it: a possible false negative.
 */
export function deriveTier(riskScore: number, reports: number, t: Thresholds, n: number = REPORTS_N): PriorityTier {
  if (riskScore >= t.orange) return reports >= n ? "critical_viral" : "high_risk_early";
  return reports >= n ? "crowd_anomaly" : "low_watch";
}

/** Same formula as the server: min(100, risk × (1 + 0.25 × log2(1 + reports))). */
export function priorityScore(riskScore: number, reports: number): number {
  return Math.min(100, riskScore * (1 + 0.25 * Math.log2(1 + Math.max(0, reports))));
}

export const reportsOf = (it: Pick<IncidentSummary, "user_reports_count">): number => it.user_reports_count ?? 0;

export function priorityOf(it: Pick<IncidentSummary, "risk_score" | "user_reports_count" | "priority_score">): number {
  return typeof it.priority_score === "number" ? it.priority_score : priorityScore(it.risk_score, reportsOf(it));
}

export function tierOf(it: Pick<IncidentSummary, "risk_score" | "user_reports_count">, t: Thresholds): PriorityTier {
  return deriveTier(it.risk_score, reportsOf(it), t);
}
