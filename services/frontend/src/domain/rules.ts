import type { RuleId } from "../types/incident";

/**
 * The 19 UKNF risk-information criteria (12 split into 12a / 12b), as the engine names them
 * (services/ai/app/rules). Used for the tooltip on a criterion number in the queue, so nobody has to
 * remember what "kryt. 14" means.
 */
export const RULES: Record<RuleId, { name: string; definition: string; basis: string }> = {
  "1": { name: "Identyfikacja firmy", definition: "Materiał wskazuje firmę, która go publikuje lub w której imieniu jest publikowany.", basis: "art. 44 ust. 2 lit. a rozp. del. 2017/565" },
  "2": { name: "Oznaczenie reklamy", definition: "Komunikat marketingowy jest wyraźnie rozpoznawalny jako reklama.", basis: "art. 24 ust. 3 MiFID II" },
  "3": { name: "Informacja o ryzyku", definition: "Obok korzyści materiał rzetelnie wskazuje odpowiednie ryzyko.", basis: "art. 44 ust. 2 lit. b rozp. del. 2017/565" },
  "4": { name: "Rozmiar czcionki ryzyka", definition: "Ostrzeżenie o ryzyku jest pisane czcionką co najmniej tak dużą jak główna treść.", basis: "art. 44 ust. 2 lit. c rozp. del. 2017/565" },
  "5": { name: "Ekspozycja i kontrast ryzyka", definition: "Ostrzeżenie jest dobrze widoczne: ma wystarczający kontrast i nie ginie w tle.", basis: "art. 44 ust. 2 lit. c i e rozp. del. 2017/565" },
  "6": { name: "Zakrywanie lub ukrywanie ryzyka", definition: "Ostrzeżenie nie jest schowane w przypisach, notach prawnych ani zasłonięte innymi elementami.", basis: "art. 44 ust. 2 lit. e rozp. del. 2017/565" },
  "7": { name: "Dostępność za jednym kliknięciem", definition: "Informacja o ryzyku nie wymaga rozwijania, przewijania okna ani dodatkowych kliknięć.", basis: "art. 44 ust. 2 lit. b i e rozp. del. 2017/565" },
  "8": { name: "Czytelność na różnych urządzeniach", definition: "Ostrzeżenie pozostaje czytelne na telefonie, tablecie i komputerze.", basis: "art. 44 ust. 2 lit. g rozp. del. 2017/565" },
  "9": { name: "Zrozumiałość dla odbiorcy", definition: "Treść jest zrozumiała dla przeciętnego odbiorcy z grupy, do której jest kierowana.", basis: "art. 44 ust. 2 lit. d rozp. del. 2017/565" },
  "10": { name: "Spójność językowa", definition: "Ostrzeżenie jest w tym samym języku co główny przekaz.", basis: "art. 44 ust. 2 lit. f rozp. del. 2017/565" },
  "11": { name: "Porównania produktów lub usług", definition: "Porównanie jest rzetelne, ma podane źródła oraz założenia.", basis: "art. 44 ust. 3 rozp. del. 2017/565" },
  "12a": { name: "Wyniki historyczne: okres i zakres", definition: "Wyniki z przeszłości obejmują co najmniej 5 lat (lub cały okres oferowania) i pełne okresy 12-miesięczne.", basis: "art. 44 ust. 4 rozp. del. 2017/565" },
  "12b": { name: "Wyniki historyczne: warunki i waluta", definition: "Podano źródło wyników, a przy innej walucie ostrzeżenie o wpływie kursu.", basis: "art. 44 ust. 4 rozp. del. 2017/565" },
  "13": { name: "Dominacja wyników historycznych", definition: "Wyniki z przeszłości nie są najbardziej eksponowaną częścią materiału.", basis: "art. 44 ust. 4 lit. a rozp. del. 2017/565" },
  "14": { name: "Ostrzeżenie przy wynikach historycznych", definition: "Przy wynikach z przeszłości jest ostrzeżenie, że nie są one wskaźnikiem przyszłych wyników.", basis: "art. 44 ust. 4 lit. d rozp. del. 2017/565" },
  "15": { name: "Prognozy przyszłych wyników", definition: "Prognoza opiera się na rozsądnych założeniach i zawiera ostrzeżenie, że nie jest gwarancją.", basis: "art. 44 ust. 6 rozp. del. 2017/565" },
  "16": { name: "Informacja podatkowa", definition: "Materiał zaznacza, że skutki podatkowe zależą od indywidualnej sytuacji klienta.", basis: "art. 44 ust. 7 rozp. del. 2017/565" },
  "17": { name: "Zakaz sugerowania aprobaty nadzoru", definition: "Materiał nie sugeruje, że organ nadzoru zatwierdził produkt lub usługę.", basis: "art. 44 ust. 8 rozp. del. 2017/565" },
  "18": { name: "Nadzór jako argument bezpieczeństwa", definition: "Materiał nie przedstawia faktu nadzoru jako gwarancji bezpieczeństwa inwestycji.", basis: "art. 44 ust. 8 rozp. del. 2017/565" },
};

export const ruleTooltip = (id: RuleId): string => {
  const r = RULES[id];
  return r ? `Kryterium ${id}: ${r.name}. ${r.definition} (${r.basis})` : `Kryterium ${id}`;
};
