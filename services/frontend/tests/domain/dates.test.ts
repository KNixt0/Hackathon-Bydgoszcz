import { describe, expect, it } from "vitest";
import { apiDate, clampDateTime, matchesDates, SYSTEM_START_LOCAL, todayIso, validDateInput, warsawInput } from "../../src/domain/dates";

describe("Warsaw date controls", () => {
  it("uses the fixed 20:50 launch instant and clamps future values", () => {
    expect(apiDate(SYSTEM_START_LOCAL)).toBe("2026-11-21T19:50:00.000Z");
    expect(clampDateTime("2026-11-21T20:49", "2026-11-22T14:00")).toBe(SYSTEM_START_LOCAL);
    expect(clampDateTime("2026-11-23T12:00", "2026-11-22T14:00")).toBe("2026-11-22T14:00");
  });
  it("uses Poland's calendar across midnight and summer time", () => {
    expect(todayIso(new Date("2026-11-21T23:30Z"))).toBe("2026-11-22");
    expect(warsawInput("2026-06-01T10:15Z")).toBe("2026-06-01T12:15");
    expect(apiDate("2026-06-01T12:15")).toBe("2026-06-01T10:15:00.000Z");
    expect(validDateInput("2026-03-29T02:30")).toBe(false);
    expect(validDateInput("2026-02-30T12:00")).toBe(false);
  });
  it("filters exact instants inclusively and supports saved date-only links", () => {
    expect(matchesDates("2026-11-21T19:50:00Z", SYSTEM_START_LOCAL, SYSTEM_START_LOCAL)).toBe(true);
    expect(matchesDates("2026-11-21T19:49:59Z", SYSTEM_START_LOCAL, "")).toBe(false);
    expect(matchesDates("2026-11-21T23:30:00Z", "2026-11-22", "2026-11-22")).toBe(true);
  });
});
