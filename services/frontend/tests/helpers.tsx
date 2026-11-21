import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import type { LiveSocket } from "../src/api/socket";
import { AppProviders, AppRoutes } from "../src/App";
import type { Thresholds } from "../src/domain/levels";
import { calibrationSet, incidentsById, incidentSummaries, minimalIncident, trends } from "./fixtures/data.mjs";

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

/** Replaces global fetch with the contract's happy path served from fixtures; `override` wins when it returns a value. */
export function mockApi(override?: Route) {
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
    if (path === "/api/incidents") return json({ items: incidentSummaries, total: incidentSummaries.length });
    if (path === "/api/stats/trends") return json(trends);
    if (path === "/api/calibration") return json(calibrationSet);
    if (path === "/api/scans" && call.method === "GET") return json({ items: [] });
    if (path === "/api/scans") return json({ job_id: "job-1" }, 202);
    if (path === "/api/demo/trigger") return json({ job_id: "job-demo" }, 202);
    if (path === "/api/samples/import") return json({ job_ids: ["job-a", "job-b"] }, 202);
    if (path.startsWith("/api/evidence/")) return new Response("<html>archiwum</html>", { status: 200 });
    const one = path.match(/^\/api\/incidents\/([^/]+)$/);
    if (one?.[1]) {
      const id = one[1];
      const summary = incidentSummaries.find((s) => s.id === id);
      const incident = incidentsById[id] ?? (summary ? minimalIncident(summary) : null);
      if (!incident) return json({ detail: "Nie znaleziono zasobu." }, 404);
      if (call.method === "PATCH") return json({ ...incident, status: (call.body as { status: string }).status });
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
