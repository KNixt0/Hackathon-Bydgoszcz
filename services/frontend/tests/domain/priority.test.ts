import { describe, expect, it } from "vitest";
import { reportsLabel } from "../../src/domain/format";
import { DEFAULT_THRESHOLDS } from "../../src/domain/levels";
import { deriveTier, priorityScore, REPORTS_N } from "../../src/domain/priority";
import { applyQueue, EMPTY_FILTERS, filtersFromSearch } from "../../src/domain/queue";
import { incidentSummaries } from "../fixtures/data.mjs";

const T = DEFAULT_THRESHOLDS; // orange = 20

describe("priority tier (T = T_orange, N = 5)", () => {
  it.each([
    [19.9, 0, "low_watch"],
    [19.9, 4, "low_watch"],
    [19.9, 5, "crowd_anomaly"],
    [0, 40, "crowd_anomaly"],
    [20, 0, "high_risk_early"],
    [20, 4, "high_risk_early"],
    [20, 5, "critical_viral"],
    [95, 4, "high_risk_early"],
    [95, 120, "critical_viral"],
  ] as const)("risk %s with %s reports is %s", (risk, reports, tier) => {
    expect(deriveTier(risk, reports, T)).toBe(tier);
  });

  it("follows the analyst's orange threshold", () => {
    expect(deriveTier(30, 6, { red: 70, orange: 20 })).toBe("critical_viral");
    expect(deriveTier(30, 6, { red: 70, orange: 35 })).toBe("crowd_anomaly");
    expect(REPORTS_N).toBe(5);
  });

  it("computes the contract's priority score", () => {
    expect(priorityScore(80, 0)).toBe(80);
    expect(priorityScore(40, 3)).toBeCloseTo(40 * 1.5);
    expect(priorityScore(90, 50)).toBe(100);
  });

  it("writes Polish plurals", () => {
    expect([1, 2, 4, 5, 12, 22, 25].map(reportsLabel)).toEqual([
      "1 zgłoszenie", "2 zgłoszenia", "4 zgłoszenia", "5 zgłoszeń", "12 zgłoszeń", "22 zgłoszenia", "25 zgłoszeń",
    ]);
  });
});

describe("queue after public reports were removed", () => {
  it("ignores old report filters and uses the model risk", () => {
    expect(filtersFromSearch(new URLSearchParams("priorytet=crowd_anomaly&sortowanie=priorytet"))).toEqual(EMPTY_FILTERS);
    const risk = applyQueue(incidentSummaries, EMPTY_FILTERS, T);
    expect(applyQueue(incidentSummaries, { ...EMPTY_FILTERS, sort: "priority" }, T)).toEqual(risk);
  });
});
