import { describe, expect, it } from "vitest";
import { bestF1Threshold, confusionAt, histogram, metricsAt, metricsCurve, misclassifiedAt } from "../../src/domain/calibration";
import type { CalibrationItem } from "../../src/types/api";
import { calibrationSet } from "../fixtures/data.mjs";

const item = (risk_score: number, ground_truth: "violation" | "ok", id = `${risk_score}-${ground_truth}`): CalibrationItem => ({
  id, title: id, risk_score, ground_truth, module: 1,
});

// 4 violations (90, 75, 60, 30) and 4 ok (80, 50, 20, 10)
const SET = [item(90, "violation"), item(75, "violation"), item(60, "violation"), item(30, "violation"), item(80, "ok"), item(50, "ok"), item(20, "ok"), item(10, "ok")];

describe("confusionAt", () => {
  it("counts TP/FP/FN/TN at threshold 70", () => {
    expect(confusionAt(SET, 70)).toEqual({ tp: 2, fp: 1, fn: 2, tn: 3 });
  });
  it("counts at threshold 50 (boundary is inclusive)", () => {
    expect(confusionAt(SET, 50)).toEqual({ tp: 3, fp: 2, fn: 1, tn: 2 });
  });
  it("counts at the default flag threshold 20 (boundary is inclusive: the 20 ok item is a false positive)", () => {
    expect(confusionAt(SET, 20)).toEqual({ tp: 4, fp: 3, fn: 0, tn: 1 });
  });
  it("counts at flag thresholds 35 and 31 on the shared overlap", () => {
    expect(confusionAt(SET, 35)).toEqual({ tp: 3, fp: 2, fn: 1, tn: 2 });
    expect(confusionAt(SET, 31)).toEqual({ tp: 3, fp: 2, fn: 1, tn: 2 });
    expect(confusionAt(SET, 30)).toEqual({ tp: 4, fp: 2, fn: 0, tn: 2 });
  });
  it("flags everything at 0 and nothing above the maximum", () => {
    expect(confusionAt(SET, 0)).toEqual({ tp: 4, fp: 4, fn: 0, tn: 0 });
    expect(confusionAt(SET, 91)).toEqual({ tp: 0, fp: 0, fn: 4, tn: 4 });
  });
  it("always sums to the set size", () => {
    for (const t of [0, 13, 35, 70, 100]) {
      const c = confusionAt(calibrationSet.items, t);
      expect(c.tp + c.fp + c.fn + c.tn).toBe(calibrationSet.items.length);
    }
  });
});

describe("calibration fixtures", () => {
  const scoresOf = (gt: string) => calibrationSet.items.filter((i) => i.ground_truth === gt).map((i) => i.risk_score).sort((a, b) => a - b);
  it("overlap around 15–35 so the trade-off is visible at the default flag threshold", () => {
    const v = scoresOf("violation");
    const ok = scoresOf("ok");
    expect(v[0]).toBeLessThanOrEqual(20);
    expect(Math.max(...ok)).toBeGreaterThanOrEqual(25);
    expect(Math.max(...ok)).toBeLessThanOrEqual(35);
    const atDefault = metricsAt(calibrationSet.items, 20);
    const stricter = metricsAt(calibrationSet.items, 35);
    expect(atDefault.fp).toBeGreaterThan(0);
    expect(atDefault.fn).toBeGreaterThan(0);
    expect(stricter.fn).toBeGreaterThan(atDefault.fn);
    expect(stricter.fp).toBeLessThan(atDefault.fp);
  });
});

describe("metricsAt", () => {
  it("computes precision, recall and F1", () => {
    const m = metricsAt(SET, 70);
    expect(m.precision).toBeCloseTo(2 / 3);
    expect(m.recall).toBeCloseTo(0.5);
    expect(m.f1).toBeCloseTo((2 * (2 / 3) * 0.5) / (2 / 3 + 0.5));
  });
  it("gives recall 1 at threshold 0 and precision equal to the base rate", () => {
    const m = metricsAt(SET, 0);
    expect(m.recall).toBe(1);
    expect(m.precision).toBe(0.5);
  });
  it("returns null precision when nothing is flagged, never NaN", () => {
    const m = metricsAt(SET, 95);
    expect(m.precision).toBeNull();
    expect(m.recall).toBe(0);
    expect(m.f1).toBeNull();
  });
  it("returns null recall when the set has no violations", () => {
    expect(metricsAt([item(80, "ok")], 50).recall).toBeNull();
  });
  it("handles an empty set", () => {
    expect(metricsAt([], 50)).toEqual({ tp: 0, fp: 0, fn: 0, tn: 0, precision: null, recall: null, f1: null });
  });
});

describe("metricsCurve", () => {
  it("has one point per threshold 0–100 with non-increasing recall", () => {
    const curve = metricsCurve(calibrationSet.items);
    expect(curve).toHaveLength(101);
    for (let i = 1; i < curve.length; i += 1) {
      expect(curve[i]?.recall ?? 0).toBeLessThanOrEqual(curve[i - 1]?.recall ?? 0);
    }
  });
  it("finds the threshold with the best F1", () => {
    // 21–30 flags all four violations plus two ok items: F1 = 0.8, the maximum; ties resolve to the lowest threshold
    expect(bestF1Threshold(SET)).toBe(21);
    expect(metricsAt(SET, 21).f1).toBeCloseTo(0.8);
    expect(bestF1Threshold([])).toBeNull();
  });
});

describe("histogram", () => {
  it("splits scores into ten bins by ground truth", () => {
    const bins = histogram(SET);
    expect(bins).toHaveLength(10);
    expect(bins[9]).toMatchObject({ from: 90, to: 100, violation: 1, ok: 0 });
    expect(bins[8]).toMatchObject({ violation: 0, ok: 1 });
    expect(bins.reduce((n, b) => n + b.violation + b.ok, 0)).toBe(SET.length);
  });
  it("puts a score of exactly 100 in the last bin", () => {
    expect(histogram([item(100, "violation")])[9]?.violation).toBe(1);
  });
});

describe("misclassifiedAt", () => {
  it("lists false positives and false negatives, highest risk first", () => {
    const { falsePositives, falseNegatives } = misclassifiedAt(SET, 70);
    expect(falsePositives.map((i) => i.risk_score)).toEqual([80]);
    expect(falseNegatives.map((i) => i.risk_score)).toEqual([60, 30]);
  });
  it("moves cases between the lists as the threshold moves", () => {
    expect(misclassifiedAt(SET, 25).falsePositives.map((i) => i.risk_score)).toEqual([80, 50]);
    expect(misclassifiedAt(SET, 25).falseNegatives).toEqual([]);
  });
});
