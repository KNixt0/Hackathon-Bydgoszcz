import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ComplianceMatrix } from "../../src/components/case/ComplianceMatrix";
import { DebateBlock } from "../../src/components/case/DebateBlock";
import { FinancialsPanel } from "../../src/components/case/FinancialsPanel";
import { ForensicsPanel } from "../../src/components/case/ForensicsPanel";
import { RegistryChecks } from "../../src/components/case/RegistryChecks";
import { RelationshipGraph } from "../../src/components/case/RelationshipGraph";
import { greenCase, orangeCase, redCase } from "../fixtures/data.mjs";
import { mockApi, renderApp, renderWithRouter } from "../helpers";

const orangeUrl = `/sprawy/${orangeCase.id}`;

async function caseReady(title: RegExp) {
  expect(await screen.findByRole("heading", { level: 1, name: title })).toBeInTheDocument();
}

describe("case detail", () => {
  it("shows the verdict: level, Compliance Score, raw risk, recommendation, synthetic badge, exports", async () => {
    mockApi();
    renderApp({ route: orangeUrl });
    await caseReady(/Recenzja platformy CFD Tradeon/);
    const verdict = within(screen.getByRole("region", { name: /Werdykt/ }));
    expect(verdict.getByText("Do weryfikacji")).toBeInTheDocument();
    expect(verdict.getByTestId("compliance-score")).toHaveTextContent("42");
    expect(verdict.getByText(/Surowy wynik ryzyka/)).toHaveTextContent("58");
    expect(verdict.getByText("Wezwać firmę do wyjaśnień")).toBeInTheDocument();
    expect(verdict.getByText(/Następne działanie/)).toBeInTheDocument();
    expect(verdict.getByText("Dane syntetyczne")).toBeInTheDocument();
    expect(verdict.getByRole("link", { name: /Pakiet dowodowy PDF/ })).toHaveAttribute("href", `/api/incidents/${orangeCase.id}/export.pdf`);
    expect(verdict.getByRole("link", { name: "CSV" })).toHaveAttribute("href", `/api/incidents/${orangeCase.id}/export.csv`);
    expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual([
      "1Werdykt", "2Wykresy i wizualizacje", "3Argumenty „za” i „przeciw”", "4Źródła dowodowe",
    ]);
  });

  it("recomputes the level on the case from the analyst's threshold", async () => {
    mockApi();
    renderApp({ route: orangeUrl, thresholds: { red: 50, orange: 20 } });
    await caseReady(/Recenzja platformy CFD Tradeon/);
    expect(within(screen.getByRole("region", { name: /Werdykt/ })).getByText("Krytyczne")).toBeInTheDocument();
  });

  it("opens the evidence drawer from a citation chip with the quote highlighted in the source text", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: orangeUrl });
    await caseReady(/Recenzja platformy CFD Tradeon/);
    expect(screen.queryByTestId("evidence-drawer")).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: /Cytat: Deklaracja wyniku 18%/ })[0] as HTMLElement);
    const drawer = within(await screen.findByTestId("evidence-drawer"));
    expect(drawer.getByRole("heading", { name: "Deklaracja wyniku 18% bez okresu i źródła" })).toBeInTheDocument();
    const mark = drawer.getByTestId("quote-highlight");
    expect(mark.tagName).toBe("MARK");
    expect(mark).toHaveTextContent("mój portfel urósł o 18%");
    // the highlight sits inside the full archived text, at the contract's span
    const source = mark.parentElement as HTMLElement;
    expect(source.textContent).toBe(orangeCase.source.text);
    expect(drawer.getByText(/Cytowane w sprawie/)).toBeInTheDocument();

    // next evidence, then close
    await user.click(drawer.getByRole("button", { name: "Następny dowód" }));
    expect(await screen.findByRole("heading", { name: "Zapewnienie o pełnym bezpieczeństwie środków" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("evidence-drawer")).not.toBeInTheDocument());
  });

  it("deep-links to a legal reference in the drawer", async () => {
    mockApi();
    renderApp({ route: `${orangeUrl}?dowod=ev-l2` });
    const drawer = within(await screen.findByTestId("evidence-drawer"));
    expect(drawer.getByTestId("legal-ref")).toHaveTextContent("art. 76 ustawy o obrocie instrumentami finansowymi");
    expect(drawer.getByText(/Źródło wymogu/)).toBeInTheDocument();
  });

  it("shows register entry, account samples and archived HTML in the drawer", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: `${orangeUrl}?dowod=ev-r1` });
    let drawer = within(await screen.findByTestId("evidence-drawer"));
    expect(drawer.getByText("Firmy zagraniczne działające transgranicznie")).toBeInTheDocument();
    expect(drawer.getByText(/CySEC 311\/16/)).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await user.click((await screen.findAllByRole("button", { name: /Konta: Próbka podejrzanych kont/ }))[0] as HTMLElement);
    drawer = within(await screen.findByTestId("evidence-drawer"));
    expect(drawer.getByText("kasia4821")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await user.click((await screen.findAllByRole("button", { name: /Zarchiwizowany kod HTML/ }))[0] as HTMLElement);
    drawer = within(await screen.findByTestId("evidence-drawer"));
    expect(await drawer.findByText("<html>archiwum</html>")).toBeInTheDocument();
  });

  it("handles a deep link to evidence that does not exist", async () => {
    mockApi();
    renderApp({ route: `${orangeUrl}?dowod=nie-ma` });
    expect(await screen.findByText("Nie znaleziono dowodu")).toBeInTheDocument();
  });

  it("renders the debate: both sides, critic verdicts, three rounds, arbiter", async () => {
    mockApi();
    renderApp({ route: orangeUrl });
    await caseReady(/Recenzja platformy CFD Tradeon/);
    const forCol = within(screen.getByTestId("debate-for"));
    const againstCol = within(screen.getByTestId("debate-against"));
    expect(forCol.getAllByTestId("claim")).toHaveLength(4);
    expect(againstCol.getAllByTestId("claim")).toHaveLength(3);
    expect(forCol.getByText("Krytyk: Osłabiony")).toBeInTheDocument();
    expect(againstCol.getByText("Krytyk: Odrzucony")).toBeInTheDocument();
    expect(forCol.getAllByText("Krytyk: Utrzymany")).toHaveLength(3);
    expect(forCol.getByText(/pewność 88%/)).toBeInTheDocument();
    expect(screen.getByText("Uzasadnienie arbitra")).toBeInTheDocument();
    for (const n of [1, 2, 3]) expect(screen.getByText(`Runda ${n} z 3`)).toBeInTheDocument();
  });

  it("shows the 19-row compliance matrix with legal basis and register badges", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: `${orangeUrl}?widok=zgodnosc` });
    await caseReady(/Recenzja platformy CFD Tradeon/);
    expect(screen.getAllByTestId("rule-row")).toHaveLength(19);
    const rule18 = screen.getAllByTestId("rule-row").find((r) => within(r).queryByText("18")) as HTMLElement;
    expect(within(rule18).getByText("Naruszenie")).toBeInTheDocument();
    expect(within(rule18).getAllByText("art. 76 ustawy o obrocie instrumentami finansowymi").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("registry-check")).toHaveLength(orangeCase.registry_checks.length);

    // a citation inside the matrix opens the same drawer
    await user.click(within(rule18).getByRole("button", { name: /Cytat: Kod polecający/ }));
    expect(await screen.findByTestId("quote-highlight")).toHaveTextContent("KUBA50");
  });

  it("selecting a graph node shows its details", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: `${orangeUrl}?widok=powiazania` });
    await caseReady(/Recenzja platformy CFD Tradeon/);
    expect(screen.getByText("Oznaczone ścieżki (1)")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Agencja PR: BrightReach Media/ }));
    const details = within(screen.getByTestId("node-details"));
    expect(details.getByText("0001045512")).toBeInTheDocument();
    expect(details.getByText("Na oznaczonej ścieżce")).toBeInTheDocument();
    expect(details.getByText(/Relacje \(3\)/)).toBeInTheDocument();
  });

  it("changes status from the case pipeline", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi();
    renderApp({ route: orangeUrl });
    await caseReady(/Recenzja platformy CFD Tradeon/);
    await user.click(screen.getByRole("button", { name: "Eskaluj" }));
    await waitFor(() => expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ status: "escalated" }));
    expect(await screen.findByRole("button", { name: "Zamknij: naruszenie" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Eskaluj" })).not.toBeInTheDocument();
  });

  it("green case: every data-less sub-panel shows an empty state, not a broken chart", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: `/sprawy/${greenCase.id}` });
    await caseReady(/Strona produktowa rachunku maklerskiego/);
    expect(screen.getByTestId("compliance-score")).toHaveTextContent("92");
    expect(within(screen.getByRole("region", { name: /Werdykt/ })).getByText("Zgodne")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /Graf powiązań/ }));
    expect(await screen.findByText("Brak danych o powiązaniach")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /Opinie i konta/ }));
    expect(await screen.findByText("Brak analizy opinii i kont")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /Finanse i KRS/ }));
    expect(await screen.findByText("Brak danych finansowych")).toBeInTheDocument();
    expect(within(screen.getByTestId("debate-for")).getByText("Krytyk: Odrzucony")).toBeInTheDocument();
  });

  it("a case with no analysis artefacts renders all four blocks with empty states", async () => {
    mockApi();
    renderApp({ route: "/sprawy/00000000-0000-4000-8000-000000000010" });
    await caseReady(/Podwój kapitał/);
    expect(screen.getByText("Brak debaty agentów")).toBeInTheDocument();
    expect(screen.getByText("Brak dowodów")).toBeInTheDocument();
    expect(screen.getByText("Brak sprawdzeń w rejestrach")).toBeInTheDocument();
    expect(screen.getAllByTestId("rule-row")).toHaveLength(19);
  });

  it("shows a not-found state for an unknown case id", async () => {
    mockApi();
    renderApp({ route: "/sprawy/nie-istnieje" });
    expect(await screen.findByText("Nie ma takiej sprawy")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Wróć do kolejki" })).toHaveAttribute("href", "/");
  });

  it("shows a retryable error when the case cannot be loaded", async () => {
    mockApi((call) => (call.path.startsWith("/api/incidents/") ? { status: 500, json: { detail: "Błąd odczytu sprawy." } } : undefined));
    renderApp({ route: orangeUrl });
    expect(await screen.findByText("Błąd odczytu sprawy.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Spróbuj ponownie" })).toBeInTheDocument();
  });
});

describe("case sub-panels with empty or partial data", () => {
  it("RelationshipGraph: empty graph", () => {
    renderWithRouter(<RelationshipGraph graph={{ nodes: [], edges: [], flagged_paths: [] }} />);
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Brak danych o powiązaniach");
  });
  it("RelationshipGraph: tolerates edges that point at unknown nodes and no flagged paths", () => {
    renderWithRouter(<RelationshipGraph graph={{ ...redCase.graph, edges: [...redCase.graph.edges, { source: "r-co", target: "ghost", type: "related", label: "?", suspicious: true }] }} />);
    expect(screen.getByRole("button", { name: /Spółka: Aurum Capital Partners/ })).toBeInTheDocument();
    expect(screen.getByText(/nie oznaczył żadnej ścieżki/)).toBeInTheDocument();
  });
  it("ForensicsPanel: null", () => {
    renderWithRouter(<ForensicsPanel forensics={null} />);
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Brak analizy opinii i kont");
  });
  it("ForensicsPanel: present but with empty lists", () => {
    renderWithRouter(<ForensicsPanel forensics={{ opinion_timeline: [], accounts: { total: 0, share_younger_14d: 0, age_buckets: [], origins: [], name_patterns: [] }, anomalies: [], sample_accounts: [] }} />);
    expect(screen.getByText("Brak danych o rozkładzie opinii w czasie.")).toBeInTheDocument();
    expect(screen.getByText("Nie wykryto powtarzalnych wzorców.")).toBeInTheDocument();
  });
  it("FinancialsPanel: null and all-null fields", () => {
    const { unmount } = renderWithRouter(<FinancialsPanel financials={null} />);
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Brak danych finansowych");
    unmount();
    renderWithRouter(<FinancialsPanel financials={{ company: "X sp. z o.o.", krs: null, incorporated_on: null, age_months: null, share_capital_pln: null, statements: [], flags: [] }} />);
    expect(screen.getAllByText("brak danych").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText(/nie złożyła jeszcze żadnego sprawozdania/)).toBeInTheDocument();
  });
  it("FinancialsPanel: incorporation date and statements", () => {
    renderWithRouter(<FinancialsPanel financials={orangeCase.financials} />);
    expect(screen.getByText("02.03.2026")).toBeInTheDocument();
    expect(screen.getByText("Spółka młodsza niż 12 miesięcy")).toBeInTheDocument();
    expect(screen.getAllByText("Nie złożono")).toHaveLength(2);
  });
  it("ComplianceMatrix and RegistryChecks: empty", () => {
    renderWithRouter(<><ComplianceMatrix rules={[]} /><RegistryChecks checks={[]} /></>);
    expect(screen.getByText("Brak oceny kryteriów")).toBeInTheDocument();
    expect(screen.getByText("Brak sprawdzeń w rejestrach")).toBeInTheDocument();
  });
  it("DebateBlock: empty debate", () => {
    renderWithRouter(<DebateBlock debate={{ rounds: [], claims: [], arguments_for: [], arguments_against: [], arbiter_rationale: "" }} />);
    expect(screen.getByText("Brak debaty agentów")).toBeInTheDocument();
  });
});

describe("party verification badges", () => {
  it("shows the public-warning entry even when the register uses a shortened name", async () => {
    mockApi((call) => (call.path === `/api/incidents/${redCase.id}` ? { json: redCase } : undefined));
    renderApp({ route: `/sprawy/${redCase.id}` });
    await caseReady(/Aurum Family Office/);
    const verdict = within(screen.getByRole("region", { name: /Werdykt/ }));
    expect(verdict.getByText("Na liście ostrzeżeń publicznych KNF")).toBeInTheDocument();
    expect(verdict.getByText("Poza rejestrem firm inwestycyjnych")).toBeInTheDocument();
    expect(verdict.getByText("Krytyczne")).toBeInTheDocument();
    expect(verdict.getByTestId("compliance-score")).toHaveTextContent("11");
  });
});
