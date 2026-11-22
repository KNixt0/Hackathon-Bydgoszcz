import type {
  EvidenceKind, GraphEdge, GraphNodeType, ModuleId, Platform, RegistryStatus, RiskLevel, RuleStatus, Status, Claim,
  Finding, Recommendation, Forensics, CaseLabel, EscalationPath, ResolutionAction, Role, RuleMethod,
  ContentState, FollowUpOutcome, ScopeCategory,
} from "../types/incident";
import type { AuditAction, ReportCategory, ScanState } from "../types/api";

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
  awaiting_correction: "Po interwencji: weryfikacja",
  resolved: "Zamknięte: potwierdzone przez analityka",
  false_positive: "Zamknięte: fałszywy alarm",
};
export const STATUSES: Status[] = [
  "new", "in_review", "escalation_requested", "escalated", "awaiting_correction", "resolved", "false_positive",
];

export const ROLE_LABEL: Record<Role, string> = { ANALYST: "Analityk", SUPERVISOR: "Kierownik" };

export const ESCALATION_PATH_LABEL: Record<EscalationPath, string> = {
  RISK_INFORMATION: "Ryzyko informacyjne (moduł 2)",
  UNLICENSED_ACTIVITY: "Działalność bez zezwolenia (moduł 3)",
  THIRD_PARTY_ADVERTISING: "Reklama podmiotu trzeciego (moduł 1)",
};
export const ESCALATION_PATHS = Object.keys(ESCALATION_PATH_LABEL) as EscalationPath[];

export const RESOLUTION_ACTION_LABEL: Record<ResolutionAction, string> = {
  evidence_report: "Raport z wykrycia przekazany dalej",
  content_removed: "Treść usunięta",
  content_corrected: "Treść poprawiona",
  false_positive: "Fałszywy alarm",
};

// Contract v4
export const CONTENT_STATE_LABEL: Record<ContentState, string> = {
  online: "Dostępna, bez zmian od wykrycia",
  changed: "Zmieniona od wykrycia",
  removed: "Usunięta (strona zwraca błąd 404/410)",
  unreachable: "Niedostępna przy ostatnim sprawdzeniu",
};
export const FOLLOW_UP_OUTCOME_LABEL: Record<FollowUpOutcome, string> = {
  removed: "Treść usunięta",
  corrected: "Treść poprawiona, wynik poniżej progu",
  persisting: "Naruszenie trwa",
};
export const SCOPE_CATEGORY_LABEL: Record<ScopeCategory, string> = {
  investment: "Instrumenty i usługi inwestycyjne",
  consumer_credit: "Kredyt konsumencki",
  deposit: "Produkt depozytowy",
  crypto: "Kryptoaktywa",
  insurance: "Produkt ubezpieczeniowy",
  tax_legal: "Doradztwo podatkowe lub prawne",
  foreign_market: "Rynek zagraniczny",
  no_financial_offer: "Brak oferty finansowej",
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
  rescan: "Ponowne sprawdzenie źródła",
  calibration_preview: "Zmiana progów (podgląd własny)",
  public_report: "Zgłoszenie użytkownika",
};

export const REPORT_CATEGORY_LABEL: Record<ReportCategory, string> = {
  1: "Reklama influencera lub podmiotu trzeciego",
  2: "Materiał firmy inwestycyjnej",
  3: "Doradztwo bez zezwolenia",
};

export const MODULE_LABEL: Record<ModuleId, string> = {
  1: "Reklamy podmiotów trzecich",
  2: "Zgodność i informacja o ryzyku",
  3: "Doradztwo bez zezwolenia",
};
export const MODULE_SHORT: Record<ModuleId, string> = { 1: "Podmioty trzecie", 2: "Informacja o ryzyku", 3: "Doradztwo bez zezwolenia" };
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

/** Words in the register table's "Wynik" column. */
export const REGISTRY_RESULT_LABEL: Record<RegistryStatus, string> = {
  listed: "wpis aktywny",
  not_listed: "brak wpisu",
  warning_listed: "na liście ostrzeżeń",
  inactive: "wpis nieaktywny",
  not_checked: "nie sprawdzono",
};

/** How a criterion was assessed (contract v3 RuleResult.method). */
export const RULE_METHOD_LABEL: Record<RuleMethod, string> = {
  rendered: "pomiar w przeglądarce",
  static: "analiza HTML",
  text: "tekst",
  llm: "model językowy",
};

export const NODE_TYPE_LABEL: Record<GraphNodeType, string> = {
  company: "Spółka",
  person: "Osoba",
  pr_agency: "Agencja PR",
  influencer: "Twórca internetowy",
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
  explain: "Wymaga oceny analityka",
  escalate: "Wysoki priorytet",
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
