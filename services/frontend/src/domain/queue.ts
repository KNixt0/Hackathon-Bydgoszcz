import type { IncidentSummary, ModuleId, Platform, RiskLevel, Status } from "../types/incident";
import { apiDate, clampDate, clampDateTime, matchesDates, validDateInput } from "./dates";
import { deriveLevel, LEVEL_ORDER, type Thresholds } from "./levels";
/** Sortable columns of the queue table (WatchIt: every header sorts, ascending or descending). */
export type SortKey = "risk" | "id" | "title" | "source" | "module" | "rules" | "status" | "detected" | "started";
export type SortDir = "asc" | "desc";
export const SORT_KEYS: SortKey[] = ["risk", "id", "title", "source", "module", "rules", "status", "detected", "started"];

export interface QueueFilters {
  q: string;
  from: string; // YYYY-MM-DD or ""
  to: string;
  platform: Platform | "";
  level: RiskLevel | "";
  module: ModuleId | 0;
  status: Status | "";
  /** column the table is sorted by; "risk" (default) = level, then raw risk, then newest */
  sort: SortKey;
  dir: SortDir;
}

export const EMPTY_FILTERS: QueueFilters = { q: "", from: "", to: "", platform: "", level: "", module: 0, status: "", sort: "risk", dir: "desc" };

/** Sorting is not a filter: only these narrow the list. */
export function activeFilterCount(f: QueueFilters): number {
  return [f.q, f.from, f.to, f.platform, f.level, f.module ? "m" : "", f.status].filter(Boolean).length;
}

const fold = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ł/g, "l");

export function matchesFilters(it: IncidentSummary, f: QueueFilters, t: Thresholds): boolean {
  if (f.platform && it.source.platform !== f.platform) return false;
  if (f.module && !it.modules.includes(f.module) && it.primary_module !== f.module) return false;
  if (f.status && it.status !== f.status) return false;
  if (f.level && deriveLevel(it.risk_score, t) !== f.level) return false;
  if (!matchesDates(it.created_at, f.from, f.to)) return false;
  if (f.q.trim()) {
    const hay = fold([it.title, it.summary, it.advertiser ?? "", it.firm ?? "", it.source.url].join(" "));
    const words = fold(f.q).split(/\s+/).filter(Boolean);
    if (!words.every((w) => hay.includes(w))) return false;
  }
  return true;
}

const STATUS_ORDER: Record<Status, number> = {
  new: 0, in_review: 1, escalation_requested: 2, escalated: 3, awaiting_correction: 4, resolved: 5, false_positive: 6,
};

function compareBy(key: SortKey, a: IncidentSummary, b: IncidentSummary, t: Thresholds): number {
  switch (key) {
    case "risk": {
      const levels = LEVEL_ORDER[deriveLevel(b.risk_score, t)] - LEVEL_ORDER[deriveLevel(a.risk_score, t)];
      return levels !== 0 ? levels : a.risk_score - b.risk_score;
    }
    case "id": return a.id.localeCompare(b.id);
    case "title": return a.title.localeCompare(b.title, "pl");
    case "source": return a.source.platform.localeCompare(b.source.platform) || a.source.url.localeCompare(b.source.url);
    case "module": return a.primary_module - b.primary_module;
    case "rules": return a.failed_rules.length - b.failed_rules.length;
    case "status": return STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
    case "detected": return a.created_at.localeCompare(b.created_at);
    case "started": {
      const sa = a.workflow?.started_at ?? "";
      const sb = b.workflow?.started_at ?? "";
      if (!sa || !sb) return sa ? 1 : sb ? -1 : 0; // never started sorts as the earliest
      return sa.localeCompare(sb);
    }
  }
}

/** Pinned alerts first, then the chosen column in the chosen direction; ties: higher risk, then newest. */
export function sortQueue(
  items: IncidentSummary[],
  t: Thresholds,
  pinned: readonly string[] = [],
  sort: SortKey = "risk",
  dir: SortDir = "desc",
): IncidentSummary[] {
  const pinRank = new Map(pinned.map((id, i) => [id, i]));
  const sign = dir === "asc" ? 1 : -1;
  return [...items].sort((a, b) => {
    const pa = pinRank.get(a.id);
    const pb = pinRank.get(b.id);
    if (pa !== undefined || pb !== undefined) {
      if (pa === undefined) return 1;
      if (pb === undefined) return -1;
      return pa - pb;
    }
    const primary = compareBy(sort, a, b, t) * sign;
    if (primary !== 0) return primary;
    if (a.risk_score !== b.risk_score) return b.risk_score - a.risk_score;
    return b.created_at.localeCompare(a.created_at);
  });
}

export function applyQueue(
  items: IncidentSummary[],
  f: QueueFilters,
  t: Thresholds,
  pinned: readonly string[] = [],
): IncidentSummary[] {
  return sortQueue(items.filter((it) => matchesFilters(it, f, t)), t, pinned, f.sort, f.dir);
}

/** Insert or replace by id (socket events may repeat or arrive before the list). */
export function upsertIncident(items: IncidentSummary[], next: IncidentSummary): IncidentSummary[] {
  const idx = items.findIndex((it) => it.id === next.id);
  if (idx === -1) return [next, ...items];
  const copy = [...items];
  copy[idx] = next;
  return copy;
}

export function filtersToSearch(f: QueueFilters): URLSearchParams {
  const p = new URLSearchParams();
  if (f.q) p.set("q", f.q);
  if (f.from) p.set("od", f.from);
  if (f.to) p.set("do", f.to);
  if (f.platform) p.set("zrodlo", f.platform);
  if (f.level) p.set("poziom", f.level);
  if (f.module) p.set("modul", String(f.module));
  if (f.status) p.set("status", f.status);
  if (f.sort !== "risk" || f.dir !== "desc") {
    p.set("sortuj", f.sort);
    p.set("kierunek", f.dir === "asc" ? "rosnaco" : "malejaco");
  }
  return p;
}

const PLATFORMS: Platform[] = ["web", "youtube", "instagram", "facebook", "tiktok", "x", "google_ads", "sample"];
const STATUSES: Status[] = ["new", "in_review", "escalation_requested", "escalated", "awaiting_correction", "resolved", "false_positive"];
const LEVELS: RiskLevel[] = ["red", "orange", "green"];
const clampFilter = (value: string) => value.length === 10 ? clampDate(value) : clampDateTime(value);

function oneOf<T extends string>(value: string | null, allowed: readonly T[]): T | "" {
  return value && (allowed as readonly string[]).includes(value) ? (value as T) : "";
}

export function filtersFromSearch(p: URLSearchParams): QueueFilters {
  const m = Number(p.get("modul"));
  const from = p.get("od") ?? "";
  const to = p.get("do") ?? "";
  return {
    q: p.get("q") ?? "",
    from: validDateInput(from) ? clampFilter(from) : "",
    to: validDateInput(to) ? clampFilter(to) : "",
    platform: oneOf(p.get("zrodlo"), PLATFORMS),
    level: oneOf(p.get("poziom"), LEVELS),
    module: m === 1 || m === 2 || m === 3 ? m : 0,
    status: oneOf(p.get("status"), STATUSES),
    sort: oneOf(p.get("sortuj"), SORT_KEYS) || "risk",
    dir: p.get("kierunek") === "rosnaco" ? "asc" : "desc",
  };
}

/** Query string for the server-side CSV export (the API has no level filter). */
export function filtersToApiQuery(f: QueueFilters): string {
  const p = new URLSearchParams();
  if (f.module) p.set("module", String(f.module));
  if (f.platform) p.set("source", f.platform);
  if (f.status) p.set("status", f.status);
  if (f.from) p.set("from", apiDate(f.from));
  if (f.to) p.set("to", apiDate(f.to));
  if (f.q) p.set("q", f.q);
  const s = p.toString();
  return s ? `?${s}` : "";
}
