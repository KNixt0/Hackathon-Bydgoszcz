// Contract-valid fixtures (coord/contracts/incident.md v1). Development and tests only:
// nothing in src/ imports this file, so it never reaches the production bundle.

const RULE_DEFS = [
  ["1", "Oznaczenie materiału jako informacji reklamowej", "art. 44 ust. 2 lit. a rozp. del. 2017/565"],
  ["2", "Identyfikacja firmy inwestycyjnej", "art. 44 ust. 2 lit. a rozp. del. 2017/565"],
  ["3", "Informacja rzetelna, niebudząca wątpliwości i niewprowadzająca w błąd", "art. 83c ust. 1 ustawy o obrocie"],
  ["4", "Wskazanie ryzyka przy każdej wzmiance o korzyściach", "art. 44 ust. 2 lit. b rozp. del. 2017/565"],
  ["5", "Wyrazistość informacji o ryzyku (czcionka, czas ekspozycji)", "art. 44 ust. 2 lit. c rozp. del. 2017/565"],
  ["6", "Ostrzeżenie o odsetku rachunków detalicznych przynoszących straty", "decyzja KNF z 1.08.2019 r. (CFD)"],
  ["7", "Brak gwarancji lub obietnicy zysku", "art. 44 ust. 2 lit. e rozp. del. 2017/565"],
  ["8", "Wyniki historyczne: wskazany okres i źródło", "art. 44 ust. 4 rozp. del. 2017/565"],
  ["9", "Zastrzeżenie, że wyniki historyczne nie gwarantują przyszłych", "art. 44 ust. 4 lit. d rozp. del. 2017/565"],
  ["10", "Prognozy oparte na obiektywnych danych", "art. 44 ust. 6 rozp. del. 2017/565"],
  ["11", "Porównania rzetelne i wyważone", "art. 44 ust. 3 rozp. del. 2017/565"],
  ["12a", "Informacja o kosztach i opłatach", "art. 50 rozp. del. 2017/565"],
  ["12b", "Wpływ prowizji i opłat na wynik inwestycji", "art. 44 ust. 4 lit. f rozp. del. 2017/565"],
  ["13", "Informacja o opodatkowaniu", "art. 44 ust. 7 rozp. del. 2017/565"],
  ["14", "Język zrozumiały dla przeciętnego odbiorcy docelowego", "art. 44 ust. 2 lit. d rozp. del. 2017/565"],
  ["15", "Brak powoływania się na organ nadzoru jako rekomendację", "art. 44 ust. 8 rozp. del. 2017/565"],
  ["16", "Spójność z dokumentami informacyjnymi (KID)", "art. 9 rozp. 1286/2014 (PRIIP)"],
  ["17", "Brak wywierania presji czasowej na odbiorcę", "art. 83c ust. 1 ustawy o obrocie"],
  ["18", "Ujawnienie wynagrodzenia podmiotu promującego", "art. 76 ustawy o obrocie instrumentami finansowymi"],
];

/** overrides: { [ruleId]: [status, confidence, explanation, evidence_ids] } */
function rules(defaultStatus, overrides = {}) {
  return RULE_DEFS.map(([id, name, legal_basis]) => {
    const o = overrides[id];
    return {
      id, name, legal_basis,
      status: o ? o[0] : defaultStatus,
      confidence: o ? o[1] : defaultStatus === "pass" ? 0.86 : 0.7,
      explanation: o ? o[2] : defaultStatus === "pass" ? "Wymóg spełniony w analizowanym materiale." : "Kryterium nie ma zastosowania do tego typu materiału.",
      evidence_ids: o ? o[3] ?? [] : [],
    };
  });
}

function quoteEvidence(text, id, label, quote) {
  const start = text.indexOf(quote);
  if (start < 0) throw new Error(`fixture quote not found in source text: ${quote}`);
  return { id, kind: "quote", label, quote, span: { start, end: start + quote.length } };
}

const REG = {
  firms: ["knf_investment_firms", "Rejestr firm inwestycyjnych KNF", "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/firmy_inwestycyjne"],
  cross: ["knf_foreign_cross_border", "Firmy zagraniczne działające transgranicznie", "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/zagraniczne_firmy_inwestycyjne"],
  warn: ["knf_public_warnings", "Lista ostrzeżeń publicznych KNF", "https://www.knf.gov.pl/dla_konsumenta/ostrzezenia_publiczne"],
  advisors: ["knf_investment_advisors", "Lista doradców inwestycyjnych", "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/doradcy_inwestycyjni"],
  kirp: ["kirp_legal_advisers", "Krajowa Izba Radców Prawnych", "https://rejestr.kirp.pl"],
  kidp: ["kidp_tax_advisers", "Krajowa Izba Doradców Podatkowych", "https://kidp.pl/wyszukiwarka-doradcow"],
  coop: ["uknf_cooperation_notice", "Zgłoszenia współpracy z podmiotami trzecimi (UKNF)", "https://www.knf.gov.pl"],
};
const check = (key, subject, status, detail, snapshot_date = "2026-11-14") => {
  const [registry, label, url] = REG[key];
  return { registry, label, url, subject, status, detail, snapshot_date };
};

const ENGINE = { version: "0.4.1", plugins: ["m1_finfluencer", "m2_risk_disclosure", "m3_shadow_advisory"], llm_used: true, model: "gemma-4-e4b-q4", duration_ms: 4180 };

// ───────────────────────── Orange case: finfluencer + hidden PR link + opinion forensics
const ORANGE_TEXT = [
  "Jak zacząłem zarabiać na CFD? Moja szczera recenzja platformy Tradeon.",
  "Cześć, tu Kuba z kanału Giełda Po Godzinach. Od trzech miesięcy testuję platformę Tradeon i muszę przyznać, że wyniki mówią same za siebie.",
  "W zeszłym miesiącu mój portfel urósł o 18%, a zaczynałem od zaledwie 2000 zł.",
  "Tradeon to licencjonowany broker, więc Twoje środki są w pełni bezpieczne.",
  "Rejestracja zajmuje pięć minut, a z moim kodem KUBA50 dostajesz bonus na start. Link znajdziesz w opisie.",
  "Oczywiście każda inwestycja wiąże się z ryzykiem, ale przy dobrej strategii straty można ograniczyć do minimum.",
  "To nie jest porada inwestycyjna, dzielę się tylko własnym doświadczeniem.",
  "Kontrakty CFD są złożonymi instrumentami. 74% rachunków inwestorów detalicznych odnotowuje straty.",
  "Dajcie znać w komentarzach, jak Wam idzie. Widzę, że wielu z Was już zarabia z Tradeon!",
].join("\n");

const orangeEvidence = [
  quoteEvidence(ORANGE_TEXT, "ev-q1", "Deklaracja wyniku 18% bez okresu i źródła", "mój portfel urósł o 18%"),
  quoteEvidence(ORANGE_TEXT, "ev-q2", "Zapewnienie o pełnym bezpieczeństwie środków", "Twoje środki są w pełni bezpieczne"),
  quoteEvidence(ORANGE_TEXT, "ev-q3", "Kod polecający i bonus na start", "z moim kodem KUBA50 dostajesz bonus na start"),
  quoteEvidence(ORANGE_TEXT, "ev-q4", "Ostrzeżenie o ryzyku CFD (obecne, na końcu materiału)", "74% rachunków inwestorów detalicznych odnotowuje straty"),
  quoteEvidence(ORANGE_TEXT, "ev-q5", "Bagatelizowanie ryzyka", "straty można ograniczyć do minimum"),
  quoteEvidence(ORANGE_TEXT, "ev-q6", "Zastrzeżenie autora", "To nie jest porada inwestycyjna"),
  { id: "ev-l1", kind: "legal", label: "Zakaz sugerowania gwarancji zysku", legal_ref: "art. 44 ust. 2 lit. e rozporządzenia delegowanego (UE) 2017/565", attachment: "Załącznik 2: kryteria oceny informacji reklamowych.pdf" },
  { id: "ev-l2", kind: "legal", label: "Ujawnienie wynagrodzenia podmiotu promującego", legal_ref: "art. 76 ustawy o obrocie instrumentami finansowymi", attachment: "Załącznik 2: kryteria oceny informacji reklamowych.pdf" },
  { id: "ev-l3", kind: "legal", label: "Wyniki historyczne: okres i źródło", legal_ref: "art. 44 ust. 4 rozporządzenia delegowanego (UE) 2017/565", attachment: "Załącznik 2: kryteria oceny informacji reklamowych.pdf" },
  { id: "ev-r1", kind: "registry", label: "Tradeon Europe Ltd: wpis w rejestrze firm transgranicznych", url: REG.cross[2] },
  { id: "ev-r2", kind: "registry", label: "Brak zgłoszenia współpracy Tradeon ↔ BrightReach Media", url: REG.coop[2] },
  { id: "ev-a1", kind: "archive", label: "Zrzut ekranu strony z materiałem", storage_key: "archive/orange/screenshot.png" },
  { id: "ev-a2", kind: "archive", label: "Zarchiwizowany kod HTML", storage_key: "archive/orange/page.html" },
  { id: "ev-acc1", kind: "account", label: "Próbka podejrzanych kont komentujących" },
  { id: "ev-u1", kind: "url", label: "Adres materiału źródłowego", url: "https://www.youtube.com/watch?v=tr4de0nKuba" },
  { id: "ev-k1", kind: "krs", label: "BrightReach Media sp. z o.o.: odpis KRS 0001045512", url: "https://wyszukiwarka-krs.ms.gov.pl" },
];

export const orangeCase = {
  id: "3f6c1c1e-5b0a-4f0e-9a51-0c2d1e7a9b01",
  status: "in_review",
  created_at: "2026-11-19T08:42:00Z",
  updated_at: "2026-11-20T10:05:00Z",
  title: "Recenzja platformy CFD Tradeon na kanale „Giełda Po Godzinach”",
  summary: "Influencer promuje platformę CFD, deklarując wynik 18% bez okresu i źródła; wynagrodzenie nie jest ujawnione, a agencja PR łączy go z członkiem zarządu firmy.",
  modules: [1, 2],
  primary_module: 1,
  risk_score: 58,
  compliance_score: 42,
  risk_level: "orange",
  synthetic: true,
  ground_truth: "violation",
  demo_case: "case2",
  source: {
    platform: "youtube",
    url: "https://www.youtube.com/watch?v=tr4de0nKuba",
    fetched_at: "2026-11-19T08:40:12Z",
    language: "pl",
    content_hash: "9b1f4c6de7a2035c8e44f1a6b0d97e2c51a8f3046d7be9c21f05a4736e8b1d90",
    text: ORANGE_TEXT,
    archive: { html_key: "archive/orange/page.html", screenshot_key: "archive/orange/screenshot.png" },
  },
  entities: {
    investment_firm: { name: "Tradeon Europe Ltd", kind: "investment_firm", country: "CY", url: "https://tradeon.example" },
    advertiser: { name: "Jakub Wrona", kind: "influencer", handle: "@gieldapogodzinach", country: "PL" },
    others: [
      { name: "BrightReach Media sp. z o.o.", kind: "pr_agency", krs: "0001045512", country: "PL" },
      { name: "Marta Lis", kind: "person", country: "PL" },
    ],
  },
  module_results: [
    {
      module: 1, plugin: "m1_finfluencer", score: 64, weight: 0.6,
      findings: [
        { code: "PR_CONFLICT_PATH", severity: "high", text: "Członek zarządu Tradeon Polska jest wspólnikiem agencji PR, która ma umowę z influencerem.", evidence_ids: ["ev-k1", "ev-r2"] },
        { code: "RULE_18", severity: "medium", text: "Materiał zawiera kod polecający, ale nie ujawnia wynagrodzenia.", evidence_ids: ["ev-q3", "ev-l2"] },
        { code: "FRESH_ACCOUNT_CLUSTER", severity: "medium", text: "41% komentujących kont założono w ostatnich 14 dniach.", evidence_ids: ["ev-acc1"] },
      ],
    },
    {
      module: 2, plugin: "m2_risk_disclosure", score: 49, weight: 0.4,
      findings: [
        { code: "RULE_8", severity: "medium", text: "Wynik 18% podany bez okresu odniesienia i źródła danych.", evidence_ids: ["ev-q1", "ev-l3"] },
        { code: "RULE_7", severity: "medium", text: "Sformułowanie o pełnym bezpieczeństwie środków sugeruje brak ryzyka.", evidence_ids: ["ev-q2", "ev-l1"] },
        { code: "RULE_6", severity: "info", text: "Ostrzeżenie o odsetku rachunków stratnych jest obecne.", evidence_ids: ["ev-q4"] },
      ],
    },
  ],
  rules: rules("pass", {
    "1": ["fail", 0.81, "Materiał nie jest oznaczony jako reklama ani współpraca płatna.", ["ev-q3"]],
    "4": ["fail", 0.74, "Korzyści (wzrost portfela, bonus) pojawiają się na początku, a ryzyko dopiero pod koniec.", ["ev-q1", "ev-q4"]],
    "5": ["unknown", 0.4, "Wymaga oceny wizualnej: czas ekspozycji i wielkość ostrzeżenia w nagraniu.", ["ev-a1"]],
    "6": ["pass", 0.93, "Ostrzeżenie o 74% rachunków stratnych występuje w treści.", ["ev-q4"]],
    "7": ["fail", 0.78, "„Środki w pełni bezpieczne” sugeruje brak ryzyka utraty kapitału.", ["ev-q2", "ev-l1"]],
    "8": ["fail", 0.88, "Wynik 18% bez wskazania okresu i źródła.", ["ev-q1", "ev-l3"]],
    "9": ["fail", 0.83, "Brak zastrzeżenia, że wyniki historyczne nie gwarantują przyszłych.", ["ev-q1"]],
    "10": ["na", 0.9, "Materiał nie zawiera prognoz.", []],
    "11": ["na", 0.9, "Materiał nie zawiera porównań z innymi produktami.", []],
    "12a": ["unknown", 0.35, "Brak informacji o kosztach w transkrypcji; wymaga sprawdzenia opisu filmu.", []],
    "12b": ["na", 0.8, "Nie przedstawiono symulacji wyniku.", []],
    "13": ["na", 0.85, "Materiał nie odnosi się do opodatkowania.", []],
    "16": ["na", 0.8, "Materiał podmiotu trzeciego, bez odwołania do KID.", []],
    "18": ["fail", 0.86, "Kod polecający wskazuje na wynagrodzenie, które nie zostało ujawnione.", ["ev-q3", "ev-l2", "ev-r2"]],
  }),
  registry_checks: [
    check("cross", "Tradeon Europe Ltd", "listed", "Zgodny wpis: Tradeon Europe Ltd (CySEC 311/16), działalność transgraniczna bez oddziału"),
    check("firms", "Tradeon Europe Ltd", "not_listed", "Brak wpisu w rejestrze krajowych firm inwestycyjnych"),
    check("warn", "Tradeon Europe Ltd", "not_listed", "Podmiot nie figuruje na liście ostrzeżeń"),
    check("coop", "Tradeon Europe Ltd ↔ Jakub Wrona", "not_listed", "Brak zgłoszenia współpracy z podmiotem trzecim"),
    check("advisors", "Jakub Wrona", "not_listed", "Autor nie jest doradcą inwestycyjnym"),
    check("kirp", "nie dotyczy", "not_checked", "W materiale nie powołano się na radcę prawnego", null),
  ],
  graph: {
    nodes: [
      { id: "n-lis", type: "person", label: "Marta Lis", meta: { rola: "Członek zarządu Tradeon Polska; wspólnik BrightReach Media", udział: "40%" } },
      { id: "n-nowak", type: "person", label: "Piotr Nowak", meta: { rola: "Prezes zarządu Tradeon Polska" } },
      { id: "n-tradeon-pl", type: "company", label: "Tradeon Polska sp. z o.o.", meta: { KRS: "0000987321", "data rejestracji": "2026-01-15" } },
      { id: "n-tradeon-eu", type: "company", label: "Tradeon Europe Ltd", meta: { kraj: "Cypr", licencja: "CySEC 311/16" } },
      { id: "n-pr", type: "pr_agency", label: "BrightReach Media", meta: { KRS: "0001045512", "kapitał zakładowy": "5 000 zł" } },
      { id: "n-inf", type: "influencer", label: "@gieldapogodzinach", meta: { platforma: "YouTube", subskrybenci: 184000 } },
      { id: "n-inf2", type: "influencer", label: "@finanse_z_ola", meta: { platforma: "Instagram", obserwujący: 52000 } },
      { id: "n-ad", type: "ad", label: "Recenzja Tradeon (film)", meta: { opublikowano: "2026-11-17" } },
    ],
    edges: [
      { source: "n-lis", target: "n-tradeon-pl", type: "board_member", label: "członek zarządu", suspicious: true },
      { source: "n-nowak", target: "n-tradeon-pl", type: "board_member", label: "prezes zarządu", suspicious: false },
      { source: "n-tradeon-eu", target: "n-tradeon-pl", type: "owner", label: "100% udziałów", suspicious: false },
      { source: "n-lis", target: "n-pr", type: "beneficial_owner", label: "wspólnik 40%", suspicious: true },
      { source: "n-pr", target: "n-inf", type: "contract", label: "umowa promocyjna", suspicious: true },
      { source: "n-pr", target: "n-inf2", type: "contract", label: "umowa promocyjna", suspicious: false },
      { source: "n-inf", target: "n-ad", type: "publishes", label: "publikuje", suspicious: false },
      { source: "n-ad", target: "n-tradeon-eu", type: "promotes", label: "promuje", suspicious: false },
    ],
    flagged_paths: [
      { node_ids: ["n-tradeon-pl", "n-lis", "n-pr", "n-inf"], description: "Zarząd spółki → agencja PR → influencer: członek zarządu Tradeon Polska jest wspólnikiem agencji, która opłaca autora recenzji." },
    ],
  },
  forensics: {
    opinion_timeline: [
      { date: "2026-11-06", count: 9, avg_rating: 3.9, new_account_share: 0.08 },
      { date: "2026-11-07", count: 12, avg_rating: 4.0, new_account_share: 0.1 },
      { date: "2026-11-08", count: 8, avg_rating: 3.8, new_account_share: 0.06 },
      { date: "2026-11-09", count: 11, avg_rating: 4.1, new_account_share: 0.09 },
      { date: "2026-11-10", count: 14, avg_rating: 4.0, new_account_share: 0.12 },
      { date: "2026-11-11", count: 10, avg_rating: 3.9, new_account_share: 0.1 },
      { date: "2026-11-12", count: 13, avg_rating: 4.2, new_account_share: 0.11 },
      { date: "2026-11-13", count: 15, avg_rating: 4.1, new_account_share: 0.13 },
      { date: "2026-11-14", count: 12, avg_rating: 4.0, new_account_share: 0.1 },
      { date: "2026-11-15", count: 16, avg_rating: 4.2, new_account_share: 0.15 },
      { date: "2026-11-16", count: 21, avg_rating: 4.4, new_account_share: 0.24 },
      { date: "2026-11-17", count: 96, avg_rating: 4.9, new_account_share: 0.71 },
      { date: "2026-11-18", count: 74, avg_rating: 4.8, new_account_share: 0.66 },
      { date: "2026-11-19", count: 31, avg_rating: 4.6, new_account_share: 0.38 },
    ],
    accounts: {
      total: 342,
      share_younger_14d: 0.41,
      age_buckets: [
        { bucket: "<14d", count: 140 }, { bucket: "14–90d", count: 48 }, { bucket: "3–12m", count: 52 },
        { bucket: "1–3y", count: 61 }, { bucket: ">3y", count: 41 },
      ],
      origins: [
        { country: "PL", count: 171 }, { country: "VN", count: 68 }, { country: "NG", count: 44 },
        { country: "IN", count: 37 }, { country: "DE", count: 12 }, { country: "inne", count: 10 },
      ],
      name_patterns: [
        { pattern: "imię + 4 cyfry", count: 87, examples: ["kasia4821", "tomek9034", "ania1177"] },
        { pattern: "user + ciąg losowy", count: 39, examples: ["user-x8k2p", "user-qq71m"] },
        { pattern: "imię_nazwisko", count: 112, examples: ["jan_kowalczyk", "ewa_mazur"] },
      ],
    },
    anomalies: [
      { type: "opinion_spike", severity: "high", description: "17–18.11: 170 opinii w 48 godzin przy średniej 12 dziennie." },
      { type: "fresh_account_cluster", severity: "high", description: "41% kont założono w ciągu 14 dni przed publikacją." },
      { type: "name_pattern_cluster", severity: "medium", description: "87 kont według schematu „imię + 4 cyfry”." },
      { type: "foreign_origin_cluster", severity: "medium", description: "44% kont spoza Polski przy polskojęzycznym materiale." },
    ],
    sample_accounts: [
      { handle: "kasia4821", created_at: "2026-11-15", country: "VN", text: "Super platforma, zarobiłam już 3000 zł w tydzień! Polecam każdemu." },
      { handle: "tomek9034", created_at: "2026-11-16", country: "NG", text: "Najlepszy broker, wypłata w 5 minut. Dziękuję Kuba!" },
      { handle: "user-x8k2p", created_at: "2026-11-16", country: "IN", text: "Tradeon zmienił moje życie, zero strat od miesiąca." },
      { handle: "ania1177", created_at: "2026-11-14", country: "VN", text: "Polecam, bezpiecznie i szybko. Kod KUBA50 działa." },
    ],
  },
  financials: {
    company: "BrightReach Media sp. z o.o.",
    krs: "0001045512",
    incorporated_on: "2026-03-02",
    age_months: 8,
    share_capital_pln: 5000,
    statements: [
      { year: 2024, revenue_pln: null, net_result_pln: null, filed: false },
      { year: 2025, revenue_pln: null, net_result_pln: null, filed: false },
      { year: 2026, revenue_pln: 1840000, net_result_pln: 912000, filed: true },
    ],
    flags: ["Spółka młodsza niż 12 miesięcy", "Minimalny kapitał zakładowy (5 000 zł)", "Przychód 1,84 mln zł w pierwszym roku działalności"],
  },
  debate: {
    rounds: [
      { round: 1, agent: "Oskarżyciel", role: "Zbiera argumenty za naruszeniem", summary: "Wskazał nieujawnione wynagrodzenie, wynik 18% bez źródła i powiązanie kapitałowe przez agencję PR.", claim_ids: ["c1", "c2", "c3", "c4"] },
      { round: 1, agent: "Obrońca", role: "Zbiera okoliczności łagodzące", summary: "Podniósł obecność ostrzeżenia CFD, zastrzeżenie autora i legalność działalności transgranicznej.", claim_ids: ["c5", "c6", "c7"] },
      { round: 2, agent: "Krytyk", role: "Weryfikuje każdy argument względem dowodów", summary: "Utrzymał trzy zarzuty, osłabił zarzut dotyczący opinii (korelacja, nie dowód zlecenia) i odrzucił argument o zastrzeżeniu autora.", claim_ids: ["c1", "c2", "c3", "c4", "c5", "c6", "c7"] },
      { round: 3, agent: "Arbiter", role: "Waży utrzymane argumenty i wydaje ocenę", summary: "Naruszenia formalne potwierdzone, ale brak gwarancji zysku wprost i obecne ostrzeżenie CFD obniżają wagę sprawy.", claim_ids: ["c1", "c2", "c3", "c5", "c7"] },
    ],
    claims: [
      { id: "c1", stance: "for", text: "Autor otrzymuje wynagrodzenie za polecenia (kod KUBA50), czego nie ujawnia.", confidence: 0.86, evidence_ids: ["ev-q3", "ev-l2", "ev-r2"], verdict: "upheld", critique: "Kod polecający i brak zgłoszenia współpracy są spójne; zarzut utrzymany." },
      { id: "c2", stance: "for", text: "Wynik 18% podano bez okresu, źródła i zastrzeżenia o wynikach historycznych.", confidence: 0.88, evidence_ids: ["ev-q1", "ev-l3"], verdict: "upheld", critique: "Cytat dosłowny, brak jakiegokolwiek kontekstu wyniku." },
      { id: "c3", stance: "for", text: "Członek zarządu spółki zależnej firmy inwestycyjnej jest wspólnikiem agencji PR opłacającej influencera.", confidence: 0.79, evidence_ids: ["ev-k1", "ev-r2"], verdict: "upheld", critique: "Potwierdzone odpisem KRS; ścieżka zarząd → agencja → influencer jest kompletna." },
      { id: "c4", stance: "for", text: "Pozytywne opinie pod materiałem są zlecone: 41% kont ma mniej niż 14 dni.", confidence: 0.52, evidence_ids: ["ev-acc1"], verdict: "weakened", critique: "Anomalia jest wyraźna, ale nie dowodzi, kto zlecił opinie. Wymaga weryfikacji ręcznej." },
      { id: "c5", stance: "against", text: "Materiał zawiera wymagane ostrzeżenie o 74% rachunków stratnych.", confidence: 0.93, evidence_ids: ["ev-q4"], verdict: "upheld", critique: "Ostrzeżenie obecne dosłownie, choć na końcu materiału." },
      { id: "c6", stance: "against", text: "Autor zastrzega, że nie udziela porady inwestycyjnej.", confidence: 0.3, evidence_ids: ["ev-q6"], verdict: "rejected", critique: "Zastrzeżenie nie zwalnia z wymogów dotyczących informacji reklamowej." },
      { id: "c7", stance: "against", text: "Tradeon Europe Ltd działa w Polsce legalnie w trybie transgranicznym.", confidence: 0.9, evidence_ids: ["ev-r1"], verdict: "upheld", critique: "Wpis w rejestrze potwierdzony; zarzut dotyczy reklamy, nie licencji." },
    ],
    arguments_for: ["c1", "c2", "c3", "c4"],
    arguments_against: ["c5", "c7"],
    arbiter_rationale: "Trzy z czterech zarzutów utrzymano po krytyce: nieujawnione wynagrodzenie, wynik bez źródła i powiązanie przez agencję PR. Na korzyść podmiotu przemawia obecność ostrzeżenia CFD i legalna działalność transgraniczna. Materiał nie obiecuje zysku wprost, dlatego sprawa trafia do weryfikacji, a nie do natychmiastowej eskalacji.",
  },
  evidence: orangeEvidence,
  recommendation: {
    action: "explain",
    label: "Wezwać firmę do wyjaśnień",
    next_step: "Wystąpić do Tradeon Europe Ltd o umowę z BrightReach Media i zasady wynagradzania podmiotów promujących; zweryfikować ręcznie próbkę kont komentujących.",
  },
  engine: ENGINE,
};

// ───────────────────────── Green case: compliant own material of a brokerage house
const GREEN_TEXT = [
  "Rachunek maklerski w Domu Maklerskim Wisła S.A.",
  "Materiał reklamowy. Dom Maklerski Wisła S.A. z siedzibą w Warszawie, nadzorowany przez Komisję Nadzoru Finansowego.",
  "Inwestuj w akcje i ETF-y notowane na GPW. Prowizja od 0,19%, minimum 3 zł za zlecenie. Pełna tabela opłat jest dostępna na stronie.",
  "Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków.",
  "Wyniki osiągnięte w przeszłości nie stanowią gwarancji ich osiągnięcia w przyszłości.",
  "Przed podjęciem decyzji zapoznaj się z regulaminem oraz dokumentami zawierającymi kluczowe informacje.",
].join("\n");

export const greenCase = {
  id: "8a2e7d40-11c3-4b6f-8d2a-5e9f3c7b2a02",
  status: "closed_ok",
  created_at: "2026-11-16T13:20:00Z",
  updated_at: "2026-11-17T09:00:00Z",
  title: "Strona produktowa rachunku maklerskiego DM Wisła",
  summary: "Materiał własny domu maklerskiego: oznaczony jako reklama, z wyraźną informacją o ryzyku i kosztach. Nie stwierdzono naruszeń.",
  modules: [2],
  primary_module: 2,
  risk_score: 8,
  compliance_score: 92,
  risk_level: "green",
  synthetic: true,
  ground_truth: "ok",
  demo_case: "case1",
  source: {
    platform: "web", url: "https://dmwisla.example/rachunek-maklerski", fetched_at: "2026-11-16T13:18:44Z", language: "pl",
    content_hash: "1e0c5a9b3f77d2e4486a0b9c1d2e3f4a5b6c7d8e9f00112233445566778899aa",
    text: GREEN_TEXT, archive: { html_key: "archive/green/page.html", screenshot_key: null },
  },
  entities: {
    investment_firm: { name: "Dom Maklerski Wisła S.A.", kind: "investment_firm", krs: "0000123456", country: "PL" },
    advertiser: { name: "Dom Maklerski Wisła S.A.", kind: "investment_firm", country: "PL" },
    others: [],
  },
  module_results: [
    { module: 2, plugin: "m2_risk_disclosure", score: 8, weight: 1, findings: [
      { code: "RISK_DISCLOSURE_PRESENT", severity: "info", text: "Informacja o ryzyku jest obecna i proporcjonalna do treści o korzyściach.", evidence_ids: ["ev-g1"] },
    ] },
  ],
  rules: rules("pass", {
    "5": ["unknown", 0.45, "Wielkość czcionki ostrzeżenia wymaga oceny wizualnej.", []],
    "6": ["na", 0.95, "Materiał nie dotyczy kontraktów CFD.", []],
    "10": ["na", 0.9, "Materiał nie zawiera prognoz.", []],
    "11": ["na", 0.9, "Brak porównań.", []],
    "18": ["na", 0.95, "Materiał własny firmy, bez podmiotu promującego.", []],
  }),
  registry_checks: [
    check("firms", "Dom Maklerski Wisła S.A.", "listed", "Zgodny wpis: Dom Maklerski Wisła S.A., zezwolenie z 2009 r."),
    check("warn", "Dom Maklerski Wisła S.A.", "not_listed", "Podmiot nie figuruje na liście ostrzeżeń"),
  ],
  graph: { nodes: [], edges: [], flagged_paths: [] },
  forensics: null,
  financials: null,
  debate: {
    rounds: [
      { round: 1, agent: "Oskarżyciel", role: "Zbiera argumenty za naruszeniem", summary: "Nie znalazł treści obiecujących zysk; zgłosił jedynie niepewność co do wyrazistości ostrzeżenia.", claim_ids: ["g1"] },
      { round: 2, agent: "Krytyk", role: "Weryfikuje każdy argument względem dowodów", summary: "Uznał zarzut za niepoparty dowodem tekstowym.", claim_ids: ["g1", "g2"] },
      { round: 3, agent: "Arbiter", role: "Waży utrzymane argumenty i wydaje ocenę", summary: "Brak utrzymanych zarzutów.", claim_ids: ["g2"] },
    ],
    claims: [
      { id: "g1", stance: "for", text: "Ostrzeżenie o ryzyku może być mało wyraziste wizualnie.", confidence: 0.2, evidence_ids: [], verdict: "rejected", critique: "Brak dowodu w tekście; kwestia do ewentualnej oceny wizualnej." },
      { id: "g2", stance: "against", text: "Materiał zawiera pełną informację o ryzyku i zastrzeżenie o wynikach historycznych.", confidence: 0.94, evidence_ids: ["ev-g1", "ev-g2"], verdict: "upheld", critique: null },
    ],
    arguments_for: [],
    arguments_against: ["g2"],
    arbiter_rationale: "Materiał spełnia wymogi formalne: jest oznaczony jako reklama, identyfikuje firmę i zawiera proporcjonalną informację o ryzyku oraz kosztach.",
  },
  evidence: [
    quoteEvidence(GREEN_TEXT, "ev-g1", "Informacja o ryzyku", "Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków."),
    quoteEvidence(GREEN_TEXT, "ev-g2", "Zastrzeżenie o wynikach historycznych", "Wyniki osiągnięte w przeszłości nie stanowią gwarancji ich osiągnięcia w przyszłości."),
  ],
  recommendation: { action: "none", label: "Bez działań", next_step: "Zamknąć sprawę; materiał pozostaje w monitoringu okresowym." },
  engine: { ...ENGINE, llm_used: false, model: null, duration_ms: 940 },
};

// ───────────────────────── Red case: unlicensed advisory (the live demo sample)
const RED_TEXT = [
  "Aurum Family Office: gwarantowany zysk 12% miesięcznie.",
  "Indywidualne zarządzanie majątkiem dla wymagających klientów. Nasi eksperci dobiorą dla Ciebie portfel i powiedzą dokładnie, co kupić i kiedy sprzedać.",
  "Gwarantujemy zysk 12% miesięcznie bez żadnego ryzyka.",
  "Nie potrzebujesz wiedzy: wpłać środki, a my zajmiemy się resztą. Oferta ograniczona, zostało tylko 7 miejsc do końca tygodnia!",
  "Współpracujemy z licencjonowanym doradcą inwestycyjnym nr 999 oraz kancelarią radcy prawnego Adama Sowy.",
  "Aurum Capital Partners sp. z o.o., Warszawa.",
].join("\n");

export const redCase = {
  id: "c41d9e77-2f58-4a3b-b6c0-7d1e4f8a3c03",
  status: "new",
  created_at: "2026-11-21T07:15:00Z",
  updated_at: "2026-11-21T07:15:00Z",
  title: "Aurum Family Office: gwarancja zysku 12% miesięcznie bez licencji",
  summary: "Podmiot spoza rejestru KNF oferuje zarządzanie portfelem i konkretne rekomendacje, gwarantując zysk bez ryzyka. Powołuje się na nieistniejący numer doradcy.",
  modules: [3, 2],
  primary_module: 3,
  risk_score: 89,
  compliance_score: 11,
  risk_level: "red",
  synthetic: true,
  ground_truth: "violation",
  demo_case: "case3",
  source: {
    platform: "web", url: "https://aurum-familyoffice.example/oferta", fetched_at: "2026-11-21T07:14:31Z", language: "pl",
    content_hash: "77aa10c2de5b9f8e3d4c6b1a0f9e8d7c6b5a49382716f5e4d3c2b1a009182736",
    text: RED_TEXT, archive: { html_key: "archive/red/page.html", screenshot_key: "archive/red/screenshot.png" },
  },
  entities: {
    investment_firm: null,
    advertiser: { name: "Aurum Capital Partners sp. z o.o.", kind: "company", krs: "0001098877", country: "PL", url: "https://aurum-familyoffice.example" },
    others: [{ name: "Adam Sowa", kind: "lawyer", country: "PL" }],
  },
  module_results: [
    { module: 3, plugin: "m3_shadow_advisory", score: 93, weight: 0.65, findings: [
      { code: "REGISTRY_NOT_LISTED", severity: "high", text: "Podmiot nie figuruje w żadnym rejestrze firm inwestycyjnych KNF.", evidence_ids: ["ev-rr1"] },
      { code: "ADVISORY_PHRASE", severity: "high", text: "Oferta konkretnych rekomendacji („co kupić i kiedy sprzedać”) to doradztwo inwestycyjne.", evidence_ids: ["ev-rq2", "ev-rl2"] },
      { code: "FAKE_LICENCE", severity: "high", text: "Numer doradcy inwestycyjnego 999 nie istnieje na liście KNF.", evidence_ids: ["ev-rq4", "ev-rr2"] },
    ] },
    { module: 2, plugin: "m2_risk_disclosure", score: 82, weight: 0.35, findings: [
      { code: "RULE_7", severity: "high", text: "Wprost zagwarantowany zysk bez ryzyka.", evidence_ids: ["ev-rq1", "ev-rl1"] },
      { code: "RULE_17", severity: "medium", text: "Presja czasowa: ograniczona liczba miejsc.", evidence_ids: ["ev-rq3"] },
    ] },
  ],
  rules: rules("fail", {
    "1": ["fail", 0.7, "Brak oznaczenia materiału jako reklamy.", []],
    "2": ["fail", 0.9, "Podmiot nie jest firmą inwestycyjną; brak identyfikacji licencji.", ["ev-rr1"]],
    "3": ["fail", 0.95, "Treść wprowadza w błąd co do ryzyka i statusu podmiotu.", ["ev-rq1"]],
    "4": ["fail", 0.96, "Brak jakiejkolwiek informacji o ryzyku.", ["ev-rq1"]],
    "5": ["na", 0.9, "Brak ostrzeżenia, którego wyrazistość można by ocenić.", []],
    "6": ["na", 0.8, "Materiał nie wskazuje na kontrakty CFD.", []],
    "7": ["fail", 0.98, "„Gwarantujemy zysk 12% miesięcznie bez żadnego ryzyka”.", ["ev-rq1", "ev-rl1"]],
    "8": ["na", 0.8, "Nie przedstawiono wyników historycznych.", []],
    "9": ["na", 0.8, "Nie przedstawiono wyników historycznych.", []],
    "10": ["fail", 0.85, "Deklarowany zysk nie opiera się na żadnych danych.", ["ev-rq1"]],
    "11": ["na", 0.9, "Brak porównań.", []],
    "12a": ["fail", 0.8, "Brak informacji o kosztach i opłatach.", []],
    "12b": ["fail", 0.75, "Zysk podany bez uwzględnienia opłat.", []],
    "13": ["unknown", 0.4, "Brak danych o opodatkowaniu; do oceny ręcznej.", []],
    "14": ["pass", 0.8, "Język prosty i zrozumiały.", []],
    "15": ["fail", 0.72, "Powołanie się na „licencjonowanego doradcę” sugeruje nadzór, którego nie ma.", ["ev-rq4"]],
    "16": ["na", 0.9, "Brak produktu objętego KID.", []],
    "17": ["fail", 0.9, "„Zostało tylko 7 miejsc do końca tygodnia”.", ["ev-rq3"]],
    "18": ["na", 0.9, "Materiał własny podmiotu.", []],
  }),
  registry_checks: [
    check("firms", "Aurum Capital Partners sp. z o.o.", "not_listed", "Brak wpisu"),
    check("cross", "Aurum Capital Partners sp. z o.o.", "not_listed", "Brak wpisu"),
    check("warn", "Aurum Capital Partners", "warning_listed", "Wpis z 3.11.2026: podejrzenie działalności bez zezwolenia (art. 178 ustawy o obrocie)"),
    check("advisors", "licencja nr 999", "not_listed", "Numer licencji nie istnieje"),
    check("kirp", "Adam Sowa", "inactive", "Nie wykonuje zawodu"),
    check("kidp", "nie dotyczy", "not_checked", "Nie powołano się na doradcę podatkowego", null),
  ],
  graph: {
    nodes: [
      { id: "r-co", type: "company", label: "Aurum Capital Partners", meta: { KRS: "0001098877", "data rejestracji": "2026-08-11" } },
      { id: "r-p1", type: "person", label: "Igor Zalewski", meta: { rola: "Jedyny członek zarządu i wspólnik" } },
      { id: "r-ad", type: "ad", label: "Oferta family office", meta: { opublikowano: "2026-11-20" } },
    ],
    edges: [
      { source: "r-p1", target: "r-co", type: "board_member", label: "prezes zarządu", suspicious: false },
      { source: "r-p1", target: "r-co", type: "owner", label: "100% udziałów", suspicious: false },
      { source: "r-co", target: "r-ad", type: "publishes", label: "publikuje", suspicious: true },
    ],
    flagged_paths: [],
  },
  forensics: null,
  financials: {
    company: "Aurum Capital Partners sp. z o.o.", krs: "0001098877", incorporated_on: "2026-08-11", age_months: 3,
    share_capital_pln: 5000, statements: [], flags: ["Spółka młodsza niż 12 miesięcy", "Brak złożonych sprawozdań finansowych"],
  },
  debate: {
    rounds: [
      { round: 1, agent: "Oskarżyciel", role: "Zbiera argumenty za naruszeniem", summary: "Gwarancja zysku, brak wpisu w rejestrach, fałszywy numer licencji, presja czasowa.", claim_ids: ["r1", "r2", "r3", "r4"] },
      { round: 1, agent: "Obrońca", role: "Zbiera okoliczności łagodzące", summary: "Wskazał, że podmiot deklaruje współpracę z licencjonowanym doradcą.", claim_ids: ["r5"] },
      { round: 2, agent: "Krytyk", role: "Weryfikuje każdy argument względem dowodów", summary: "Utrzymał wszystkie zarzuty; argument obrony odrzucił, bo numer licencji nie istnieje.", claim_ids: ["r1", "r2", "r3", "r4", "r5"] },
      { round: 3, agent: "Arbiter", role: "Waży utrzymane argumenty i wydaje ocenę", summary: "Cztery utrzymane zarzuty, brak okoliczności łagodzących.", claim_ids: ["r1", "r2", "r3", "r4"] },
    ],
    claims: [
      { id: "r1", stance: "for", text: "Materiał wprost gwarantuje zysk 12% miesięcznie bez ryzyka.", confidence: 0.98, evidence_ids: ["ev-rq1", "ev-rl1"], verdict: "upheld", critique: "Cytat dosłowny." },
      { id: "r2", stance: "for", text: "Podmiot oferuje doradztwo inwestycyjne i zarządzanie portfelem bez zezwolenia KNF.", confidence: 0.94, evidence_ids: ["ev-rq2", "ev-rr1", "ev-rl2"], verdict: "upheld", critique: "Brak wpisu w rejestrach potwierdzony na migawce z 14.11.2026." },
      { id: "r3", stance: "for", text: "Powołuje się na nieistniejący numer licencji doradcy inwestycyjnego.", confidence: 0.92, evidence_ids: ["ev-rq4", "ev-rr2"], verdict: "upheld", critique: "Lista doradców nie zawiera numeru 999." },
      { id: "r4", stance: "for", text: "Wywiera presję czasową na odbiorcę.", confidence: 0.85, evidence_ids: ["ev-rq3"], verdict: "upheld", critique: null },
      { id: "r5", stance: "against", text: "Podmiot deklaruje współpracę z licencjonowanym doradcą i radcą prawnym.", confidence: 0.08, evidence_ids: ["ev-rq4"], verdict: "rejected", critique: "Licencja nie istnieje, a wskazany radca nie wykonuje zawodu." },
    ],
    arguments_for: ["r1", "r2", "r3", "r4"],
    arguments_against: [],
    arbiter_rationale: "Wszystkie cztery zarzuty utrzymano po krytyce, a jedyny argument łagodzący okazał się nieprawdziwy. Podmiot figuruje na liście ostrzeżeń publicznych. Sprawa wymaga pilnej eskalacji.",
  },
  evidence: [
    quoteEvidence(RED_TEXT, "ev-rq1", "Gwarancja zysku bez ryzyka", "Gwarantujemy zysk 12% miesięcznie bez żadnego ryzyka"),
    quoteEvidence(RED_TEXT, "ev-rq2", "Oferta konkretnych rekomendacji", "powiedzą dokładnie, co kupić i kiedy sprzedać"),
    quoteEvidence(RED_TEXT, "ev-rq3", "Presja czasowa", "zostało tylko 7 miejsc do końca tygodnia"),
    quoteEvidence(RED_TEXT, "ev-rq4", "Powołanie się na licencję nr 999", "licencjonowanym doradcą inwestycyjnym nr 999"),
    { id: "ev-rl1", kind: "legal", label: "Zakaz sugerowania gwarancji zysku", legal_ref: "art. 44 ust. 2 lit. e rozporządzenia delegowanego (UE) 2017/565", attachment: "Załącznik 2: kryteria oceny informacji reklamowych.pdf" },
    { id: "ev-rl2", kind: "legal", label: "Działalność maklerska bez zezwolenia", legal_ref: "art. 178 ustawy o obrocie instrumentami finansowymi", attachment: "Załącznik 3: przesłanki doradztwa inwestycyjnego.pdf" },
    { id: "ev-rr1", kind: "registry", label: "Brak wpisu w rejestrze firm inwestycyjnych", url: REG.firms[2] },
    { id: "ev-rr2", kind: "registry", label: "Lista doradców inwestycyjnych: brak numeru 999", url: REG.advisors[2] },
    { id: "ev-ra1", kind: "archive", label: "Zrzut ekranu oferty", storage_key: "archive/red/screenshot.png" },
  ],
  recommendation: {
    action: "escalate",
    label: "Eskalować do Departamentu Postępowań",
    next_step: "Przekazać pakiet dowodowy do zawiadomienia o podejrzeniu popełnienia przestępstwa z art. 178 ustawy o obrocie; zabezpieczyć archiwum strony.",
  },
  engine: { ...ENGINE, duration_ms: 5320 },
};

export function toSummary(inc) {
  return {
    id: inc.id, title: inc.title, summary: inc.summary, modules: inc.modules, primary_module: inc.primary_module,
    risk_score: inc.risk_score, compliance_score: inc.compliance_score, risk_level: inc.risk_level, status: inc.status,
    created_at: inc.created_at, updated_at: inc.updated_at, synthetic: inc.synthetic, ground_truth: inc.ground_truth,
    demo_case: inc.demo_case, source: { platform: inc.source.platform, url: inc.source.url },
    advertiser: inc.entities.advertiser?.name ?? null, firm: inc.entities.investment_firm?.name ?? null,
    failed_rules: inc.rules.filter((r) => r.status === "fail").map((r) => r.id),
  };
}

// ───────────────────────── 30 labelled items: the calibration set (and the bulk of the queue)
// [title, risk_score, ground_truth, module, platform, advertiser, firm, daysAgo, status, failed_rules]
const LABELLED = [
  ["„Podwój kapitał w 30 dni”: reklama sygnałów forex", 96, "violation", 3, "facebook", "FX Masters Club", null, 1, "escalated", ["3", "4", "7", "17"]],
  ["Kanał Telegram z „pewnymi” typami na akcje", 91, "violation", 3, "x", "Giełdowy Insider", null, 2, "new", ["3", "7"]],
  ["Webinar: emerytura z krypto bez ryzyka", 87, "violation", 2, "youtube", "CoinFuture Academy", "CoinFuture OÜ", 2, "in_review", ["4", "7", "10"]],
  ["Family office z gwarantowaną stopą zwrotu 9%", 84, "violation", 3, "web", "Prestige Wealth sp. z o.o.", null, 3, "new", ["2", "7", "12a"]],
  ["Rolka: „CFD to najprostszy sposób na pasywny dochód”", 79, "violation", 1, "instagram", "@milioner_przed30", "TopMarkets Ltd", 4, "in_review", ["1", "4", "6", "18"]],
  ["Reklama konta demo z obietnicą bonusu 100%", 76, "violation", 2, "google_ads", "TopMarkets Ltd", "TopMarkets Ltd", 4, "new", ["4", "6"]],
  ["Poradnik inwestycyjny z linkiem afiliacyjnym do brokera", 73, "violation", 1, "youtube", "Kanał Finansowy Spokój", "EuroBroker AS", 5, "new", ["1", "18"]],
  ["Porównanie brokerów: ranking sponsorowany bez oznaczenia", 72, "ok", 1, "web", "PorownajBrokera.example", "EuroBroker AS", 6, "closed_ok", ["1"]],
  ["Oferta „doradztwa majątkowego” z rekomendacjami spółek", 68, "violation", 3, "web", "Kapitał Plus Consulting", null, 6, "in_review", ["2", "3"]],
  ["Film: jak zarobiłem 40% na kontraktach terminowych", 66, "violation", 1, "tiktok", "@trader_bartek", "TopMarkets Ltd", 7, "new", ["8", "9", "18"]],
  ["Baner: lokata strukturyzowana do 11% rocznie", 61, "ok", 2, "google_ads", "Bank Bursztynowy S.A.", "Bank Bursztynowy S.A.", 8, "closed_ok", ["5"]],
  ["Post sponsorowany o ETF-ach bez informacji o kosztach", 57, "violation", 2, "facebook", "DM Bałtyk S.A.", "DM Bałtyk S.A.", 9, "in_review", ["12a"]],
  ["Newsletter z analizą spółek i kodem rabatowym", 54, "ok", 1, "web", "Analizy Giełdowe Pro", "DM Bałtyk S.A.", 10, "closed_ok", ["18"]],
  ["Reklama aplikacji inwestycyjnej: ryzyko drobnym drukiem", 52, "violation", 2, "instagram", "InvestApp Europe", "InvestApp Europe UAB", 11, "in_review", ["5"]],
  ["Wpis ekspercki doradcy podatkowego o IKE i IKZE", 47, "ok", 3, "web", "Kancelaria Podatkowa Rejtan", null, 12, "closed_ok", []],
  ["Shorts: „3 spółki, które kupiłbym dziś”", 44, "violation", 3, "youtube", "@dywidendowy", null, 13, "new", ["3"]],
  ["Artykuł sponsorowany o funduszach obligacji", 41, "ok", 2, "web", "TFI Karpaty S.A.", "TFI Karpaty S.A.", 14, "closed_ok", []],
  ["Relacja z konferencji z logotypem brokera", 38, "ok", 1, "instagram", "@inwestorka_ewa", "EuroBroker AS", 15, "closed_ok", []],
  ["Kampania wizerunkowa domu maklerskiego", 33, "ok", 2, "facebook", "DM Bałtyk S.A.", "DM Bałtyk S.A.", 16, "closed_ok", []],
  ["Podcast edukacyjny o dywersyfikacji portfela", 29, "ok", 1, "youtube", "Podcast O Pieniądzach", null, 17, "closed_ok", []],
  ["Kalkulator prowizji na stronie brokera", 26, "ok", 2, "web", "EuroBroker AS", "EuroBroker AS", 18, "closed_ok", []],
  ["Oferta kancelarii: obsługa prawna funduszy", 24, "ok", 3, "web", "Kancelaria Sowa i Wspólnicy", null, 19, "closed_ok", []],
  ["Ukryta rekomendacja w recenzji książki o inwestowaniu", 22, "violation", 1, "web", "Blog Czytam o Giełdzie", "TopMarkets Ltd", 20, "new", ["18"]],
  ["Reklama IKE z pełną informacją o ryzyku", 19, "ok", 2, "google_ads", "TFI Karpaty S.A.", "TFI Karpaty S.A.", 21, "closed_ok", []],
  ["Materiał edukacyjny GPW o obligacjach", 15, "ok", 2, "web", "Fundacja Edukacji Giełdowej", null, 22, "closed_ok", []],
  ["Komunikat prasowy o wynikach kwartalnych TFI", 13, "ok", 2, "web", "TFI Karpaty S.A.", "TFI Karpaty S.A.", 23, "closed_ok", []],
  ["Strona „O nas” licencjonowanego doradcy inwestycyjnego", 11, "ok", 3, "web", "Tomasz Brzoza, doradca nr 512", null, 24, "closed_ok", []],
  ["Ogłoszenie o walnym zgromadzeniu spółki", 6, "ok", 2, "web", "Stalprodukt Północ S.A.", null, 26, "closed_ok", []],
];

const NOW = Date.parse("2026-11-21T09:00:00Z");
const pad = (n) => String(n).padStart(2, "0");

const generated = LABELLED.map(([title, risk, gt, module, platform, advertiser, firm, daysAgo, status, failed], i) => {
  const created = new Date(NOW - daysAgo * 86400000 - (i % 7) * 3600000).toISOString();
  return {
    id: `00000000-0000-4000-8000-0000000000${pad(i + 10)}`,
    title,
    summary: `Automatyczna ocena modułu ${module}: ${failed.length ? `naruszone kryteria ${failed.join(", ")}` : "nie stwierdzono naruszeń kryteriów"}.`,
    modules: [module], primary_module: module, risk_score: risk, compliance_score: 100 - risk,
    risk_level: risk >= 70 ? "red" : risk >= 35 ? "orange" : "green",
    status, created_at: created, updated_at: created, synthetic: true, ground_truth: gt, demo_case: null,
    source: { platform, url: `https://przyklad-${i + 1}.example/material` }, advertiser, firm, failed_rules: failed,
  };
});

/** The queue as GET /api/incidents returns it at startup (the red demo case arrives live). */
export const incidentSummaries = [toSummary(orangeCase), toSummary(greenCase), ...generated].sort((a, b) => b.risk_score - a.risk_score);

/** GET /api/calibration: every labelled incident (30 items). */
export const calibrationSet = {
  items: incidentSummaries
    .filter((it) => it.ground_truth)
    .map((it) => ({ id: it.id, title: it.title, risk_score: it.risk_score, ground_truth: it.ground_truth, module: it.primary_module })),
};

export const redSummary = toSummary(redCase);

export function trendsFrom(summaries, days = 30, now = NOW) {
  const out = [];
  for (let d = days - 1; d >= 0; d -= 1) {
    const date = new Date(now - d * 86400000).toISOString().slice(0, 10);
    out.push({
      date,
      items: summaries.filter((s) => s.created_at.slice(0, 10) === date).map((s) => ({ id: s.id, risk_score: s.risk_score, module: s.primary_module })),
    });
  }
  return { days: out };
}

export const trends = trendsFrom(incidentSummaries);

/** A full Incident for list rows that have no hand-written detail: empty graph, no forensics/financials. */
export function minimalIncident(summary) {
  const text = `${summary.title}\n${summary.summary}`;
  return {
    ...summary,
    advertiser: undefined, firm: undefined, failed_rules: undefined,
    source: { ...summary.source, fetched_at: summary.created_at, language: "pl", content_hash: "0".repeat(64), text, archive: { html_key: null, screenshot_key: null } },
    entities: {
      investment_firm: summary.firm ? { name: summary.firm, kind: "investment_firm" } : null,
      advertiser: summary.advertiser ? { name: summary.advertiser, kind: "advertiser" } : null,
      others: [],
    },
    module_results: [{ module: summary.primary_module, plugin: `m${summary.primary_module}`, score: summary.risk_score, weight: 1, findings: [] }],
    rules: rules("pass", Object.fromEntries(summary.failed_rules.map((id) => [id, ["fail", 0.75, "Kryterium naruszone w analizowanym materiale.", []]]))),
    registry_checks: [],
    graph: { nodes: [], edges: [], flagged_paths: [] },
    forensics: null,
    financials: null,
    debate: { rounds: [], claims: [], arguments_for: [], arguments_against: [], arbiter_rationale: "" },
    evidence: [],
    recommendation: summary.risk_score >= 70
      ? { action: "escalate", label: "Eskalować", next_step: "Przekazać sprawę do weryfikacji przez drugiego analityka." }
      : summary.risk_score >= 35
        ? { action: "explain", label: "Wezwać do wyjaśnień", next_step: "Zweryfikować ręcznie naruszone kryteria." }
        : { action: "none", label: "Bez działań", next_step: "Zamknąć sprawę." },
    engine: { ...ENGINE, llm_used: false, model: null, duration_ms: 610 },
  };
}

export const incidentsById = { [orangeCase.id]: orangeCase, [greenCase.id]: greenCase, [redCase.id]: redCase };
