import { formatDateTime } from "./format";
import type { AuditEntry } from "../types/api";
import { CASE_LABEL_LABEL, ESCALATION_PATH_LABEL, RESOLUTION_ACTION_LABEL, STATUS_LABEL } from "./labels";

const FIELD_LABEL: Record<string, string> = {
  status: "Etap",
  assigned_to: "Prowadzi",
  escalation_path: "Ścieżka eskalacji",
  resolution_action: "Działanie końcowe",
  resolution_note: "Notatka",
  started_at: "Rozpoczęcie pracy",
  closed_at: "Zamknięcie sprawy",
  intervention_note: "Interwencja",
  follow_up_due: "Termin weryfikacji",
  label: "Ocena",
  flag: "Próg oznaczenia",
  critical: "Próg krytyczny",
  method: "Sposób",
  format: "Format",
  document: "Dokument",
  scope: "Zakres",
  rows: "Wierszy",
  url: "Adres",
  job_ids: "Zadania",
  user_reports_count: "Liczba zgłoszeń",
  priority_score: "Priorytet",
};

const VALUE_LABEL: Record<string, string> = {
  ...STATUS_LABEL,
  ...ESCALATION_PATH_LABEL,
  ...RESOLUTION_ACTION_LABEL,
  ...CASE_LABEL_LABEL,
  password: "hasło",
  demo: "konto demonstracyjne",
  evidence_package: "raport z wykrycia",
  detection_report: "raport z wykrycia",
  // entries written before contract v4
  warning_list_request: "raport z wykrycia (dawny wniosek)",
  enhanced_monitoring: "monitorowanie",
  SUPERVISION_RISK_DEPT: "ryzyko informacyjne",
  LEGAL_WARNING_LIST: "działalność bez zezwolenia",
  THIRD_PARTY_AUDIT: "reklama podmiotu trzeciego",
  list: "lista spraw",
};
// the same key means different things per field
const FIELD_VALUE: Record<string, Record<string, string>> = {
  label: CASE_LABEL_LABEL,
  status: STATUS_LABEL,
  resolution_action: RESOLUTION_ACTION_LABEL,
};

function show(field: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "brak";
  if (typeof value === "string" && /(_at|_due)$/.test(field) && /^\d{4}-\d{2}-\d{2}T/.test(value)) return formatDateTime(value);
  if (typeof value === "string") return FIELD_VALUE[field]?.[value] ?? VALUE_LABEL[value] ?? value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

const asRecord = (v: unknown): Record<string, unknown> => (v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {});

export interface ChangeLine {
  field: string;
  label: string;
  before: string | null;
  after: string;
}

/** "Etap: Nowa → W weryfikacji"-style lines for an audit entry (fields present in `new`). */
export function describeChange(entry: AuditEntry): ChangeLine[] {
  const prev = asRecord(entry.previous);
  const next = asRecord(entry.new);
  // the closing note is the entry's reason: shown once, as the reason
  return Object.keys(next).filter((field) => !(field === "resolution_note" && next[field] === entry.reason)).map((field) => ({
    field,
    label: FIELD_LABEL[field] ?? field,
    before: field in prev ? show(field, prev[field]) : null,
    after: show(field, next[field]),
  }));
}
