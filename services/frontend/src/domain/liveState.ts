import type { ScanJob } from "../types/api";
import type { IncidentSummary } from "../types/incident";
import { upsertIncident } from "./queue";

export interface IncidentsState {
  phase: "loading" | "error" | "ready";
  error: string | null;
  items: IncidentSummary[];
  /** ids that arrived live and still carry the "new" highlight */
  fresh: string[];
  /** alert:high incidents, newest first; pinned to the top of the queue until dismissed */
  alerts: IncidentSummary[];
}

export type IncidentsAction =
  | { type: "load:start" }
  | { type: "load:ok"; items: IncidentSummary[] }
  | { type: "load:error"; message: string }
  | { type: "incident:new"; incident: IncidentSummary }
  | { type: "incident:updated"; incident: IncidentSummary }
  | { type: "alert:high"; incident: IncidentSummary }
  | { type: "alert:dismiss"; id: string }
  | { type: "fresh:clear"; id: string };

export const INITIAL_INCIDENTS: IncidentsState = { phase: "loading", error: null, items: [], fresh: [], alerts: [] };

const withId = (ids: string[], id: string) => (ids.includes(id) ? ids : [id, ...ids]);

export function incidentsReducer(state: IncidentsState, action: IncidentsAction): IncidentsState {
  switch (action.type) {
    case "load:start":
      return { ...state, phase: state.items.length ? "ready" : "loading", error: null };
    case "load:ok": {
      // Keep anything that arrived over the socket while the request was in flight.
      const loaded = new Set(action.items.map((it) => it.id));
      const liveOnly = state.items.filter((it) => state.fresh.includes(it.id) && !loaded.has(it.id));
      return { ...state, phase: "ready", error: null, items: [...liveOnly, ...action.items] };
    }
    case "load:error":
      return { ...state, phase: state.items.length ? "ready" : "error", error: action.message };
    case "incident:new":
      return {
        ...state,
        phase: state.phase === "loading" ? "loading" : "ready",
        items: upsertIncident(state.items, action.incident),
        fresh: withId(state.fresh, action.incident.id),
      };
    case "incident:updated":
      return {
        ...state,
        items: upsertIncident(state.items, action.incident),
        alerts: state.alerts.map((a) => (a.id === action.incident.id ? action.incident : a)),
      };
    case "alert:high":
      return {
        ...state,
        items: upsertIncident(state.items, action.incident),
        fresh: withId(state.fresh, action.incident.id),
        alerts: [action.incident, ...state.alerts.filter((a) => a.id !== action.incident.id)],
      };
    case "alert:dismiss":
      return { ...state, alerts: state.alerts.filter((a) => a.id !== action.id) };
    case "fresh:clear":
      return { ...state, fresh: state.fresh.filter((id) => id !== action.id) };
  }
}


/** Insert or replace a scan job; newest first, capped. */
export function upsertJob(jobs: ScanJob[], job: ScanJob, cap = 20): ScanJob[] {
  const idx = jobs.findIndex((j) => j.id === job.id);
  if (idx === -1) return [job, ...jobs].slice(0, cap);
  const copy = [...jobs];
  copy[idx] = { ...copy[idx], ...job };
  return copy;
}
