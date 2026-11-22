// Dev-only mock of the backend contract (coord/contracts/api.md v3): REST + Socket.IO, login, workflow, audit.
// Usage: npm run mock   (listens on MOCK_PORT, default 8000; point VITE_BACKEND_URL at it)
import { createServer } from "node:http";
import { randomBytes, randomUUID } from "node:crypto";
import { deflateSync, crc32 } from "node:zlib";
import { Server } from "socket.io";
import {
  analystUser, globalThresholds, incidentSummaries, incidentsById, minimalIncident, redCase, supervisorUser, toSummary,
} from "./fixtures/data.mjs";

const PORT = Number(process.env.MOCK_PORT) || 8000;
const STEP_MS = Number(process.env.MOCK_STEP_MS) || 1200;

/** @type {Map<string, any>} */
const summaries = new Map(incidentSummaries.map((s) => [s.id, { ...s }]));
const details = new Map(Object.entries(incidentsById).filter(([id]) => id !== redCase.id).map(([id, v]) => [id, structuredClone(v)]));
const jobs = [];

// ── Contract v3: sessions (cookie iw_session), audit log, global thresholds
const DEMO_PASSWORD = process.env.MOCK_PASSWORD || "haslo-demo";
const sessions = new Map();
const audit = [];
let thresholds = { ...globalThresholds };
let auditId = 1;
let notificationId = 1;
const notifications = [];
const bounds = { earliest: new Date(Math.min(...[...summaries.values()].map((s) => Date.parse(s.created_at)))).toISOString(), latest: new Date().toISOString(), timezone: "Europe/Warsaw" };

function userOf(req) {
  const cookie = String(req.headers.cookie ?? "").split(";").map((c) => c.trim()).find((c) => c.startsWith("iw_session="));
  return cookie ? sessions.get(cookie.slice("iw_session=".length)) ?? null : null;
}
function startSession(res, user) {
  const token = randomBytes(24).toString("hex");
  sessions.set(token, user);
  res.setHeader("Set-Cookie", `iw_session=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800`);
  record(user, "login", null, null, { method: "demo" });
}
function record(user, action, incidentId, previous, next, reason = null) {
  audit.unshift({ id: auditId++, at: new Date().toISOString(), actor_email: user.email, actor_role: user.role, action, incident_id: incidentId, previous, new: next, reason });
}

const TRANSITIONS = {
  new: ["in_review"], in_review: ["escalation_requested", "resolved", "false_positive"],
  escalation_requested: ["escalated", "in_review"], escalated: ["resolved", "false_positive"], resolved: [], false_positive: [],
};
const DEFAULT_PATH = { 1: "THIRD_PARTY_AUDIT", 2: "SUPERVISION_RISK_DEPT", 3: "LEGAL_WARNING_LIST" };

/** Same rules as the backend: 409 edge, 403 role, 422 reason. Returns [status, body]. */
function transition(user, inc, body) {
  if (!body || !(body.to in TRANSITIONS)) return [422, { detail: "to: invalid status" }];
  const from = inc.status;
  if (!TRANSITIONS[from].includes(body.to)) return [409, { detail: `transition ${from} -> ${body.to} is not allowed` }];
  if (from === "escalation_requested" && body.to === "escalated" && user.role !== "SUPERVISOR") return [403, { detail: "only a supervisor can approve an escalation" }];
  const reason = typeof body.reason === "string" && body.reason.trim() ? body.reason.trim() : null;
  if (["resolved", "false_positive"].includes(body.to) && !reason) return [422, { detail: "a reason is required" }];
  const wf = { ...inc.workflow };
  const before = { status: from, ...inc.workflow };
  if (body.to === "in_review" && from === "new" && !wf.assigned_to) wf.assigned_to = user.email;
  if (body.to === "in_review" && from === "escalation_requested") wf.escalation_path = null;
  if (body.to === "escalation_requested") wf.escalation_path = body.escalation_path ?? DEFAULT_PATH[inc.primary_module];
  if (body.to === "escalated" && body.escalation_path) wf.escalation_path = body.escalation_path;
  if (body.to === "false_positive") Object.assign(wf, { resolution_action: "false_positive", resolution_note: reason, label: "false_positive" });
  if (body.to === "resolved") Object.assign(wf, { resolution_action: body.resolution_action ?? "evidence_report", resolution_note: reason });
  const updated = { ...inc, status: body.to, workflow: wf, updated_at: new Date().toISOString() };
  const after = { status: body.to, ...wf };
  const keys = Object.keys(after).filter((k) => k === "status" || before[k] !== after[k]);
  record(user, "transition", inc.id, Object.fromEntries(keys.map((k) => [k, before[k]])), Object.fromEntries(keys.map((k) => [k, after[k]])), reason);
  return [200, updated];
}

const send = (res, status, body, type = "application/json; charset=utf-8") => {
  const payload = typeof body === "string" || Buffer.isBuffer(body) ? body : JSON.stringify(body);
  res.writeHead(status, { "Content-Type": type, "Cache-Control": "no-store" });
  res.end(payload);
};
const notFound = (res) => send(res, 404, { detail: "Nie znaleziono zasobu." });

const readJson = (req) =>
  new Promise((resolve) => {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        resolve(null);
      }
    });
  });

function detailOf(id) {
  if (details.has(id)) return details.get(id);
  const s = summaries.get(id);
  return s ? minimalIncident(s) : null;
}

function store(io, incident) {
  details.set(incident.id, incident);
  const s = toSummary(incident);
  summaries.set(s.id, s);
  io.emit("incident:updated", s);
  return incident;
}

// A tiny PNG "screenshot" (page mock-up) so the evidence drawer has a real image to show.
function png(width, height, paint) {
  const raw = Buffer.alloc((width * 3 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    raw[y * (width * 3 + 1)] = 0;
    for (let x = 0; x < width; x += 1) {
      const [r, g, b] = paint(x, y);
      raw.set([r, g, b], y * (width * 3 + 1) + 1 + x * 3);
    }
  }
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(td) >>> 0);
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr.set([8, 2, 0, 0, 0], 8);
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0)),
  ]);
}
const SCREENSHOT = png(640, 400, (x, y) => {
  if (y < 44) return [27, 42, 92];
  if (x > 40 && x < 600 && y > 70 && y < 250) return x > 290 && x < 350 && y > 135 && y < 185 ? [245, 245, 245] : [40, 44, 52];
  if (x > 40 && x < 520 && y > 270 && y < 286) return [60, 66, 78];
  if (x > 40 && x < 600 && y > 300 && (y % 22) < 9 && y < 380) return [208, 212, 220];
  return [255, 255, 255];
});

function emitIncident(io, incident) {
  const s = toSummary(incident);
  summaries.set(s.id, s);
  details.set(s.id, incident);
  io.emit("incident:new", s);
  if (s.risk_score >= 70) io.emit("alert:high", s);
}

function runJob(io, url, makeIncident) {
  const job = { id: randomUUID(), url, state: "queued", incident_id: null, error: null, created_at: new Date().toISOString(), finished_at: null };
  jobs.unshift(job);
  const steps = ["scraping", "analyzing", "done"];
  steps.forEach((state, i) => {
    setTimeout(() => {
      job.state = state;
      if (state === "done") {
        if (url.includes("fail")) {
          job.state = "failed";
          job.error = "Strona nie odpowiada (timeout po 30 s).";
        } else {
          const incident = makeIncident();
          job.incident_id = incident.id;
          emitIncident(io, incident);
        }
        job.finished_at = new Date().toISOString();
      }
      io.emit("scan:progress", { ...job });
    }, STEP_MS * (i + 1));
  });
  setTimeout(() => io.emit("scan:progress", { ...job }), 50);
  return job;
}

function scannedIncident(url, moduleHint) {
  const now = new Date().toISOString();
  const risk = 20 + Math.round(Math.random() * 45);
  const module = moduleHint ?? 2;
  let host = url;
  try {
    host = new URL(url).host;
  } catch {
    // keep the raw string
  }
  return minimalIncident({
    id: randomUUID(), title: `Skan: ${host}`, summary: "Materiał pobrany na żądanie analityka i oceniony przez silnik.",
    modules: [module], primary_module: module, risk_score: risk, compliance_score: 100 - risk,
    risk_level: risk >= 70 ? "red" : risk >= 20 ? "orange" : "green", status: "new", created_at: now, updated_at: now,
    synthetic: false, ground_truth: null, demo_case: null, source: { platform: "web", url }, advertiser: host, firm: null,
    failed_rules: risk >= 20 ? ["4"] : [], workflow: { assigned_to: null, label: "unlabeled" },
  });
}

function filtered(query) {
  let items = [...summaries.values()];
  const m = Number(query.get("module"));
  if (m) items = items.filter((s) => s.modules.includes(m));
  if (query.get("source")) items = items.filter((s) => s.source.platform === query.get("source"));
  if (query.get("status")) items = items.filter((s) => s.status === query.get("status"));
  if (query.get("from")) items = items.filter((s) => s.created_at.slice(0, 10) >= query.get("from"));
  if (query.get("to")) items = items.filter((s) => s.created_at.slice(0, 10) <= query.get("to"));
  const minReports = Number(query.get("min_reports")) || 0;
  if (minReports) items = items.filter((s) => (s.user_reports_count ?? 0) >= minReports);
  const q = (query.get("q") ?? "").toLowerCase();
  if (q) items = items.filter((s) => `${s.title} ${s.summary} ${s.advertiser} ${s.firm}`.toLowerCase().includes(q));
  const key = query.get("sort") === "priority" ? "priority_score" : "risk_score";
  return items.sort((a, b) => b[key] - a[key]);
}

const csvCell = (v) => `"${String(v ?? "").replaceAll('"', '""')}"`;
const PDF = Buffer.from(
  "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n",
);

const server = createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", "http://localhost");
  const path = decodeURIComponent(url.pathname);
  const method = req.method ?? "GET";
  if (process.env.MOCK_DELAY_MS) await new Promise((r) => setTimeout(r, Number(process.env.MOCK_DELAY_MS)));

  if (path === "/api/health") return send(res, 200, { status: "ok", ai: { reachable: true, llm_available: true, model: "gemma-4-e4b-q4" }, queue: true, storage: true });

  const user = userOf(req);
  if (path === "/api/auth/config") return send(res, 200, { demo_login: true, authenticated: user !== null });
  if (path === "/api/auth/me") return user ? send(res, 200, { user }) : send(res, 401, { detail: "authentication required" });
  if (path === "/api/auth/logout" && method === "POST") {
    const cookie = String(req.headers.cookie ?? "").match(/iw_session=([^;]+)/);
    if (cookie) sessions.delete(cookie[1]);
    res.writeHead(204, { "Set-Cookie": "iw_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0" });
    return res.end();
  }
  if (path === "/api/auth/login" && method === "POST") {
    const body = await readJson(req);
    const found = [analystUser, supervisorUser].find((u) => u.email === String(body?.email ?? "").trim().toLowerCase());
    if (!found || body?.password !== DEMO_PASSWORD) return send(res, 401, { detail: "invalid email or password" });
    startSession(res, found);
    return send(res, 200, { user: found });
  }
  if (path === "/api/auth/demo" && method === "POST") {
    const body = await readJson(req);
    const found = body?.role === "SUPERVISOR" ? supervisorUser : body?.role === "ANALYST" ? analystUser : null;
    if (!found) return send(res, 422, { detail: "role: invalid" });
    startSession(res, found);
    return send(res, 200, { user: found });
  }
  if (path.startsWith("/api/public/")) return notFound(res);
  if (path.startsWith("/api/") && !path.startsWith("/api/public/") && !user) return send(res, 401, { detail: "authentication required" });

  if (path === "/api/notifications") return send(res, 200, { items: notifications.filter((item) => item.user_id === user.id) });
  const readNotification = path.match(/^\/api\/notifications\/(\d+)\/read$/);
  if (readNotification && method === "POST") {
    const item = notifications.find((item) => item.id === Number(readNotification[1]) && item.user_id === user.id);
    if (!item) return notFound(res);
    item.read_at = item.read_at || new Date().toISOString();
    return send(res, 200, item);
  }
  if (path === "/api/settings/thresholds") {
    if (method === "PUT") {
      if (user.role !== "SUPERVISOR") return send(res, 403, { detail: "supervisor role required" });
      const body = await readJson(req);
      const flag = Number(body?.flag);
      const critical = Number(body?.critical);
      if (!(flag >= 0 && critical <= 100 && flag <= critical)) return send(res, 422, { detail: "invalid thresholds" });
      record(user, "thresholds", null, { flag: thresholds.flag, critical: thresholds.critical }, { flag, critical });
      if (flag !== thresholds.flag || critical !== thresholds.critical) {
        for (const recipient of [analystUser, supervisorUser]) notifications.unshift({ id: notificationId++, user_id: recipient.id, read_at: null, created_at: new Date().toISOString(), message: `${user.name} zmienił(a) kalibrację: ${thresholds.flag} → ${flag}, krytyczne ${thresholds.critical} → ${critical}.`, details: { actor: user.email, previous: { ...thresholds }, new: { flag, critical } } });
      }
      thresholds = { flag, critical, updated_by: user.email, updated_at: new Date().toISOString() };
    }
    return send(res, 200, thresholds);
  }
  if (path === "/api/audit") {
    if (user.role !== "SUPERVISOR") return send(res, 403, { detail: "supervisor role required" });
    const incidentId = url.searchParams.get("incident_id");
    const actor = url.searchParams.get("actor");
    const items = audit.filter((e) => (!incidentId || e.incident_id === incidentId) && (!actor || e.actor_email === actor));
    return send(res, 200, { items: items.slice(0, Number(url.searchParams.get("limit")) || 200) });
  }
  const wfCall = path.match(/^\/api\/incidents\/([^/]+)\/(transition|assign|label|history|warning-list-request\.pdf)$/);
  if (wfCall) {
    const inc = detailOf(wfCall[1]);
    if (!inc) return notFound(res);
    const action = wfCall[2];
    if (action === "history") return send(res, 200, { items: audit.filter((e) => e.incident_id === inc.id).slice().reverse() });
    if (action === "warning-list-request.pdf") {
      if (!inc.modules.includes(3) && inc.primary_module !== 3) return send(res, 409, { detail: "only for Module 3 cases" });
      record(user, "export", inc.id, null, { format: "pdf", document: "warning_list_request" });
      return send(res, 200, PDF, "application/pdf");
    }
    if (method !== "POST") return notFound(res);
    const body = action === "assign" ? {} : await readJson(req);
    if (action === "assign") {
      if (["resolved", "false_positive"].includes(inc.status)) return send(res, 409, { detail: "closed" });
      record(user, "assign", inc.id, { assigned_to: inc.workflow.assigned_to }, { assigned_to: user.email });
      return send(res, 200, store(io, { ...inc, workflow: { ...inc.workflow, assigned_to: user.email }, updated_at: new Date().toISOString() }));
    }
    if (action === "label") {
      if (!["unlabeled", "true_positive", "false_positive"].includes(body?.label)) return send(res, 422, { detail: "label: invalid" });
      record(user, "label", inc.id, { label: inc.workflow.label }, { label: body.label });
      return send(res, 200, store(io, { ...inc, workflow: { ...inc.workflow, label: body.label } }));
    }
    const [status, out] = transition(user, inc, body);
    return send(res, status, status === 200 ? store(io, out) : out);
  }

  if (path === "/api/incidents" && method === "GET") {
    const items = filtered(url.searchParams);
    return send(res, 200, { items, total: items.length });
  }
  if (path === "/api/incidents/export.csv") {
    const rows = filtered(url.searchParams).map((s) => [s.id, s.title, s.risk_score, s.status, s.source.url].map(csvCell).join(","));
    return send(res, 200, ["id,title,risk_score,status,url", ...rows].join("\n"), "text/csv; charset=utf-8");
  }
  const exp = path.match(/^\/api\/incidents\/([^/]+)\/export\.(pdf|csv)$/);
  if (exp) {
    const inc = detailOf(exp[1]);
    if (!inc) return notFound(res);
    record(user, "export", inc.id, null, { format: exp[2] });
    if (exp[2] === "pdf") return send(res, 200, PDF, "application/pdf");
    const rows = inc.rules.map((r) => ["rule", r.id, r.name, r.status, r.legal_basis].map(csvCell).join(","));
    return send(res, 200, ["type,id,name,status,legal_basis", ...rows].join("\n"), "text/csv; charset=utf-8");
  }
  const one = path.match(/^\/api\/incidents\/([^/]+)$/);
  if (one) {
    const inc = detailOf(one[1]);
    if (!inc) return notFound(res);
    if (method === "GET") return send(res, 200, inc);
    if (method === "PATCH") {
      const body = await readJson(req);
      const [status, out] = transition(user, inc, body ? { ...body, to: body.status, status: undefined } : null);
      return send(res, status, status === 200 ? store(io, out) : out);
    }
  }
  if (path === "/api/stats/trends") {
    const period = url.searchParams.get("period");
    const end = Math.min(Date.now(), Date.parse(url.searchParams.get("to") || new Date().toISOString()));
    const start = Date.parse(url.searchParams.get("from") || new Date(end - (period === "24h" ? 86400000 : (period === "7d" ? 7 : 30) * 86400000)).toISOString());
    const hourly = period === "24h";
    const step = hourly ? 3600000 : 86400000;
    const buckets = new Map();
    for (let at = Math.floor(start / step) * step; at <= end; at += step) buckets.set(hourly ? new Date(at).toISOString() : new Date(at).toISOString().slice(0, 10), []);
    for (const item of summaries.values()) {
      const at = Date.parse(item.created_at);
      if (at < start || at > end) continue;
      const key = hourly ? new Date(Math.floor(at / step) * step).toISOString() : item.created_at.slice(0, 10);
      buckets.get(key)?.push({ id: item.id, risk_score: item.risk_score, module: item.primary_module, modules: item.modules });
    }
    return send(res, 200, { days: [...buckets].map(([date, items]) => ({ date, items })), date_bounds: bounds, interval: hourly ? "hour" : "day" });
  }
  if (path === "/api/calibration") {
    const truth = { true_positive: "violation", false_positive: "ok" };
    const items = [...summaries.values()]
      .filter((s) => s.ground_truth || truth[s.workflow?.label])
      .map((s) => ({
        id: s.id, title: s.title, risk_score: s.risk_score, module: s.primary_module,
        ground_truth: truth[s.workflow?.label] ?? s.ground_truth, label_source: truth[s.workflow?.label] ? "analyst" : "sample",
      }));
    return send(res, 200, { items });
  }
  if (path === "/api/scans" && method === "GET") return send(res, 200, { items: jobs.slice(0, 50) });
  if (path === "/api/scans" && method === "POST") {
    const body = await readJson(req);
    if (!body || typeof body.url !== "string" || !/^https?:\/\//.test(body.url)) return send(res, 422, { detail: "Podaj pełny adres URL zaczynający się od http:// lub https://." });
    const job = runJob(io, body.url, () => scannedIncident(body.url));
    return send(res, 202, { job_id: job.id });
  }
  if (path === "/api/demo/trigger" && method === "POST") {
    const job = runJob(io, redCase.source.url, () => {
      const now = new Date().toISOString();
      return { ...structuredClone(redCase), id: summaries.has(redCase.id) ? randomUUID() : redCase.id, created_at: now, updated_at: now };
    });
    return send(res, 202, { job_id: job.id });
  }
  if (path === "/api/samples/import" && method === "POST") {
    const ids = ["https://probka-1.example/reklama", "https://probka-2.example/oferta"].map((u, i) => runJob(io, u, () => scannedIncident(u, i + 1)).id);
    return send(res, 202, { job_ids: ids });
  }
  if (path === "/api/registries") return send(res, 200, { items: [] });
  if (path.startsWith("/api/evidence/")) {
    const key = path.slice("/api/evidence/".length);
    if (key.endsWith(".png")) return send(res, 200, SCREENSHOT, "image/png");
    if (key.endsWith(".html")) {
      const inc = [...details.values(), redCase].find((d) => d.source.archive.html_key === key);
      const body = inc ? inc.source.text.split("\n").map((l) => `    <p>${l}</p>`).join("\n") : "    <p>…</p>";
      return send(res, 200, `<!doctype html>\n<html lang="pl">\n  <head><title>${inc?.title ?? "Archiwum"}</title></head>\n  <body>\n${body}\n  </body>\n</html>\n`, "text/plain; charset=utf-8");
    }
    return notFound(res);
  }
  return notFound(res);
});

const io = new Server(server, { path: "/socket.io", cors: { origin: true } });
// Same rule as the backend: no session cookie, no live connection.
io.use((socket, next) => (userOf(socket.request) ? next() : next(new Error("authentication required"))));

server.listen(PORT, () => {
  process.stdout.write(`Watchit mock backend: http://localhost:${PORT}\n`);
});
