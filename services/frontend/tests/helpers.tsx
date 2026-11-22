import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import type { LiveSocket } from "../src/api/socket";
import { AppProviders, AppRoutes } from "../src/App";
import type { Thresholds } from "../src/domain/levels";
import type { User } from "../src/types/api";
import {
  analystUser, calibrationSet, globalThresholds, incidentsById, incidentSummaries, minimalIncident, reportsForCase, supervisorUser, trends,
} from "./fixtures/data.mjs";

type Handler = (payload: never) => void;

/** In-memory stand-in for the Socket.IO client: tests push server events with `emit`. */
export class FakeSocket implements LiveSocket {
  connected = false;
  private handlers = new Map<string, Set<Handler>>();
  on(event: string, handler: Handler) {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)?.add(handler);
    return this;
  }
  off(event: string, handler: Handler) {
    this.handlers.get(event)?.delete(handler);
    return this;
  }
  connect() {
    this.connected = true;
    this.emit("connect", undefined);
    return this;
  }
  disconnect() {
    this.connected = false;
    return this;
  }
  emit(event: string, payload: unknown) {
    this.handlers.get(event)?.forEach((h) => h(payload as never));
  }
}

export interface FetchCall {
  method: string;
  path: string;
  body: unknown;
}

type Route = (call: FetchCall) => { status?: number; json?: unknown; text?: string } | undefined;

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

export interface MockOptions {
  /** The logged-in user; null = no session (the app shows the login page). Default: the demo analyst. */
  user?: User | null;
  demoLogin?: boolean;
}

/** Replaces global fetch with the contract's happy path served from fixtures; `override` wins when it returns a value. */
export function mockApi(override?: Route, { user = analystUser, demoLogin = true }: MockOptions = {}) {
  let session: User | null = user;
  const calls: FetchCall[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === "string" ? input : input.toString(), "http://localhost");
    const call: FetchCall = {
      method: init?.method ?? "GET",
      path: url.pathname + url.search,
      body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
    };
    calls.push(call);
    const custom = override?.(call);
    if (custom) return custom.text !== undefined ? new Response(custom.text, { status: custom.status ?? 200 }) : json(custom.json, custom.status ?? 200);

    const path = url.pathname;
    if (path === "/api/auth/config") return json({ demo_login: demoLogin, authenticated: session !== null });
    if (path === "/api/auth/me") return session ? json({ user: session }) : json({ detail: "authentication required" }, 401);
    if (path === "/api/auth/logout") {
      session = null;
      return new Response(null, { status: 204 });
    }
    if (path === "/api/auth/login") {
      const body = call.body as { email: string; password: string };
      const found = [analystUser, supervisorUser].find((u) => u.email === body.email && body.password === "haslo-demo");
      if (!found) return json({ detail: "invalid email or password" }, 401);
      session = found;
      return json({ user: found });
    }
    if (path === "/api/auth/demo") {
      if (!demoLogin) return json({ detail: "Not Found" }, 404);
      session = (call.body as { role: string }).role === "SUPERVISOR" ? supervisorUser : analystUser;
      return json({ user: session });
    }
    if (path === "/api/public/reports") return json({ status: "accepted", known: false }, 202);
    if (path.startsWith("/api/") && !session) return json({ detail: "authentication required" }, 401);
    if (path === "/api/settings/thresholds" && call.method === "PUT") {
      if (session?.role !== "SUPERVISOR") return json({ detail: "supervisor role required" }, 403);
      const body = call.body as { flag: number; critical: number };
      return json({ ...body, updated_by: session.email, updated_at: "2026-11-21T10:00:00Z" });
    }
    if (path === "/api/settings/thresholds") return json(globalThresholds);
    if (path === "/api/audit") return session?.role === "SUPERVISOR" ? json({ items: [] }) : json({ detail: "supervisor role required" }, 403);
    if (/^\/api\/incidents\/[^/]+\/history$/.test(path)) return json({ items: [] });
    if (/^\/api\/incidents\/[^/]+\/versions$/.test(path)) return json({ items: [] });
    if (path === "/api/settings/thresholds/history") return json({ items: [] });
    if (path === "/api/settings/thresholds/preview") return json(null, 204);
    if (/^\/api\/incidents\/[^/]+\/rescan$/.test(path)) return json({ job_id: "job-rescan" }, 202);
    const reportsOf = path.match(/^\/api\/incidents\/([^/]+)\/reports$/);
    if (reportsOf?.[1]) {
      const found = incidentsById[reportsOf[1]] ?? incidentSummaries.find((s) => s.id === reportsOf[1]);
      return found ? json({ items: reportsForCase(found) }) : json({ detail: "Nie znaleziono zasobu." }, 404);
    }
    if (path === "/api/incidents") return json({ items: incidentSummaries, total: incidentSummaries.length });
    if (path === "/api/stats/trends") return json(trends);
    if (path === "/api/calibration") return json(calibrationSet);
    if (path === "/api/scans" && call.method === "GET") return json({ items: [] });
    if (path === "/api/scans") return json({ job_id: "job-1" }, 202);
    if (path === "/api/demo/trigger") return json({ job_id: "job-demo" }, 202);
    if (path === "/api/samples/import") return json({ job_ids: ["job-a", "job-b"] }, 202);
    if (path.startsWith("/api/evidence/")) return new Response("<html>archiwum</html>", { status: 200 });
    const one = path.match(/^\/api\/incidents\/([^/]+)(\/(transition|assign|label))?$/);
    if (one?.[1]) {
      const id = one[1];
      const summary = incidentSummaries.find((s) => s.id === id);
      const incident = incidentsById[id] ?? (summary ? minimalIncident(summary) : null);
      if (!incident) return json({ detail: "Nie znaleziono zasobu." }, 404);
      const me = session?.email ?? null;
      if (one[3] === "assign") return json({ ...incident, workflow: { ...incident.workflow, assigned_to: me } });
      if (one[3] === "label") return json({ ...incident, workflow: { ...incident.workflow, label: (call.body as { label: string }).label } });
      if (one[3] === "transition") {
        const body = call.body as { to: string; reason?: string; escalation_path?: string; resolution_action?: string };
        return json({
          ...incident,
          status: body.to,
          workflow: {
            ...incident.workflow,
            escalation_path: body.escalation_path ?? incident.workflow.escalation_path,
            resolution_action: body.resolution_action ?? (body.to === "false_positive" ? "false_positive" : incident.workflow.resolution_action),
            resolution_note: body.reason ?? incident.workflow.resolution_note,
          },
        });
      }
      return json(incident);
    }
    return json({ detail: "Nie znaleziono zasobu." }, 404);
  });
  vi.stubGlobal("fetch", fn);
  return { calls, fn };
}

interface RenderOptions {
  route?: string;
  thresholds?: Thresholds;
  socket?: FakeSocket;
}

/** Renders the real routed app with providers, a fake socket and an in-memory router. */
export function renderApp({ route = "/", thresholds, socket = new FakeSocket() }: RenderOptions = {}) {
  const factory = () => socket;
  const view = render(
    <MemoryRouter initialEntries={[route]}>
      <AppProviders socketFactory={factory} initialThresholds={thresholds}>
        <AppRoutes />
      </AppProviders>
    </MemoryRouter>,
  );
  return { ...view, socket };
}

export function renderWithRouter(ui: ReactNode, route = "/") {
  return render(<MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>);
}
