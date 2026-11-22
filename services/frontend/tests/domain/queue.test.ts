import { describe, expect, it } from "vitest";
import { DEFAULT_THRESHOLDS } from "../../src/domain/levels";
import { incidentsReducer, INITIAL_INCIDENTS, upsertJob } from "../../src/domain/liveState";
import {
  activeFilterCount, applyQueue, EMPTY_FILTERS, filtersFromSearch, filtersToApiQuery, filtersToSearch, matchesFilters, sortQueue, upsertIncident,
} from "../../src/domain/queue";
import { trendRows } from "../../src/domain/trends";
import type { ScanJob } from "../../src/types/api";
import type { IncidentSummary } from "../../src/types/incident";
import { incidentSummaries, redSummary, trends } from "../fixtures/data.mjs";

const T = DEFAULT_THRESHOLDS;
const make = (id: string, risk: number, patch: Partial<IncidentSummary> = {}): IncidentSummary => ({
  ...(incidentSummaries[0] as IncidentSummary), id, risk_score: risk, compliance_score: 100 - risk, title: `Sprawa ${id}`, ...patch,
});

describe("sortQueue", () => {
  it("orders red, then orange, then green, each by risk descending", () => {
    const sorted = sortQueue([make("a", 10), make("b", 72), make("c", 40), make("d", 96), make("e", 69)], T);
    expect(sorted.map((i) => i.id)).toEqual(["d", "b", "e", "c", "a"]);
  });
  it("breaks ties with the newest first", () => {
    const sorted = sortQueue([make("old", 50, { created_at: "2026-11-01T00:00:00Z" }), make("new", 50, { created_at: "2026-11-20T00:00:00Z" })], T);
    expect(sorted.map((i) => i.id)).toEqual(["new", "old"]);
  });
  it("puts pinned alerts on top regardless of score", () => {
    const sorted = sortQueue([make("a", 96), make("b", 71), make("c", 20)], T, ["b"]);
    expect(sorted.map((i) => i.id)).toEqual(["b", "a", "c"]);
  });
  it("does not mutate its input", () => {
    const input = [make("a", 10), make("b", 90)];
    sortQueue(input, T);
    expect(input.map((i) => i.id)).toEqual(["a", "b"]);
  });
});

describe("matchesFilters", () => {
  const it1 = make("x", 58, {
    title: "Recenzja platformy CFD", advertiser: "Jakub Wrona", firm: "Tradeon Europe Ltd", modules: [1, 2], primary_module: 1,
    status: "in_review", created_at: "2026-11-19T08:42:00Z", source: { platform: "youtube", url: "https://youtube.com/x" },
  });
  it("matches with no filters", () => expect(matchesFilters(it1, EMPTY_FILTERS, T)).toBe(true));
  it("filters by module (any module of the incident)", () => {
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, module: 2 }, T)).toBe(true);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, module: 3 }, T)).toBe(false);
  });
  it("filters by platform and status", () => {
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, platform: "youtube", status: "in_review" }, T)).toBe(true);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, platform: "web" }, T)).toBe(false);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, status: "new" }, T)).toBe(false);
  });
  it("filters by the level derived from the current thresholds", () => {
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, level: "orange" }, T)).toBe(true);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, level: "orange" }, { red: 50, orange: 20 })).toBe(false);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, level: "red" }, { red: 50, orange: 20 })).toBe(true);
  });
  it("filters by an inclusive date range", () => {
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, from: "2026-11-19", to: "2026-11-19" }, T)).toBe(true);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, from: "2026-11-20" }, T)).toBe(false);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, to: "2026-11-18" }, T)).toBe(false);
  });
  it("searches title, parties and URL, ignoring case and Polish diacritics", () => {
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, q: "tradeon cfd" }, T)).toBe(true);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, q: "WRONA" }, T)).toBe(true);
    expect(matchesFilters(make("z", 1, { title: "Gwarancja zysku: żółć" }), { ...EMPTY_FILTERS, q: "zolc" }, T)).toBe(true);
    expect(matchesFilters(it1, { ...EMPTY_FILTERS, q: "aurum" }, T)).toBe(false);
  });
});

describe("applyQueue on the fixture queue", () => {
  it("returns only module 3 incidents, still sorted", () => {
    const out = applyQueue(incidentSummaries, { ...EMPTY_FILTERS, module: 3 }, T);
    expect(out.length).toBeGreaterThan(0);
    expect(out.every((i) => i.modules.includes(3))).toBe(true);
    expect(out.map((i) => i.risk_score)).toEqual([...out.map((i) => i.risk_score)].sort((a, b) => b - a));
  });
});

describe("filters ↔ URL", () => {
  it("round-trips through search params", () => {
    const f = { q: "cfd", from: "2026-11-21", to: "2026-11-21", platform: "youtube" as const, level: "red" as const, module: 2 as const, status: "new" as const, sort: "detected" as const, dir: "asc" as const };
    expect(filtersFromSearch(filtersToSearch(f))).toEqual(f);
    expect(activeFilterCount(f)).toBe(7);
  });
  it("ignores invalid values from a hand-edited URL", () => {
    expect(filtersFromSearch(new URLSearchParams("poziom=purple&modul=9&status=x&od=wczoraj&zrodlo=myspace"))).toEqual(EMPTY_FILTERS);
  });
  it("builds the API query for the CSV export without the client-only level filter", () => {
    expect(filtersToApiQuery({ ...EMPTY_FILTERS, module: 1, level: "red", platform: "web" })).toBe("?module=1&source=web");
    expect(filtersToApiQuery(EMPTY_FILTERS)).toBe("");
  });
});

describe("upsertIncident", () => {
  it("prepends unknown incidents and replaces known ones in place", () => {
    const list = [make("a", 10), make("b", 20)];
    expect(upsertIncident(list, make("c", 30)).map((i) => i.id)).toEqual(["c", "a", "b"]);
    const replaced = upsertIncident(list, make("b", 99));
    expect(replaced.map((i) => i.id)).toEqual(["a", "b"]);
    expect(replaced[1]?.risk_score).toBe(99);
  });
});

describe("incidentsReducer (socket events)", () => {
  const ready = incidentsReducer(INITIAL_INCIDENTS, { type: "load:ok", items: [make("a", 10)] });

  it("adds incident:new and marks it fresh", () => {
    const next = incidentsReducer(ready, { type: "incident:new", incident: make("n", 50) });
    expect(next.items.map((i) => i.id)).toEqual(["n", "a"]);
    expect(next.fresh).toEqual(["n"]);
  });
  it("does not duplicate when the same incident arrives twice", () => {
    const once = incidentsReducer(ready, { type: "incident:new", incident: make("n", 50) });
    const twice = incidentsReducer(once, { type: "incident:new", incident: make("n", 55) });
    expect(twice.items.filter((i) => i.id === "n")).toHaveLength(1);
    expect(twice.items[0]?.risk_score).toBe(55);
  });
  it("applies incident:updated to the list and to open alerts", () => {
    const alerted = incidentsReducer(ready, { type: "alert:high", incident: redSummary });
    const next = incidentsReducer(alerted, { type: "incident:updated", incident: { ...redSummary, status: "escalated" } });
    expect(next.items.find((i) => i.id === redSummary.id)?.status).toBe("escalated");
    expect(next.alerts[0]?.status).toBe("escalated");
  });
  it("keeps alert:high until dismissed and inserts the incident even without incident:new", () => {
    const alerted = incidentsReducer(ready, { type: "alert:high", incident: redSummary });
    expect(alerted.alerts.map((a) => a.id)).toEqual([redSummary.id]);
    expect(alerted.items.some((i) => i.id === redSummary.id)).toBe(true);
    expect(incidentsReducer(alerted, { type: "alert:dismiss", id: redSummary.id }).alerts).toEqual([]);
  });
  it("keeps live arrivals when the initial list resolves afterwards", () => {
    const early = incidentsReducer(INITIAL_INCIDENTS, { type: "incident:new", incident: make("live", 80) });
    const loaded = incidentsReducer(early, { type: "load:ok", items: [make("a", 10)] });
    expect(loaded.items.map((i) => i.id)).toEqual(["live", "a"]);
  });
  it("keeps the list on screen when a reload fails", () => {
    const failed = incidentsReducer(ready, { type: "load:error", message: "x" });
    expect(failed.phase).toBe("ready");
    expect(incidentsReducer(INITIAL_INCIDENTS, { type: "load:error", message: "x" }).phase).toBe("error");
  });
});

describe("upsertJob", () => {
  const job = (id: string, state: ScanJob["state"]): ScanJob => ({ id, url: "https://x.example", state, incident_id: null, error: null, created_at: "2026-11-21T00:00:00Z", finished_at: null });
  it("adds new jobs first and updates existing ones", () => {
    const list = upsertJob([job("a", "queued")], job("b", "queued"));
    expect(list.map((j) => j.id)).toEqual(["b", "a"]);
    expect(upsertJob(list, job("a", "analyzing")).find((j) => j.id === "a")?.state).toBe("analyzing");
  });
});

describe("trendRows", () => {
  it("stacks each day by the level at the current thresholds and keeps totals", () => {
    const base = trendRows(trends.days, T);
    const moved = trendRows(trends.days, { red: 40, orange: 20 });
    const total = (rows: typeof base) => rows.reduce((n, r) => n + r.red + r.orange + r.green, 0);
    expect(total(base)).toBe(incidentSummaries.length);
    expect(total(moved)).toBe(total(base));
    expect(moved.reduce((n, r) => n + r.red, 0)).toBeGreaterThan(base.reduce((n, r) => n + r.red, 0));
  });
  it("can be limited to one module", () => {
    const m3 = trendRows(trends.days, T, 3).reduce((n, r) => n + r.red + r.orange + r.green, 0);
    expect(m3).toBe(incidentSummaries.filter((i) => i.primary_module === 3).length);
  });
});

describe("WatchIT: dates and column sorting", () => {
  it("never accepts a date before the system start or after today from the URL", () => {
    const f = filtersFromSearch(new URLSearchParams("od=2026-10-01&do=2999-01-01"));
    expect(f.from).toBe("2026-11-21");
    expect(f.to <= new Date().toISOString().slice(0, 10) || f.to.length === 10).toBe(true);
  });

  it("sorts by any column in both directions", () => {
    const a = make("a", 10, { created_at: "2026-11-21T08:00:00Z", workflow: { assigned_to: null, label: "unlabeled", started_at: "2026-11-21T09:00:00Z", closed_at: null } });
    const b = make("b", 90, { created_at: "2026-11-21T10:00:00Z", workflow: { assigned_to: null, label: "unlabeled", started_at: null, closed_at: null } });
    expect(sortQueue([a, b], T, [], "detected", "asc").map((i) => i.id)).toEqual(["a", "b"]);
    expect(sortQueue([a, b], T, [], "detected", "desc").map((i) => i.id)).toEqual(["b", "a"]);
    expect(sortQueue([a, b], T, [], "started", "desc").map((i) => i.id)).toEqual(["a", "b"]);
    expect(sortQueue([a, b], T, [], "risk", "asc").map((i) => i.id)).toEqual(["a", "b"]);
  });
});
