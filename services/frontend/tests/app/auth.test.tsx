import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { AuditEntry } from "../../src/types/api";
import { analystUser, orangeCase, supervisorUser } from "../fixtures/data.mjs";
import { FakeSocket, mockApi, renderApp } from "../helpers";

async function onLoginPage() {
  expect(await screen.findByRole("heading", { level: 1, name: "Logowanie" })).toBeInTheDocument();
}

describe("login and session", () => {
  it("redirects every route to the login page without a session, and does not call /me", async () => {
    const { calls } = mockApi(undefined, { user: null });
    const socket = new FakeSocket();
    renderApp({ route: `/sprawy/${orangeCase.id}`, socket });
    await onLoginPage();
    expect(screen.getByLabelText("Adres e-mail")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Hasło")).toHaveAttribute("type", "password");
    expect(calls.map((c) => c.path)).toEqual(["/api/auth/config"]);
    expect(socket.connected).toBe(false); // the socket connects only after login
  });

  it("shows the demo buttons only when the server enables the demo login", async () => {
    mockApi(undefined, { user: null, demoLogin: false });
    renderApp();
    await onLoginPage();
    expect(screen.queryByRole("button", { name: /Zaloguj jako/ })).not.toBeInTheDocument();
  });

  it("demo login as analyst returns to the requested case; the top bar shows the user and logout", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(undefined, { user: null });
    const socket = new FakeSocket();
    renderApp({ route: `/sprawy/${orangeCase.id}`, socket });
    await onLoginPage();
    await user.click(screen.getByRole("button", { name: "Zaloguj jako analityk (demo)" }));
    expect(await screen.findByRole("heading", { level: 1, name: orangeCase.title })).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/api/auth/demo")?.body).toEqual({ role: "ANALYST" });
    const chip = within(screen.getByTestId("user-chip"));
    expect(chip.getByText(analystUser.name)).toBeInTheDocument();
    expect(chip.getByText("Analityk")).toBeInTheDocument();
    await waitFor(() => expect(socket.connected).toBe(true));
    expect(screen.queryByRole("link", { name: /Dziennik audytu/ })).not.toBeInTheDocument();

    await user.click(chip.getByRole("button", { name: /Wyloguj/ }));
    await onLoginPage();
    expect(calls.some((c) => c.path === "/api/auth/logout" && c.method === "POST")).toBe(true);
    expect(socket.connected).toBe(false);
  });

  it("password login as supervisor; the supervisor sees the audit log", async () => {
    const user = userEvent.setup();
    mockApi(undefined, { user: null });
    renderApp();
    await onLoginPage();
    await user.type(screen.getByLabelText("Adres e-mail"), supervisorUser.email);
    await user.type(screen.getByLabelText("Hasło"), "haslo-demo");
    await user.click(screen.getByRole("button", { name: "Zaloguj się" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Kolejka spraw" })).toBeInTheDocument();
    expect(within(screen.getByTestId("user-chip")).getByText("Kierownik")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Dziennik audytu/ })).toHaveAttribute("href", "/audyt");
  });

  it("a wrong password gives an error that does not blame the user and keeps the form", async () => {
    const user = userEvent.setup();
    mockApi(undefined, { user: null });
    renderApp();
    await onLoginPage();
    await user.click(screen.getByRole("button", { name: "Zaloguj się" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Wpisz adres e-mail i hasło.");
    await user.type(screen.getByLabelText("Adres e-mail"), "ktos@uknf.local");
    await user.type(screen.getByLabelText("Hasło"), "zle");
    await user.click(screen.getByRole("button", { name: "Zaloguj się" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ten adres e-mail i hasło nie pasują do żadnego konta");
    expect(screen.getByLabelText("Adres e-mail")).toHaveValue("ktos@uknf.local");
    expect(screen.getByLabelText("Adres e-mail")).toHaveAttribute("aria-invalid", "true");
  });

  it("a 401 during the session returns to the login page with an explanation", async () => {
    let expired = false;
    mockApi((call) => (expired && call.path.startsWith("/api/incidents/") ? { status: 401, json: { detail: "authentication required" } } : undefined));
    const user = userEvent.setup();
    renderApp();
    expect(await screen.findByRole("heading", { level: 1, name: "Kolejka spraw" })).toBeInTheDocument();
    expired = true;
    await user.click((await screen.findAllByRole("link", { name: orangeCase.title }))[0] as HTMLElement);
    await onLoginPage();
    expect(screen.getByRole("status")).toHaveTextContent("Sesja wygasła");
  });

  it("an analyst opening /audyt sees that the page is for the supervisor", async () => {
    const { calls } = mockApi();
    renderApp({ route: "/audyt" });
    expect(await screen.findByText("Dziennik audytu jest dostępny dla kierownika")).toBeInTheDocument();
    await act(async () => {});
    expect(calls.some((c) => c.path.startsWith("/api/audit"))).toBe(false);
  });
});

const ENTRIES: AuditEntry[] = [
  {
    id: 3, at: "2026-11-21T10:05:00Z", actor_email: supervisorUser.email, actor_role: "SUPERVISOR", action: "transition",
    incident_id: orangeCase.id, previous: { status: "escalation_requested" }, new: { status: "escalated" }, reason: null,
  },
  {
    id: 2, at: "2026-11-21T10:00:00Z", actor_email: analystUser.email, actor_role: "ANALYST", action: "transition",
    incident_id: orangeCase.id, previous: { status: "in_review", escalation_path: null },
    new: { status: "escalation_requested", escalation_path: "THIRD_PARTY_AUDIT" }, reason: "Brak oznaczenia współpracy",
  },
  {
    id: 1, at: "2026-11-21T09:00:00Z", actor_email: analystUser.email, actor_role: "ANALYST", action: "login",
    incident_id: null, previous: null, new: { method: "demo" }, reason: null,
  },
];

describe("audit log page", () => {
  it("lists entries with previous → new values and filters by case and actor on the server", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi((call) => {
      if (!call.path.startsWith("/api/audit")) return undefined;
      const q = new URLSearchParams(call.path.split("?")[1]);
      const items = ENTRIES.filter((e) => (!q.get("actor") || e.actor_email === q.get("actor")) && (!q.get("incident_id") || e.incident_id === q.get("incident_id")));
      return { json: { items } };
    }, { user: supervisorUser });
    renderApp({ route: "/audyt" });
    expect(await screen.findByRole("heading", { level: 1, name: "Dziennik audytu" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByTestId("audit-row")).toHaveLength(3));
    const first = within(screen.getAllByTestId("audit-row")[1] as HTMLElement);
    expect(first.getByText("Zmiana etapu")).toBeInTheDocument();
    expect(first.getByText(/Etap: W weryfikacji →/)).toHaveTextContent("Etap: W weryfikacji → Wniosek o eskalację");
    expect(first.getByText("Brak oznaczenia współpracy")).toBeInTheDocument();
    expect(first.getByRole("link", { name: orangeCase.title })).toHaveAttribute("href", `/sprawy/${orangeCase.id}#historia`);

    await user.selectOptions(screen.getByLabelText("Użytkownik"), analystUser.email);
    await waitFor(() => expect(screen.getAllByTestId("audit-row")).toHaveLength(2));
    expect(calls.some((c) => c.path.includes(`actor=${encodeURIComponent(analystUser.email)}`))).toBe(true);
    await user.selectOptions(screen.getByLabelText("Sprawa"), orangeCase.id);
    await waitFor(() => expect(screen.getAllByTestId("audit-row")).toHaveLength(1));
    expect(calls.some((c) => c.path.includes(`incident_id=${orangeCase.id}`))).toBe(true);
  });
});
