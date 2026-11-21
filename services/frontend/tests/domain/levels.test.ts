import { describe, expect, it } from "vitest";
import { complianceScore, countLevels, DEFAULT_THRESHOLDS, deriveLevel, normalizeThresholds } from "../../src/domain/levels";

describe("deriveLevel", () => {
  it("uses the contract defaults (red >= 70, orange >= 35)", () => {
    expect(DEFAULT_THRESHOLDS).toEqual({ red: 70, orange: 35 });
    expect(deriveLevel(70)).toBe("red");
    expect(deriveLevel(69.9)).toBe("orange");
    expect(deriveLevel(35)).toBe("orange");
    expect(deriveLevel(34.9)).toBe("green");
    expect(deriveLevel(0)).toBe("green");
    expect(deriveLevel(100)).toBe("red");
  });

  it("follows custom thresholds", () => {
    expect(deriveLevel(58, { red: 50, orange: 20 })).toBe("red");
    expect(deriveLevel(58, { red: 90, orange: 60 })).toBe("green");
    expect(deriveLevel(58, { red: 90, orange: 58 })).toBe("orange");
  });

  it("treats equal thresholds as no orange band", () => {
    expect(deriveLevel(50, { red: 50, orange: 50 })).toBe("red");
    expect(deriveLevel(49, { red: 50, orange: 50 })).toBe("green");
  });
});

describe("complianceScore", () => {
  it("is 100 minus the risk score", () => {
    expect(complianceScore(8)).toBe(92);
    expect(complianceScore(89)).toBe(11);
    expect(complianceScore(57.6)).toBe(42);
    expect(complianceScore(140)).toBe(0);
  });
});

describe("normalizeThresholds", () => {
  it("clamps to 0–100 and keeps orange at or below red", () => {
    expect(normalizeThresholds({ red: 140, orange: -5 })).toEqual({ red: 100, orange: 0 });
    expect(normalizeThresholds({ red: 40, orange: 60 })).toEqual({ red: 40, orange: 40 });
    expect(normalizeThresholds({ red: 61.6, orange: 20.2 })).toEqual({ red: 62, orange: 20 });
  });

  it("falls back to defaults for garbage", () => {
    expect(normalizeThresholds({ red: Number.NaN })).toEqual(DEFAULT_THRESHOLDS);
    expect(normalizeThresholds({})).toEqual(DEFAULT_THRESHOLDS);
  });
});

describe("countLevels", () => {
  const scores = [96, 72, 70, 58, 35, 34, 8];
  it("counts at the default thresholds", () => {
    expect(countLevels(scores, DEFAULT_THRESHOLDS)).toEqual({ red: 3, orange: 2, green: 2 });
  });
  it("recounts when the threshold moves", () => {
    expect(countLevels(scores, { red: 50, orange: 35 })).toEqual({ red: 4, orange: 1, green: 2 });
    expect(countLevels(scores, { red: 97, orange: 0 })).toEqual({ red: 0, orange: 7, green: 0 });
  });
});
