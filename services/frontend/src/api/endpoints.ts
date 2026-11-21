import type { CalibrationSet, Health, IncidentList, ScanJob, ScanRequest, Trends } from "../types/api";
import type { Incident, Status } from "../types/incident";
import { request, requestText } from "./client";

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });
const id = (v: string) => encodeURIComponent(v);

export const api = {
  health: (signal?: AbortSignal) => request<Health>("/api/health", { signal }),
  listIncidents: (signal?: AbortSignal) => request<IncidentList>("/api/incidents", { signal }),
  getIncident: (incidentId: string, signal?: AbortSignal) => request<Incident>(`/api/incidents/${id(incidentId)}`, { signal }),
  setStatus: (incidentId: string, status: Status) =>
    request<Incident>(`/api/incidents/${id(incidentId)}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  trends: (days = 30, signal?: AbortSignal) => request<Trends>(`/api/stats/trends?days=${days}`, { signal }),
  calibration: (signal?: AbortSignal) => request<CalibrationSet>("/api/calibration", { signal }),
  startScan: (body: ScanRequest) => request<{ job_id: string }>("/api/scans", post(body)),
  listScans: (signal?: AbortSignal) => request<{ items: ScanJob[] }>("/api/scans", { signal }),
  importSamples: () => request<{ job_ids: string[] }>("/api/samples/import", post({})),
  triggerDemo: () => request<{ job_id: string }>("/api/demo/trigger", post({ case: "case3" })),
  evidenceText: (key: string, signal?: AbortSignal) => requestText(evidenceUrl(key), { signal }),
};

/** Object-storage keys contain slashes: encode each segment, keep the path shape. */
export function evidenceUrl(key: string): string {
  return `/api/evidence/${key.split("/").map(encodeURIComponent).join("/")}`;
}
export const exportPdfUrl = (incidentId: string) => `/api/incidents/${id(incidentId)}/export.pdf`;
export const exportCsvUrl = (incidentId: string) => `/api/incidents/${id(incidentId)}/export.csv`;
export const exportListCsvUrl = (query: string) => `/api/incidents/export.csv${query}`;
