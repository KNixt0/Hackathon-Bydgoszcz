import type { IncidentSummary, ModuleId, Platform, RiskLevel, Status } from "../types/incident";
import { deriveLevel, LEVEL_ORDER, type Thresholds } from "./levels";

export interface QueueFilters {
  q: string;
  from: string; // YYYY-MM-DD or ""
  to: string;
  platform: Platform | "";
  level: RiskLevel | "";
  module: ModuleId | 0;
  status: Status | "";
}

export const EMPTY_FILTERS: QueueFilters = { q: "", from: "", to: "", platform: "", level: "", module: 0, status: "" };

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
  const day = it.created_at.slice(0, 10);
  if (f.from && day < f.from) return false;
  if (f.to && day > f.to) return false;
  if (f.q.trim()) {
    const hay = fold([it.title, it.summary, it.advertiser ?? "", it.firm ?? "", it.source.url].join(" "));
    const words = fold(f.q).split(/\s+/).filter(Boolean);
    if (!words.every((w) => hay.includes(w))) return false;
  }
  return true;
}

/** Most dangerous first: pinned alerts, then red → orange → green, then raw risk, then newest. */
export function sortQueue(items: IncidentSummary[], t: Thresholds, pinned: readonly string[] = []): IncidentSummary[] {
  const pinRank = new Map(pinned.map((id, i) => [id, i]));
  return [...items].sort((a, b) => {
    const pa = pinRank.get(a.id);
    const pb = pinRank.get(b.id);
    if (pa !== undefined || pb !== undefined) {
      if (pa === undefined) return 1;
      if (pb === undefined) return -1;
      return pa - pb;
    }
    const la = LEVEL_ORDER[deriveLevel(a.risk_score, t)];
    const lb = LEVEL_ORDER[deriveLevel(b.risk_score, t)];
    if (la !== lb) return la - lb;
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
  return sortQueue(items.filter((it) => matchesFilters(it, f, t)), t, pinned);
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
  return p;
}

const PLATFORMS: Platform[] = ["web", "youtube", "instagram", "facebook", "tiktok", "x", "google_ads", "sample"];
const STATUSES: Status[] = ["new", "in_review", "escalated", "closed_violation", "closed_ok"];
const LEVELS: RiskLevel[] = ["red", "orange", "green"];
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function oneOf<T extends string>(value: string | null, allowed: readonly T[]): T | "" {
  return value && (allowed as readonly string[]).includes(value) ? (value as T) : "";
}

export function filtersFromSearch(p: URLSearchParams): QueueFilters {
  const m = Number(p.get("modul"));
  const from = p.get("od") ?? "";
  const to = p.get("do") ?? "";
  return {
    q: p.get("q") ?? "",
    from: DATE_RE.test(from) ? from : "",
    to: DATE_RE.test(to) ? to : "",
    platform: oneOf(p.get("zrodlo"), PLATFORMS),
    level: oneOf(p.get("poziom"), LEVELS),
    module: m === 1 || m === 2 || m === 3 ? m : 0,
    status: oneOf(p.get("status"), STATUSES),
  };
}

/** Query string for the server-side CSV export (the API has no level filter). */
export function filtersToApiQuery(f: QueueFilters): string {
  const p = new URLSearchParams();
  if (f.module) p.set("module", String(f.module));
  if (f.platform) p.set("source", f.platform);
  if (f.status) p.set("status", f.status);
  if (f.from) p.set("from", f.from);
  if (f.to) p.set("to", f.to);
  if (f.q) p.set("q", f.q);
  const s = p.toString();
  return s ? `?${s}` : "";
}
