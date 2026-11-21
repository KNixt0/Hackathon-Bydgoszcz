import { describe, expect, it } from "vitest";
import { reportsLabel } from "../../src/domain/format";
import { DEFAULT_THRESHOLDS } from "../../src/domain/levels";
import { deriveTier, priorityScore, REPORTS_N } from "../../src/domain/priority";
import { applyQueue, EMPTY_FILTERS, filtersFromSearch, filtersToApiQuery, filtersToSearch, matchesFilters } from "../../src/domain/queue";
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

describe("queue by tier and priority", () => {
  it("filters by tier and the crowd anomaly exists in the fixtures", () => {
    const anomalies = incidentSummaries.filter((it) => matchesFilters(it, { ...EMPTY_FILTERS, tier: "crowd_anomaly" }, T));
    expect(anomalies.length).toBeGreaterThanOrEqual(2);
    expect(anomalies.every((it) => it.risk_score < 20 && it.user_reports_count >= 5)).toBe(true);
  });

  it("sorts by priority instead of risk, pinned cases stay first", () => {
    const byRisk = applyQueue(incidentSummaries, EMPTY_FILTERS, T);
    const byPriority = applyQueue(incidentSummaries, { ...EMPTY_FILTERS, sort: "priority" }, T);
    expect(byPriority.map((i) => i.id)).not.toEqual(byRisk.map((i) => i.id));
    const scores = byPriority.map((i) => i.priority_score);
    expect(scores).toEqual([...scores].sort((a, b) => b - a));
    const pinned = byPriority[byPriority.length - 1]?.id ?? "";
    expect(applyQueue(incidentSummaries, { ...EMPTY_FILTERS, sort: "priority" }, T, [pinned])[0]?.id).toBe(pinned);
  });

  it("round-trips tier and sort through the URL and sends the sort to the export", () => {
    const f = { ...EMPTY_FILTERS, tier: "crowd_anomaly" as const, sort: "priority" as const };
    expect(filtersFromSearch(filtersToSearch(f))).toEqual(f);
    expect(filtersFromSearch(new URLSearchParams("priorytet=nonsense"))).toEqual(EMPTY_FILTERS);
    expect(filtersToApiQuery(f)).toBe("?sort=priority");
  });
});
