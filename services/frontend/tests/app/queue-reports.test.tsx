import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { orangeCase, supervisorUser } from "../fixtures/data.mjs";
import { mockApi, renderApp } from "../helpers";

describe("Watchit workflow", () => {
  it("has collapsed filters, no report column, and no calibration link in the queue card", async () => {
    mockApi(); renderApp();
    await screen.findAllByTestId("queue-row");
    expect(screen.getByRole("link", { name: "Watchit, kolejka spraw" })).toBeInTheDocument();
    expect(screen.queryByText("Nadzór nad reklamą finansową")).not.toBeInTheDocument();
    expect(screen.getByText("Filtry", { selector: "summary" }).parentElement).not.toHaveAttribute("open");
    expect(screen.queryByRole("columnheader", { name: /Zgłoszenia/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Kalibracja progów" })).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /ID sprawy/ })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Rozpoczęto obsługę/ })).toBeInTheDocument();
  });
  it("sorts dates both ways and changes the graph period", async () => {
    const user = userEvent.setup(); const { calls } = mockApi(); renderApp();
    await screen.findAllByTestId("queue-row");
    const header = screen.getByRole("columnheader", { name: /Wykryto/ });
    await user.click(within(header).getByRole("button")); expect(header).toHaveAttribute("aria-sort", "ascending");
    await user.click(within(header).getByRole("button")); expect(header).toHaveAttribute("aria-sort", "descending");
    await user.click(screen.getByRole("button", { name: "7 dni" }));
    await waitFor(() => expect(calls.some((call) => call.path.includes("period=7d"))).toBe(true));
    await user.click(screen.getByRole("button", { name: "30 dni" }));
    await waitFor(() => expect(calls.some((call) => call.path.includes("period=30d"))).toBe(true));
  });
  it("hides AI verdict and reasoning initially and merges arguments into the recommendation", async () => {
    mockApi(); renderApp({ route: `/sprawy/${orangeCase.id}` });
    await screen.findByRole("heading", { level: 1 });
    const verdict = screen.getByText("Werdykt AI", { selector: "summary" }).parentElement!;
    expect(verdict).not.toHaveAttribute("open");
    const recommendation = screen.getByTestId("recommendation");
    expect(within(recommendation).getByTestId("debate-for")).toBeInTheDocument();
    expect(within(recommendation).getByText("Tok rozumowania").parentElement).not.toHaveAttribute("open");
    expect(screen.queryByText("Uzasadnienie arbitra")).not.toBeInTheDocument();
    expect(screen.queryByText("Zgłoszenia użytkowników")).not.toBeInTheDocument();
    expect(screen.getByText("Adres URL", { selector: "dt" })).toBeInTheDocument();
  });
  it("always analyses all modules and offers no module selector", async () => {
    const user = userEvent.setup(); const { calls } = mockApi(); renderApp();
    await screen.findAllByTestId("queue-row");
    await user.click(screen.getByRole("button", { name: "Analiza URL" }));
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.queryByLabelText("Moduł analityczny")).not.toBeInTheDocument();
    await user.type(dialog.getByLabelText("Adres materiału"), "https://przyklad.pl/oferta");
    await user.click(dialog.getByRole("button", { name: "Rozpocznij analizę" }));
    await waitFor(() => expect(calls.find((call) => call.path === "/api/scans" && call.method === "POST")?.body).toEqual({ url: "https://przyklad.pl/oferta" }));
  });
  it("shows calibration notifications to a supervisor and saves their own read state", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi((call) => {
      if (call.path === "/api/notifications") return { json: { items: [{ id: 7, created_at: "2026-11-22T00:00:00Z", read_at: null, message: "Zmieniono próg oznaczenia: 20 → 30.", details: {} }] } };
      if (call.path === "/api/notifications/7/read") return { json: { id: 7, read_at: "2026-11-22T00:01:00Z" } };
    }, { user: supervisorUser });
    renderApp();
    await user.click(await screen.findByRole("button", { name: "Powiadomienia, nieprzeczytane: 1" }));
    await user.click(await screen.findByRole("button", { name: "Oznacz jako przeczytane" }));
    await waitFor(() => expect(calls.some((call) => call.path === "/api/notifications/7/read" && call.method === "POST")).toBe(true));
    await user.keyboard("{Escape}");
    expect(await screen.findByRole("button", { name: "Powiadomienia, nieprzeczytane: 0" })).toBeInTheDocument();
  });
});
