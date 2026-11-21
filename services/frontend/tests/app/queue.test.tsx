import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { countLevels, DEFAULT_THRESHOLDS } from "../../src/domain/levels";
import { incidentSummaries, redSummary } from "../fixtures/data.mjs";
import { FakeSocket, mockApi, renderApp } from "../helpers";

const rows = () => screen.getAllByTestId("queue-row");
const count = (level: string) => within(screen.getByTestId(`count-${level}`)).getByText(/^\d+$/).textContent;

async function ready() {
  await waitFor(() => expect(screen.getAllByTestId("queue-row").length).toBeGreaterThan(0));
}

/** A live event makes the trend chart refetch: let that request settle before the test ends. */
async function trendRefetched(calls: { path: string }[]) {
  await waitFor(() => expect(calls.filter((c) => c.path.startsWith("/api/stats/trends")).length).toBeGreaterThan(1));
  await act(async () => {});
}

describe("triage queue", () => {
  it("lists incidents most dangerous first with counts per level", async () => {
    mockApi();
    renderApp();
    await ready();
    expect(rows()).toHaveLength(incidentSummaries.length);
    const levels = rows().map((r) => r.dataset.level);
    expect(levels).toEqual([...levels].sort((a, b) => ["red", "orange", "green"].indexOf(a ?? "") - ["red", "orange", "green"].indexOf(b ?? "")));
    expect(within(rows()[0] as HTMLElement).getByText("Krytyczne")).toBeInTheDocument();
    const expected = countLevels(incidentSummaries.map((i) => i.risk_score), DEFAULT_THRESHOLDS);
    expect(count("red")).toBe(String(expected.red));
    expect(count("orange")).toBe(String(expected.orange));
    expect(count("green")).toBe(String(expected.green));
    expect(screen.getByTestId("nav-flagged")).toHaveTextContent(String(expected.red + expected.orange));
  });

  it("derives levels from the analyst's thresholds, not from the stored risk_level", async () => {
    mockApi();
    renderApp({ thresholds: { red: 50, orange: 20 } });
    await ready();
    expect(count("red")).toBe(String(incidentSummaries.filter((i) => i.risk_score >= 50).length));
    expect(count("red")).not.toBe(String(countLevels(incidentSummaries.map((i) => i.risk_score), DEFAULT_THRESHOLDS).red));
    expect(Number(count("red")) + Number(count("orange")) + Number(count("green"))).toBe(30);
  });

  it("filters by module, level and text, and clears filters", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp();
    await ready();

    await user.selectOptions(screen.getByLabelText("Moduł"), "3");
    const m3 = incidentSummaries.filter((i) => i.modules.includes(3)).length;
    expect(rows()).toHaveLength(m3);
    expect(screen.getByTestId("queue-count")).toHaveTextContent(`Pokazano ${m3} z 30 spraw`);

    await user.selectOptions(screen.getByLabelText("Poziom ryzyka"), "red");
    expect(rows().every((r) => r.dataset.level === "red")).toBe(true);

    await user.type(screen.getByLabelText("Szukaj"), "telegram");
    expect(rows()).toHaveLength(1);
    expect(rows()[0]).toHaveTextContent("Kanał Telegram");

    await user.type(screen.getByLabelText("Szukaj"), "zzz");
    expect(screen.queryAllByTestId("queue-row")).toHaveLength(0);
    expect(screen.getByText("Żadna sprawa nie spełnia filtrów")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Wyczyść filtry" }));
    expect(rows()).toHaveLength(30);
  });

  it("reads filters from the URL (deep link, command palette)", async () => {
    mockApi();
    renderApp({ route: "/?poziom=green&modul=2" });
    await ready();
    expect(rows().every((r) => r.dataset.level === "green")).toBe(true);
    expect(screen.getByLabelText("Moduł")).toHaveValue("2");
  });

  it("adds incident:new rows live with a highlight", async () => {
    const { calls } = mockApi();
    const socket = new FakeSocket();
    renderApp({ socket });
    await ready();
    const incoming = { ...redSummary, id: "live-1", title: "Nowa reklama na żywo", risk_score: 44 };
    act(() => socket.emit("incident:new", incoming));
    expect(rows()).toHaveLength(31);
    const row = screen.getByText("Nowa reklama na żywo").closest("tr") as HTMLElement;
    expect(row).toHaveClass("queue__row--fresh");
    expect(within(row).getByText("Nowa")).toBeInTheDocument();
    expect(count("orange")).toBe(String(countLevels(incidentSummaries.map((i) => i.risk_score), DEFAULT_THRESHOLDS).orange + 1));
    await trendRefetched(calls);
  });

  it("shows a persistent alert for alert:high, links to the case and pins it to the top", async () => {
    const user = userEvent.setup();
    mockApi();
    const socket = new FakeSocket();
    renderApp({ socket });
    await ready();
    // Lower score than the current top row: only the pin can put it first.
    const alert = { ...redSummary, risk_score: 71 };
    act(() => {
      socket.emit("incident:new", alert);
      socket.emit("alert:high", alert);
    });
    const banner = screen.getByRole("alert");
    expect(banner).toHaveTextContent("Nowy incydent wysokiego ryzyka");
    expect(within(banner).getByRole("link", { name: "Otwórz sprawę" })).toHaveAttribute("href", `/sprawy/${redSummary.id}`);
    expect(rows()[0]).toHaveTextContent(redSummary.title);
    expect(rows()).toHaveLength(31);

    await user.click(within(banner).getByRole("button", { name: /Zamknij alert/ }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(rows()[0]).not.toHaveTextContent(redSummary.title);
  });

  it("applies incident:updated from another analyst", async () => {
    const { calls } = mockApi();
    const socket = new FakeSocket();
    renderApp({ socket });
    await ready();
    const target = incidentSummaries[1];
    if (!target) throw new Error("fixture missing");
    act(() => socket.emit("incident:updated", { ...target, status: "closed_violation" }));
    expect(screen.getByLabelText(`Status sprawy: ${target.title}`)).toHaveValue("closed_violation");
    await trendRefetched(calls);
  });

  it("ignores malformed socket payloads", async () => {
    mockApi();
    const socket = new FakeSocket();
    renderApp({ socket });
    await ready();
    act(() => {
      socket.emit("incident:new", null);
      socket.emit("alert:high", undefined);
    });
    expect(rows()).toHaveLength(30);
  });

  it("changes status inline through PATCH", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi();
    renderApp();
    await ready();
    const target = incidentSummaries[0];
    if (!target) throw new Error("fixture missing");
    await user.selectOptions(screen.getByLabelText(`Status sprawy: ${target.title}`), "closed_violation");
    await waitFor(() => expect(calls.some((c) => c.method === "PATCH")).toBe(true));
    const patch = calls.find((c) => c.method === "PATCH");
    expect(patch?.path).toBe(`/api/incidents/${target.id}`);
    expect(patch?.body).toEqual({ status: "closed_violation" });
    await waitFor(() => expect(screen.getByLabelText(`Status sprawy: ${target.title}`)).toHaveValue("closed_violation"));
  });

  it("reports a failed status change without losing the row", async () => {
    const user = userEvent.setup();
    mockApi((call) => (call.method === "PATCH" ? { status: 422, json: { detail: "Nieprawidłowy status." } } : undefined));
    renderApp();
    await ready();
    const target = incidentSummaries[0];
    if (!target) throw new Error("fixture missing");
    await user.selectOptions(screen.getByLabelText(`Status sprawy: ${target.title}`), "closed_ok");
    expect(await screen.findByText(/Nie zmieniono statusu. Nieprawidłowy status./)).toBeInTheDocument();
    expect(screen.getByLabelText(`Status sprawy: ${target.title}`)).toHaveValue(target.status);
  });

  it("renders an error state with retry when the list cannot be loaded", async () => {
    const user = userEvent.setup();
    let fail = true;
    mockApi((call) => (fail && call.path === "/api/incidents" ? { status: 500, json: { detail: "Baza danych jest niedostępna." } } : undefined));
    renderApp();
    expect(await screen.findByText("Baza danych jest niedostępna.")).toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole("button", { name: "Spróbuj ponownie" }));
    await ready();
  });

  it("survives a network failure (fetch rejects) with a readable message", async () => {
    const { fn } = mockApi();
    fn.mockRejectedValue(new TypeError("Failed to fetch"));
    renderApp();
    expect(await screen.findByText(/Brak połączenia z serwerem/)).toBeInTheDocument();
  });

  it("shows an empty queue state when there are no incidents", async () => {
    mockApi((call) => (call.path === "/api/incidents" ? { json: { items: [], total: 0 } } : call.path.startsWith("/api/stats/trends") ? { json: { days: [] } } : undefined));
    renderApp();
    expect(await screen.findByText("Kolejka jest pusta")).toBeInTheDocument();
    expect(screen.getByText("Brak incydentów w tym okresie")).toBeInTheDocument();
  });

  it("shows the live connection state", async () => {
    mockApi();
    const socket = new FakeSocket();
    renderApp({ socket });
    await ready();
    await waitFor(() => expect(screen.getByText("Połączono na żywo")).toBeInTheDocument());
    act(() => socket.emit("disconnect", "transport close"));
    expect(screen.getByText("Brak połączenia na żywo")).toBeInTheDocument();
  });
});

describe("scan, demo and jobs", () => {
  it("validates the URL, posts the scan and tracks scan:progress", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi();
    const socket = new FakeSocket();
    renderApp({ socket });
    await ready();

    await user.click(screen.getByRole("button", { name: "Skanuj URL" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Adres materiału"), "nie-adres");
    await user.click(within(dialog).getByRole("button", { name: "Zleć skanowanie" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Podaj pełny adres");
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    await user.clear(within(dialog).getByLabelText("Adres materiału"));
    await user.type(within(dialog).getByLabelText("Adres materiału"), "https://broker.example/oferta");
    await user.click(within(dialog).getByRole("button", { name: "Zleć skanowanie" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(calls.find((c) => c.method === "POST" && c.path === "/api/scans")?.body).toEqual({ url: "https://broker.example/oferta" });

    act(() => socket.emit("scan:progress", { id: "job-1", url: "https://broker.example/oferta", state: "analyzing", incident_id: null, error: null, created_at: "2026-11-21T09:00:00Z", finished_at: null }));
    await user.click(screen.getByRole("button", { name: /Zadania skanowania, aktywne: 1/ }));
    expect(await screen.findByText("Analiza")).toBeInTheDocument();

    act(() => socket.emit("scan:progress", { id: "job-1", url: "https://broker.example/oferta", state: "done", incident_id: "abc", error: null, created_at: "2026-11-21T09:00:00Z", finished_at: "2026-11-21T09:00:05Z" }));
    expect(await screen.findByRole("link", { name: "Otwórz sprawę" })).toHaveAttribute("href", "/sprawy/abc");
  });

  it("shows the server's reason when a scan is rejected", async () => {
    const user = userEvent.setup();
    mockApi((call) => (call.method === "POST" && call.path === "/api/scans" ? { status: 422, json: { detail: "Domena jest na liście wykluczeń." } } : undefined));
    renderApp();
    await ready();
    await user.click(screen.getByRole("button", { name: "Skanuj URL" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Adres materiału"), "https://x.example");
    await user.click(within(dialog).getByRole("button", { name: "Zleć skanowanie" }));
    expect(await within(dialog).findByText("Domena jest na liście wykluczeń.")).toBeInTheDocument();
  });

  it("triggers the demo sample from the demo menu", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi();
    renderApp();
    await ready();
    await user.click(screen.getByRole("button", { name: "Demo" }));
    await user.click(await screen.findByRole("menuitem", { name: /Uruchom próbkę demo/ }));
    await waitFor(() => expect(calls.find((c) => c.path === "/api/demo/trigger")?.body).toEqual({ case: "case3" }));
    expect(await screen.findByText(/Próbka demo została przekazana/)).toBeInTheDocument();
  });

  it("opens the command palette with Ctrl+K and jumps to a case", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp();
    await ready();
    await user.keyboard("{Control>}k{/Control}");
    const input = await screen.findByPlaceholderText(/Wpisz tytuł sprawy/);
    await user.type(input, "Tradeon");
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { level: 1, name: /Recenzja platformy CFD Tradeon/ })).toBeInTheDocument();
  });

  it("renders the 404 route", async () => {
    mockApi();
    renderApp({ route: "/nie-ma-takiej" });
    expect(await screen.findByText("Nie ma takiej strony")).toBeInTheDocument();
  });
});
