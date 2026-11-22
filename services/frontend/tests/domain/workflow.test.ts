import { describe, expect, it } from "vitest";
import { availableActions, TRANSITIONS } from "../../src/domain/workflow";
import type { Role, Status } from "../../src/types/incident";

const ids = (status: Status, role: Role, assigned: string | null = "a@x") => availableActions(status, role, assigned, "a@x").map((a) => a.id);

describe("workflow actions", () => {
  it("offers only transitions the server allows", () => {
    for (const status of Object.keys(TRANSITIONS) as Status[]) {
      for (const role of ["ANALYST", "SUPERVISOR"] as Role[]) {
        for (const a of availableActions(status, role, null, "a@x")) if (a.to) expect(TRANSITIONS[status]).toContain(a.to);
      }
    }
  });

  it("approval is the supervisor's; closed cases have no actions", () => {
    expect(ids("escalation_requested", "ANALYST")).toEqual(["withdraw_escalation"]);
    expect(ids("escalation_requested", "SUPERVISOR")).toEqual(["approve_escalation", "reject_escalation"]);
    expect(ids("resolved", "SUPERVISOR", null)).toEqual([]);
    expect(ids("false_positive", "ANALYST", null)).toEqual([]);
    expect(ids("new", "ANALYST", null)).toEqual(["assign", "start"]);
    expect(ids("in_review", "ANALYST")).toEqual(["request_escalation", "record_intervention", "close_violation", "close_false_positive"]);
    expect(ids("awaiting_correction", "ANALYST")).toEqual(["close_after_follow_up", "reopen_review", "request_escalation"]);
  });

  it("closing and recording an intervention always ask for a required reason", () => {
    for (const a of availableActions("escalated", "SUPERVISOR", "a@x", "a@x")) expect(a.dialog?.reason).toBe("required");
    const record = availableActions("in_review", "ANALYST", "a@x", "a@x").find((a) => a.id === "record_intervention");
    expect(record?.to).toBe("awaiting_correction");
    expect(record?.dialog?.followUpDays).toBe(true);
  });
});
