import type {
  EvidenceKind, GraphEdge, GraphNodeType, ModuleId, Platform, RegistryStatus, RiskLevel, RuleStatus, Status, Claim,
  Finding, Recommendation, Forensics, CaseLabel, EscalationPath, ResolutionAction, Role,
} from "../types/incident";
import type { AuditAction, ReportCategory, ScanState } from "../types/api";
import type { PriorityTier } from "./priority";

export const LEVEL_LABEL: Record<RiskLevel, string> = {
  red: "Krytyczne",
  orange: "Do weryfikacji",
  green: "Zgodne",
};

export const STATUS_LABEL: Record<Status, string> = {
  new: "Nowe",
  in_review: "W weryfikacji",
  escalation_requested: "Wniosek o eskalację",
  escalated: "Eskalowane",
  resolved: "Zamknięte: naruszenie",
  false_positive: "Zamknięte: fałszywy alarm",
};
export const STATUSES: Status[] = ["new", "in_review", "escalation_requested", "escalated", "resolved", "false_positive"];

export const ROLE_LABEL: Record<Role, string> = { ANALYST: "Analityk", SUPERVISOR: "Kierownik" };

export const ESCALATION_PATH_LABEL: Record<EscalationPath, string> = {
  SUPERVISION_RISK_DEPT: "Departament nadzoru: informacja o ryzyku",
  LEGAL_WARNING_LIST: "Departament Prawny: lista ostrzeżeń publicznych",
  THIRD_PARTY_AUDIT: "Audyt współpracy z podmiotem trzecim",
};
export const ESCALATION_PATHS = Object.keys(ESCALATION_PATH_LABEL) as EscalationPath[];

export const RESOLUTION_ACTION_LABEL: Record<ResolutionAction, string> = {
  evidence_report: "Raport dowodowy",
  warning_list_request: "Wniosek o wpis na listę ostrzeżeń",
  enhanced_monitoring: "Wzmożony monitoring (co 6 godzin)",
  false_positive: "Fałszywy alarm",
};

export const CASE_LABEL_LABEL: Record<CaseLabel, string> = {
  unlabeled: "Bez oceny",
  true_positive: "Trafny alarm (naruszenie)",
  false_positive: "Fałszywy alarm",
};

export const AUDIT_ACTION_LABEL: Record<AuditAction, string> = {
  login: "Logowanie",
  assign: "Przypisanie sprawy",
  transition: "Zmiana etapu",
  label: "Ocena trafności",
  thresholds: "Zmiana progów",
  export: "Eksport",
  rescan: "Ponowne skanowanie",
  public_report: "Zgłoszenie użytkownika",
};

export const TIER_LABEL: Record<Exclude<PriorityTier, "low_watch">, string> = {
  critical_viral: "Krytyczne i zgłaszane",
  high_risk_early: "Wysokie ryzyko",
  crowd_anomaly: "Rozbieżność: zgłaszane przez użytkowników",
};
export const TIER_FILTER_LABEL: Record<PriorityTier, string> = { ...TIER_LABEL, low_watch: "Niskie ryzyko, mało zgłoszeń" };
export const TIER_HINT: Record<Exclude<PriorityTier, "low_watch">, string> = {
  critical_viral: "Wysoki wynik silnika i co najmniej 5 zgłoszeń użytkowników.",
  high_risk_early: "Wysoki wynik silnika, jeszcze mało zgłoszeń użytkowników.",
  crowd_anomaly: "Silnik ocenił materiał nisko, a użytkownicy zgłaszają go masowo. To możliwy fałszywie ujemny wynik modelu: warto zweryfikować ręcznie.",
};

export const REPORT_CATEGORY_LABEL: Record<ReportCategory, string> = {
  1: "Reklama influencera lub podmiotu trzeciego",
  2: "Materiał firmy inwestycyjnej",
  3: "Doradztwo bez zezwolenia",
};

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
