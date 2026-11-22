import { screen, waitFor, within } from "@testing-library/react";
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
    await user.click(screen.getByRole("button", { name: "Zaloguj jako analityk (konto demonstracyjne)" }));
    expect(await screen.findByRole("heading", { level: 1, name: orangeCase.title })).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/api/auth/demo")?.body).toEqual({ role: "ANALYST" });
    const chip = within(screen.getByTestId("user-chip"));
    expect(chip.getByText(analystUser.name)).toBeInTheDocument();
    expect(chip.getByText("analityk")).toBeInTheDocument();
    await waitFor(() => expect(socket.connected).toBe(true));
    expect(screen.getByRole("link", { name: /Dziennik audytu/ })).toBeInTheDocument(); // WatchIT: an analyst sees their own entries

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
    expect(within(screen.getByTestId("user-chip")).getByText("kierownik")).toBeInTheDocument();
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

  it("an analyst opening /audyt sees only their own entries (the server scopes them)", async () => {
    const { calls } = mockApi((call) => (call.path.startsWith("/api/audit") ? { json: { items: [] } } : undefined));
    renderApp({ route: "/audyt" });
    expect(await screen.findByText(/Twoje wpisy/)).toBeInTheDocument();
    await waitFor(() => expect(calls.some((c) => c.path.startsWith("/api/audit"))).toBe(true));
    expect(calls.find((c) => c.path.startsWith("/api/audit"))?.path).not.toMatch(/actor=/);
    expect(screen.queryByRole("button", { name: /^Kto:/ })).not.toBeInTheDocument(); // no filter by other people
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
    new: { status: "escalation_requested", escalation_path: "THIRD_PARTY_ADVERTISING" }, reason: "Brak oznaczenia współpracy",
  },
  {
    id: 1, at: "2026-11-21T09:00:00Z", actor_email: analystUser.email, actor_role: "ANALYST", action: "login",
    incident_id: null, previous: null, new: { method: "demo" }, reason: null,
  },
];

describe("audit log page", () => {
  it("register: collapsible filters and entry details retain old and new values", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi((call) => {
      if (!call.path.startsWith("/api/audit")) return undefined;
      const q = new URLSearchParams(call.path.split("?")[1]);
      const items = ENTRIES.filter((e) => (!q.get("incident_id") || e.incident_id === q.get("incident_id")) && (!q.get("action") || q.get("action")!.split(",").includes(e.action)));
      return { json: { items } };
    }, { user: supervisorUser });
    renderApp({ route: "/audyt" });
    expect(await screen.findByRole("heading", { level: 1, name: "Dziennik audytu" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByTestId("audit-row")).toHaveLength(3));
    expect(calls.find((c) => c.path.startsWith("/api/audit"))?.path).toMatch(/from=/); // default: the last 24 hours

    const row = screen.getAllByTestId("audit-row")[1] as HTMLElement;
    await user.click(within(row).getByRole("button"));
    const pane = within(await screen.findByTestId("audit-pane"));
    expect(pane.getByRole("heading", { name: "Zmiana etapu" })).toBeInTheDocument();
    const changes = within(pane.getByTestId("audit-changes"));
    expect(changes.getByText("W weryfikacji")).toBeInTheDocument();
    expect(changes.getByText("Wniosek o eskalację")).toBeInTheDocument();
    expect(pane.getByText("Brak oznaczenia współpracy")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("audit-pane")).not.toBeInTheDocument());

    expect(screen.getByTestId("audit-filters")).not.toBeVisible();
    await user.click(screen.getByRole("button", { name: "Rozwiń" }));
    expect(screen.getByTestId("audit-filters")).toBeVisible();
    await user.type(screen.getByLabelText("ID sprawy"), orangeCase.id);
    await waitFor(() => expect(calls.some((c) => c.path.includes(`incident_id=${orangeCase.id}`))).toBe(true));
    await waitFor(() => expect(screen.getAllByTestId("audit-row").length).toBeGreaterThan(0));
    expect(screen.getByText(/1 aktywny/)).toBeInTheDocument();
  });
});
