import type { RiskLevel } from "../types/incident";

export interface Thresholds {
  /** risk_score >= red → "red" */
  red: number;
  /** risk_score >= orange (and < red) → "orange"; also the flag threshold: flagged = risk_score >= orange */
  orange: number;
}

export const DEFAULT_THRESHOLDS: Thresholds = { red: 70, orange: 20 };

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n));

/** Keeps both thresholds inside 0–100 and orange never above red. */
export function normalizeThresholds(t: Partial<Thresholds>): Thresholds {
  const red = clamp(Math.round(Number.isFinite(t.red) ? (t.red as number) : DEFAULT_THRESHOLDS.red), 0, 100);
  const orangeRaw = Number.isFinite(t.orange) ? (t.orange as number) : DEFAULT_THRESHOLDS.orange;
  const orange = clamp(Math.round(orangeRaw), 0, red);
  return { red, orange };
}

/** The level is derived, never stored: it follows the analyst's thresholds. */
export function deriveLevel(riskScore: number, t: Thresholds = DEFAULT_THRESHOLDS): RiskLevel {
  if (riskScore >= t.red) return "red";
  if (riskScore >= t.orange) return "orange";
  return "green";
}

export function complianceScore(riskScore: number): number {
  return Math.round(clamp(100 - riskScore, 0, 100));
}

/** "Flagged" (a detection in the calibration panel) = orange or red = risk_score >= T_orange. */
export function isFlagged(riskScore: number, t: Thresholds = DEFAULT_THRESHOLDS): boolean {
  return riskScore >= t.orange;
}

export const LEVEL_ORDER: Record<RiskLevel, number> = { red: 0, orange: 1, green: 2 };
export const LEVELS: RiskLevel[] = ["red", "orange", "green"];

export type LevelCounts = Record<RiskLevel, number>;

export function countLevels(scores: number[], t: Thresholds): LevelCounts {
  const counts: LevelCounts = { red: 0, orange: 0, green: 0 };
  for (const s of scores) counts[deriveLevel(s, t)] += 1;
  return counts;
}
