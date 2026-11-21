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
export function toSummary(inc: Incident): IncidentSummary;
export function minimalIncident(summary: IncidentSummary): Incident;
export function trendsFrom(summaries: IncidentSummary[], days?: number, now?: number): Trends;
export const analystUser: User;
export const supervisorUser: User;
export const globalThresholds: ThresholdSettings;
