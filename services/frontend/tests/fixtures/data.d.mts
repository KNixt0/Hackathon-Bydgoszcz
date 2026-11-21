import type { CalibrationSet, ThresholdSettings, Trends, User } from "../../src/types/api";
import type { Incident, IncidentSummary } from "../../src/types/incident";

export const orangeCase: Incident;
export const greenCase: Incident;
export const redCase: Incident;
export const redSummary: IncidentSummary;
export const incidentSummaries: IncidentSummary[];
export const calibrationSet: CalibrationSet;
export const trends: Trends;
export const incidentsById: Record<string, Incident>;
export function priorityScore(risk: number, reports: number): number;
export function reportsForCase(item: { user_reports_count?: number }, now?: number): { created_at: string; category_hint: 1 | 2 | 3 | null; comment: string | null }[];
export function toSummary(inc: Incident): IncidentSummary;
export function minimalIncident(summary: IncidentSummary): Incident;
export function trendsFrom(summaries: IncidentSummary[], days?: number, now?: number): Trends;
export const analystUser: User;
export const supervisorUser: User;
export const globalThresholds: ThresholdSettings;
