import type {
  AuditEntry, AuthConfig, CalibrationSet, CaseReport, Health, IncidentList, PublicReportAccepted, PublicReportRequest, ScanJob, ScanRequest, ThresholdSettings, TransitionRequest, Trends, User,
} from "../types/api";
import type { CaseLabel, Incident, Role } from "../types/incident";
import { request, requestText } from "./client";

const post = (body?: unknown): RequestInit => ({ method: "POST", ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
const id = (v: string) => encodeURIComponent(v);

export interface AuditQuery {
  incident_id?: string;
  actor?: string;
  limit?: number;
}

function query(params: Record<string, string | number | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: (signal?: AbortSignal) => request<Health>("/api/health", { signal }),
  listIncidents: (signal?: AbortSignal) => request<IncidentList>("/api/incidents", { signal }),
  getIncident: (incidentId: string, signal?: AbortSignal) => request<Incident>(`/api/incidents/${id(incidentId)}`, { signal }),
  transition: (incidentId: string, body: TransitionRequest) => request<Incident>(`/api/incidents/${id(incidentId)}/transition`, post(body)),
  assign: (incidentId: string) => request<Incident>(`/api/incidents/${id(incidentId)}/assign`, post()),
  label: (incidentId: string, label: CaseLabel) => request<Incident>(`/api/incidents/${id(incidentId)}/label`, post({ label })),
  history: (incidentId: string, signal?: AbortSignal) => request<{ items: AuditEntry[] }>(`/api/incidents/${id(incidentId)}/history`, { signal }),
  incidentReports: (incidentId: string, signal?: AbortSignal) => request<{ items: CaseReport[] }>(`/api/incidents/${id(incidentId)}/reports`, { signal }),
  /** Public: no session needed. */
  submitReport: (body: PublicReportRequest) => request<PublicReportAccepted>("/api/public/reports", post(body)),
  trends: (days = 30, signal?: AbortSignal) => request<Trends>(`/api/stats/trends?days=${days}`, { signal }),
  calibration: (signal?: AbortSignal) => request<CalibrationSet>("/api/calibration", { signal }),
  startScan: (body: ScanRequest) => request<{ job_id: string }>("/api/scans", post(body)),
  listScans: (signal?: AbortSignal) => request<{ items: ScanJob[] }>("/api/scans", { signal }),
  importSamples: () => request<{ job_ids: string[] }>("/api/samples/import", post({})),
  triggerDemo: () => request<{ job_id: string }>("/api/demo/trigger", post({ case: "case3" })),
  evidenceText: (key: string, signal?: AbortSignal) => requestText(evidenceUrl(key), { signal }),
  thresholds: (signal?: AbortSignal) => request<ThresholdSettings>("/api/settings/thresholds", { signal }),
  saveThresholds: (flag: number, critical: number) =>
    request<ThresholdSettings>("/api/settings/thresholds", { method: "PUT", body: JSON.stringify({ flag, critical }) }),
  audit: (q: AuditQuery = {}, signal?: AbortSignal) =>
    request<{ items: AuditEntry[] }>(`/api/audit${query({ incident_id: q.incident_id, actor: q.actor, limit: q.limit })}`, { signal }),
  authConfig: (signal?: AbortSignal) => request<AuthConfig>("/api/auth/config", { signal }),
  me: (signal?: AbortSignal) => request<{ user: User }>("/api/auth/me", { signal }),
  login: (email: string, password: string) => request<{ user: User }>("/api/auth/login", post({ email, password })),
  demoLogin: (role: Role) => request<{ user: User }>("/api/auth/demo", post({ role })),
  logout: () => request<void>("/api/auth/logout", post()),
};

/** Object-storage keys contain slashes: encode each segment, keep the path shape. */
export function evidenceUrl(key: string): string {
  return `/api/evidence/${key.split("/").map(encodeURIComponent).join("/")}`;
}
export const exportPdfUrl = (incidentId: string) => `/api/incidents/${id(incidentId)}/export.pdf`;
export const exportCsvUrl = (incidentId: string) => `/api/incidents/${id(incidentId)}/export.csv`;
export const warningListRequestUrl = (incidentId: string) => `/api/incidents/${id(incidentId)}/warning-list-request.pdf`;
export const exportListCsvUrl = (query: string) => `/api/incidents/export.csv${query}`;
