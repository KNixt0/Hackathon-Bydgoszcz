import { describe, expect, it } from "vitest";
import { apiDate, defaultDateBounds, matchesDates, processingDuration, warsawInput, warsawInstant } from "../../src/domain/dates";

describe("monitoring dates", () => {
  it("uses the latest 20:50 in Warsaw and does not choose a future start", () => {
    const before = defaultDateBounds(new Date("2026-11-22T01:00:00Z"));
    expect(warsawInput(before.earliest)).toBe("2026-11-21T20:50");
    const after = defaultDateBounds(new Date("2026-11-22T21:00:00Z"));
    expect(warsawInput(after.earliest)).toBe("2026-11-22T20:50");
  });
  it("interprets local fields in Warsaw in summer and winter", () => {
    expect(new Date(warsawInstant("2026-11-21T20:50")).toISOString()).toBe("2026-11-21T19:50:00.000Z");
    expect(apiDate("2026-07-01T20:50")).toBe("2026-07-01T18:50:00.000Z");
    expect(matchesDates("2026-11-21T19:49:00Z", "2026-11-21T20:50", "")).toBe(false);
  });
  it("counts from persisted start and stops at case completion", () => {
    expect(processingDuration(null)).toBe("Nie rozpoczęto");
    expect(processingDuration("2026-11-21T20:00:00Z", null, Date.parse("2026-11-21T21:05:00Z"))).toBe("1 godz. 5 min");
    expect(processingDuration("2026-11-21T20:00:00Z", "2026-11-21T20:05:00Z", Date.parse("2026-11-25T00:00:00Z"))).toBe("5 min");
  });
});
