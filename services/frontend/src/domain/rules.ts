import type { RuleId } from "../types/incident";

/** Names and legal references from the same rule catalogue used by the analysis engine. */
export const RULE_DEFINITIONS = {
  "1": {
    "name": "Identyfikacja firmy",
    "legal_basis": "art. 44 ust. 2 lit. a rozporządzenia del. 2017/565"
  },
  "2": {
    "name": "Oznaczenie reklamy",
    "legal_basis": "art. 24 ust. 3 MiFID II"
  },
  "3": {
    "name": "Informacja o ryzyku",
    "legal_basis": "art. 44 ust. 2 lit. b rozporządzenia del. 2017/565"
  },
  "4": {
    "name": "Rozmiar czcionki ryzyka",
    "legal_basis": "art. 44 ust. 2 lit. c rozporządzenia del. 2017/565"
  },
  "5": {
    "name": "Ekspozycja i kontrast ryzyka",
    "legal_basis": "art. 44 ust. 2 lit. c i e rozporządzenia del. 2017/565"
  },
  "6": {
    "name": "Zakrywanie / ukrywanie ryzyka",
    "legal_basis": "art. 44 ust. 2 lit. e rozporządzenia del. 2017/565"
  },
  "7": {
    "name": "Dostępność za 1 kliknięciem",
    "legal_basis": "art. 44 ust. 2 lit. b i e rozporządzenia del. 2017/565"
  },
  "8": {
    "name": "Responsywność (różne urządzenia)",
    "legal_basis": "art. 44 ust. 2 lit. g rozporządzenia del. 2017/565"
  },
  "9": {
    "name": "Zrozumiałość dla grupy docelowej",
    "legal_basis": "art. 44 ust. 2 lit. d rozporządzenia del. 2017/565"
  },
  "10": {
    "name": "Spójność językowa",
    "legal_basis": "art. 44 ust. 2 lit. f rozporządzenia del. 2017/565"
  },
  "11": {
    "name": "Porównania produktów / usług",
    "legal_basis": "art. 44 ust. 3 rozporządzenia del. 2017/565"
  },
  "13": {
    "name": "Dominacja wyników historycznych",
    "legal_basis": "art. 44 ust. 4 lit. a rozporządzenia del. 2017/565"
  },
  "14": {
    "name": "Ostrzeżenie przy wynikach historycznych",
    "legal_basis": "art. 44 ust. 4 lit. d rozporządzenia del. 2017/565"
  },
  "15": {
    "name": "Prognozy przyszłych wyników",
    "legal_basis": "art. 44 ust. 6 rozporządzenia del. 2017/565"
  },
  "16": {
    "name": "Informacja podatkowa",
    "legal_basis": "art. 44 ust. 7 rozporządzenia del. 2017/565"
  },
  "17": {
    "name": "Zakaz sugerowania aprobaty organu nadzoru",
    "legal_basis": "art. 44 ust. 8 rozporządzenia del. 2017/565"
  },
  "18": {
    "name": "Nadzór jako argument bezpieczeństwa",
    "legal_basis": "art. 44 ust. 8 rozporządzenia del. 2017/565"
  },
  "12a": {
    "name": "Wyniki historyczne: okres i zakres",
    "legal_basis": "art. 44 ust. 4 rozporządzenia del. 2017/565"
  },
  "12b": {
    "name": "Wyniki historyczne: warunki i waluta",
    "legal_basis": "art. 44 ust. 4 rozporządzenia del. 2017/565"
  }
} satisfies Record<RuleId, { name: string; legal_basis: string }>;
