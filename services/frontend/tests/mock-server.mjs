// Dev-only mock of the backend contract (coord/contracts/api.md v1): REST + Socket.IO.
// Usage: npm run mock   (listens on MOCK_PORT, default 8000; point VITE_BACKEND_URL at it)
import { createServer } from "node:http";
import { randomUUID } from "node:crypto";
import { deflateSync, crc32 } from "node:zlib";
import { Server } from "socket.io";
import {
  incidentSummaries, incidentsById, minimalIncident, redCase, toSummary, trendsFrom,
} from "./fixtures/data.mjs";

const PORT = Number(process.env.MOCK_PORT) || 8000;
const STEP_MS = Number(process.env.MOCK_STEP_MS) || 1200;

/** @type {Map<string, any>} */
const summaries = new Map(incidentSummaries.map((s) => [s.id, { ...s }]));
const details = new Map(Object.entries(incidentsById).filter(([id]) => id !== redCase.id).map(([id, v]) => [id, structuredClone(v)]));
const jobs = [];

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
    failed_rules: risk >= 20 ? ["4"] : [],
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
  const q = (query.get("q") ?? "").toLowerCase();
  if (q) items = items.filter((s) => `${s.title} ${s.summary} ${s.advertiser} ${s.firm}`.toLowerCase().includes(q));
  return items.sort((a, b) => b.risk_score - a.risk_score);
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
      const allowed = ["new", "in_review", "escalated", "closed_violation", "closed_ok"];
      if (!body || !allowed.includes(body.status)) return send(res, 422, { detail: "Nieprawidłowy status." });
      const updated = { ...inc, status: body.status, updated_at: new Date().toISOString() };
      details.set(updated.id, updated);
      const s = { ...summaries.get(updated.id), status: updated.status, updated_at: updated.updated_at };
      summaries.set(updated.id, s);
      io.emit("incident:updated", s);
      return send(res, 200, updated);
    }
  }
  if (path === "/api/stats/trends") {
    return send(res, 200, trendsFrom([...summaries.values()], Number(url.searchParams.get("days")) || 30, Date.now()));
  }
  if (path === "/api/calibration") {
    const items = [...summaries.values()].filter((s) => s.ground_truth).map((s) => ({ id: s.id, title: s.title, risk_score: s.risk_score, ground_truth: s.ground_truth, module: s.primary_module }));
    return send(res, 200, { items });
  }
  if (path === "/api/scans" && method === "GET") return send(res, 200, { items: jobs.slice(0, 50) });
  if (path === "/api/scans" && method === "POST") {
    const body = await readJson(req);
    if (!body || typeof body.url !== "string" || !/^https?:\/\//.test(body.url)) return send(res, 422, { detail: "Podaj pełny adres URL zaczynający się od http:// lub https://." });
    const job = runJob(io, body.url, () => scannedIncident(body.url, body.module_hint));
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

server.listen(PORT, () => {
  process.stdout.write(`InvestWatch mock backend: http://localhost:${PORT}\n`);
});
