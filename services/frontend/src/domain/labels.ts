import type {
  EvidenceKind, GraphEdge, GraphNodeType, ModuleId, Platform, RegistryStatus, RiskLevel, RuleStatus, Status, Claim,
  Finding, Recommendation, Forensics,
} from "../types/incident";
import type { ScanState } from "../types/api";

export const LEVEL_LABEL: Record<RiskLevel, string> = {
  red: "Krytyczne",
  orange: "Do weryfikacji",
  green: "Zgodne",
};

export const STATUS_LABEL: Record<Status, string> = {
  new: "Nowe",
  in_review: "W analizie",
  escalated: "Eskalowane",
  closed_violation: "Zamknięte: naruszenie",
  closed_ok: "Zamknięte: bez naruszeń",
};
export const STATUSES: Status[] = ["new", "in_review", "escalated", "closed_violation", "closed_ok"];

export const MODULE_LABEL: Record<ModuleId, string> = {
  1: "Finfluencerzy i podmioty trzecie",
  2: "Zgodność i informacja o ryzyku",
  3: "Shadow advisory",
};
export const MODULE_SHORT: Record<ModuleId, string> = { 1: "Finfluencerzy", 2: "Informacja o ryzyku", 3: "Shadow advisory" };
export const MODULES: ModuleId[] = [1, 2, 3];

export const PLATFORM_LABEL: Record<Platform, string> = {
  web: "WWW",
  youtube: "YouTube",
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  x: "X",
  google_ads: "Google Ads",
  sample: "Próbka",
};
export const PLATFORMS = Object.keys(PLATFORM_LABEL) as Platform[];

export const RULE_STATUS_LABEL: Record<RuleStatus, string> = {
  pass: "Spełnione",
  fail: "Naruszenie",
  na: "Nie dotyczy",
  unknown: "Do oceny ręcznej",
};

export const REGISTRY_STATUS_LABEL: Record<RegistryStatus, string> = {
  listed: "W rejestrze",
  not_listed: "Brak wpisu",
  warning_listed: "Lista ostrzeżeń",
  inactive: "Wpis nieaktywny",
  not_checked: "Nie sprawdzono",
};

export const NODE_TYPE_LABEL: Record<GraphNodeType, string> = {
  company: "Spółka",
  person: "Osoba",
  pr_agency: "Agencja PR",
  influencer: "Influencer",
  ad: "Materiał reklamowy",
  advisor: "Doradca",
};

export const EDGE_TYPE_LABEL: Record<GraphEdge["type"], string> = {
  board_member: "Członek zarządu",
  owner: "Właściciel",
  beneficial_owner: "Beneficjent rzeczywisty",
  employs: "Zatrudnia",
  contract: "Umowa",
  promotes: "Promuje",
  related: "Powiązanie",
  publishes: "Publikuje",
};

export const EVIDENCE_KIND_LABEL: Record<EvidenceKind, string> = {
  quote: "Cytat",
  legal: "Podstawa prawna",
  registry: "Wpis w rejestrze",
  archive: "Archiwum",
  account: "Konta",
  url: "Adres URL",
  krs: "KRS",
};

export const CLAIM_VERDICT_LABEL: Record<Claim["verdict"], string> = {
  upheld: "Utrzymany",
  weakened: "Osłabiony",
  rejected: "Odrzucony",
};

export const SEVERITY_LABEL: Record<Finding["severity"], string> = {
  high: "Wysoka",
  medium: "Średnia",
  low: "Niska",
  info: "Informacja",
};

export const ACTION_LABEL: Record<Recommendation["action"], string> = {
  none: "Bez działań",
  monitor: "Monitorować",
  explain: "Wezwać do wyjaśnień",
  escalate: "Eskalować",
};

export const SCAN_STATE_LABEL: Record<ScanState, string> = {
  queued: "W kolejce",
  scraping: "Pobieranie",
  analyzing: "Analiza",
  done: "Zakończono",
  failed: "Błąd",
};

export const ANOMALY_LABEL: Record<Forensics["anomalies"][number]["type"], string> = {
  opinion_spike: "Skok liczby opinii",
  fresh_account_cluster: "Skupisko świeżych kont",
  name_pattern_cluster: "Wzorzec nazw kont",
  foreign_origin_cluster: "Skupisko kont zagranicznych",
};
