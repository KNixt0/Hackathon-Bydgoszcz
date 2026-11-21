import type { CalibrationItem } from "../types/api";

export interface Confusion {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
}

export interface Metrics extends Confusion {
  /** null when undefined (no flagged items / no real violations) */
  precision: number | null;
  recall: number | null;
  f1: number | null;
}

type Labelled = Pick<CalibrationItem, "risk_score" | "ground_truth">;

/** An item is "flagged" when risk_score >= threshold; callers pass the flag threshold (T_orange). */
export function confusionAt(items: Labelled[], threshold: number): Confusion {
  const c: Confusion = { tp: 0, fp: 0, fn: 0, tn: 0 };
  for (const it of items) {
    const flagged = it.risk_score >= threshold;
    const violation = it.ground_truth === "violation";
    if (flagged && violation) c.tp += 1;
    else if (flagged) c.fp += 1;
    else if (violation) c.fn += 1;
    else c.tn += 1;
  }
  return c;
}

export function metricsAt(items: Labelled[], threshold: number): Metrics {
  const c = confusionAt(items, threshold);
  const precision = c.tp + c.fp > 0 ? c.tp / (c.tp + c.fp) : null;
  const recall = c.tp + c.fn > 0 ? c.tp / (c.tp + c.fn) : null;
  const f1 = precision !== null && recall !== null && precision + recall > 0
    ? (2 * precision * recall) / (precision + recall)
    : null;
  return { ...c, precision, recall, f1 };
}

export interface CurvePoint {
  threshold: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
}

export function metricsCurve(items: Labelled[], step = 1): CurvePoint[] {
  const points: CurvePoint[] = [];
  for (let t = 0; t <= 100; t += step) {
    const m = metricsAt(items, t);
    points.push({ threshold: t, precision: m.precision, recall: m.recall, f1: m.f1 });
  }
  return points;
}

/** Threshold with the highest F1; ties resolved towards the lower threshold (higher recall). */
export function bestF1Threshold(items: Labelled[]): number | null {
  let best: number | null = null;
  let bestF1 = -1;
  for (const p of metricsCurve(items)) {
    if (p.f1 !== null && p.f1 > bestF1) {
      bestF1 = p.f1;
      best = p.threshold;
    }
  }
  return best;
}

export interface HistogramBin {
  from: number;
  to: number;
  label: string;
  violation: number;
  ok: number;
}

export function histogram(items: Labelled[], binSize = 10): HistogramBin[] {
  const bins: HistogramBin[] = [];
  for (let from = 0; from < 100; from += binSize) {
    const to = Math.min(100, from + binSize);
    bins.push({ from, to, label: `${from}–${to}`, violation: 0, ok: 0 });
  }
  for (const it of items) {
    const idx = Math.min(bins.length - 1, Math.max(0, Math.floor(it.risk_score / binSize)));
    const bin = bins[idx];
    if (!bin) continue;
    if (it.ground_truth === "violation") bin.violation += 1;
    else bin.ok += 1;
  }
  return bins;
}

export interface Misclassified<T> {
  falsePositives: T[];
  falseNegatives: T[];
}

export function misclassifiedAt<T extends Labelled>(items: T[], threshold: number): Misclassified<T> {
  const falsePositives = items
    .filter((it) => it.risk_score >= threshold && it.ground_truth === "ok")
    .sort((a, b) => b.risk_score - a.risk_score);
  const falseNegatives = items
    .filter((it) => it.risk_score < threshold && it.ground_truth === "violation")
    .sort((a, b) => b.risk_score - a.risk_score);
  return { falsePositives, falseNegatives };
}
