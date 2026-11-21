version: 3

# Service boundaries

```
browser ──▶ frontend (nginx, :FRONTEND_PORT) ──/api, /socket.io──▶ backend (:BACKEND_PORT)
backend ──HTTP──▶ ai (:AI_PORT)        backend ──▶ postgres · valkey (queue + socket fan-out) · object storage (S3 API)
```

The browser only ever talks to the frontend origin; nginx proxies `/api/*` and `/socket.io/*` to the backend (no CORS). Services share no code, only these contracts. Types `Incident`, `IncidentSummary`, `Analysis` are in [incident.md](incident.md).

## Backend REST (`/api`)

| Method + path | Request | Response |
|---|---|---|
| `GET /api/health` | | `{status:"ok", ai:{reachable:bool, llm_available:bool, model:string\|null}, queue:bool, storage:bool}` |
| `GET /api/incidents` | query: `module` (1\|2\|3), `source` (platform), `status`, `from`, `to` (ISO date), `q` | `{items: IncidentSummary[], total: number}`, sorted by `risk_score` desc. No level filter server-side: levels depend on the client threshold. |
| `GET /api/incidents/{id}` | | `Incident` · 404 |
| `PATCH /api/incidents/{id}` | `{status: Status}` | `Incident` · 404 · 422 |
| `GET /api/stats/trends` | query `days` (default 30) | `{days: {date: string, items: {id:string, risk_score:number, module:1\|2\|3}[]}[]}` (raw scores so the chart follows the threshold) |
| `GET /api/calibration` | | `{items: {id, title, risk_score, ground_truth: "violation"\|"ok", module}[]}`: only incidents with a label. The client computes TP/FP/FN/TN, precision, recall for any threshold. |
| `POST /api/scans` | `{url: string, module_hint?: 1\|2\|3, render?: boolean}` | `202 {job_id}` · 422 |
| `GET /api/scans` | | `{items: ScanJob[]}` (latest 50) |
| `POST /api/samples/import` | `{path?: string}` (relative to `SAMPLES_DIR`) | `202 {job_ids: string[]}` |
| `POST /api/demo/trigger` | `{case: "case3"}` | `202 {job_id}`: pushes the unseeded demo sample through the real pipeline |
| `GET /api/incidents/{id}/export.pdf` | | `application/pdf` evidence package |
| `GET /api/incidents/{id}/export.csv` | | `text/csv; charset=utf-8` (rules + evidence rows) |
| `GET /api/incidents/export.csv` | same filters as list | `text/csv` |
| `GET /api/evidence/{key}` | key = object-storage key | archived HTML (served as `text/plain`) or PNG |
| `GET /api/registries` | | `{items: {registry, label, url, entries: number, snapshot_date}[]}` |

`ScanJob = {id, url, state: "queued"|"scraping"|"analyzing"|"done"|"failed", incident_id: string|null, error: string|null, created_at, finished_at}`

Errors: JSON `{detail: string}`.

## Socket.IO (path `/socket.io`, default namespace)

| Event (server → client) | Payload | When |
|---|---|---|
| `incident:new` | `IncidentSummary` | every stored incident |
| `incident:updated` | `IncidentSummary` | status change or re-analysis |
| `alert:high` | `IncidentSummary` | new incident with `risk_score >= ALERT_THRESHOLD` (default 70) |
| `scan:progress` | `ScanJob` | each job state change |

Workers emit through the Valkey-backed Socket.IO manager, so any number of workers and API replicas fan out to all clients.

## AI service

| Method + path | Request | Response |
|---|---|---|
| `GET /health` | | `{status:"ok", llm_available: bool, model: string\|null, plugins: string[], registries: {registry, entries, snapshot_date}[]}` |
| `POST /analyze` | `{document: Document, context?: Context}` | `Analysis` |
| `GET /plugins` | | `{items: {id, module, description}[]}` |
| `GET /registries` | | same list as in `/health` with `label`, `url` |
| `PUT /registries/{registry}` | `{snapshot_date: string, entries: {name: string, aliases?: string[], status?: string, detail?: string}[]}` | `{entries: number}`: replaces a register snapshot (backend refresh job) |

```ts
interface Document {              // unified scraper output
  url: string;
  platform: Source["platform"];
  fetched_at: string;
  http_status: number;
  title: string;
  html: string;                   // raw HTML ("" when only text is available)
  text: string;                   // raw visible text (ai service normalizes again)
  language?: string;
  published_at?: string;
  author?: { name: string; handle?: string; url?: string };
  fetch: { engine: "httpx" | "playwright" | "file"; user_agent: string; proxy: string | null };
  archive: { html_key: string | null; screenshot_key: string | null };
}

interface Context {               // enrichment collected by backend connectors or shipped with a sample
  synthetic?: boolean;
  ground_truth?: "violation" | "ok" | null;
  demo_case?: string | null;
  module_hint?: 1 | 2 | 3;
  cooperation_notified?: boolean | null;     // UKNF internal notice of firm ↔ advertiser cooperation
  companies?: { name: string; krs?: string; role: "investment_firm"|"advertiser"|"pr_agency"|"other";
                incorporated_on?: string; share_capital_pln?: number; country?: string;
                statements?: {year:number, revenue_pln:number|null, net_result_pln:number|null, filed:boolean}[] }[];
  graph?: { nodes: GraphNode[]; edges: Omit<GraphEdge,"suspicious">[] };   // raw relations (KRS/CRBR/contracts)
  comments?: { handle: string; account_created: string; country: string; lang: string;
               text: string; posted_at: string; rating?: number }[];
  declared?: { advisor_licence_no?: string; legal_adviser_name?: string; legal_adviser_no?: string; tax_adviser_no?: string };
}
```

## Samples = the "pendrive" format (`samples/`, mounted at `SAMPLES_DIR`)

One sample = `<slug>.json`, optionally next to `<slug>.html`:

```json
{
  "meta": { "url": "https://…", "platform": "youtube", "title": "…", "published_at": "2026-11-01",
            "author": {"name": "…", "handle": "@…"}, "seed": true, "detected_days_ago": 3 },
  "html_file": "<slug>.html",
  "text": "used when there is no html_file",
  "context": { }
}
```

- `meta.seed: false` → skipped by the startup seed (used for the live demo trigger).
- A bare `*.html` or `*.txt` without a `.json` is imported too, with `platform: "sample"`.
- Seeding and import go through the real pipeline: the backend serves the file at `/fixtures/<path>`, the scraper fetches it over HTTP, the AI service scores it. Nothing is inserted pre-scored.

## Additions in version 2 (backend)

| Method + path | Request | Response |
|---|---|---|
| `GET /api/incidents` | also `limit` (default 1000, max 5000), `offset` | `total` is the full count |
| `POST /api/incidents/{id}/rescan` | | `202 {job_id}` · 404. Re-fetches the source; a changed hash adds a version row; emits `incident:updated` |
| `GET /api/incidents/{id}/versions` | | `{items: {content_hash, risk_score, changed: bool, created_at}[]}` newest first, max 20 |
| `GET /api/watchlist` · `POST /api/watchlist` · `DELETE /api/watchlist/{id}` · `POST /api/watchlist/rescan` | `{url, module_hint?, render?}` | `WatchItem = {id, url, module_hint, render, created_at, last_scanned_at}` · `202 {job_ids}` for rescan |
| `GET /api/discovery/sources` · `POST /api/discovery/sources` · `DELETE /api/discovery/sources/{id}` | `{url, module_hint?, keywords?: string[], max_links?: 1..100, render?}` | `Source = {id, url, module_hint, keywords, max_links, render, created_at, last_run_at, last_found, last_error}` |
| `POST /api/discovery/run` | | `202 {status: "queued"}`: fetch each source, filter links by keyword, scan the unseen ones |
| `POST /api/registries/refresh` | | `202 {status: "queued"}` |
| `GET /fixtures/{path}` | | sample files, read-only |

Discovery is the "wyszukiwanie" step of every module: seed pages (search results, ad libraries, listings) → candidate links → scans. Offline, `samples/discovery/index.html` is registered as a source at seed time.

The dedup key is the source URL: the same URL updates the incident in place. The demo trigger deletes the previous incident of that demo case; clients refetch the list on `incident:new`.

## Version 3 additions

### Rendered visual audit (backend scraper → AI)
For pages with HTML the scraper renders them in Chromium at three viewports (desktop 1920×1080, tablet 768×1024, mobile 390×844), stores one full-page screenshot per viewport, and attaches measurements to the document:

```ts
interface Document {
  final_url?: string; redirect_chain?: string[]; affiliate_params?: string[];   // e.g. ["ref=jan20", "utm_source=yt"]
  archive: { html_key; screenshot_key; screenshots?: {desktop?, tablet?, mobile?} };
  visual?: {
    dominant_font_px: number;                         // most common font size by text length (desktop)
    viewports: { name: "desktop"|"tablet"|"mobile"; width: number; height: number; page_height: number;
                 screenshot_key: string | null; overflow_x: boolean; clipped_texts: string[]; min_risk_font_px: number | null }[];
    risk_elements: {                                  // elements whose text is a risk warning (matched by the scraper with a keyword list; the AI decides relevance)
      text: string; font_px: number; ratio_to_dominant: number;
      color: string; background: string; contrast: number;        // WCAG contrast ratio
      opacity: number; visible: boolean; occluded: boolean;       // elementFromPoint check
      placement: "body" | "footer" | "footnote" | "legal_section";
      requires_interaction: "details" | "accordion" | "tooltip" | "modal" | "link" | null;
      bbox: BBox | null;                                          // per viewport list allowed: bboxes?: BBox[]
    }[];
    performance_blocks: { text: string; font_px: number; area_share: number; bbox: BBox | null }[];   // past-performance claims and their share of the first viewport
  };
}
```
The AI service uses `visual` for rules 4, 5, 6, 7, 8 and 13 (`method: "rendered"`), puts `bbox` on the evidence, and falls back to static HTML analysis when `visual` is absent.

### Authentication (local only)
JWT HS256 (`JWT_SECRET` from env) in an HttpOnly, SameSite=Strict cookie `iw_session`; passwords hashed with argon2. Everything under `/api` requires a session except `/api/health`, `/api/auth/*`, `/api/public/*`; `/fixtures/*` stays open (scraper). Socket.IO connections require the same cookie.

| Method + path | Request | Response |
|---|---|---|
| `POST /api/auth/login` | `{email, password}` | `{user: User}` + cookie · 401 |
| `POST /api/auth/demo` | `{role: Role}` | `{user}` + cookie; only when `DEMO_LOGIN=true` · 404 otherwise |
| `GET /api/auth/config` | | `{demo_login: boolean}` |
| `GET /api/auth/me` | | `{user: User}` · 401 |
| `POST /api/auth/logout` | | 204 |

`User = {id, email, name, role: Role}`. Two demo accounts are seeded at start (passwords from env).

### Workflow, settings, audit
| Method + path | Request | Response |
|---|---|---|
| `POST /api/incidents/{id}/assign` | | `Incident` (assigns the caller) |
| `POST /api/incidents/{id}/transition` | `{to: Status, reason?: string, escalation_path?: EscalationPath, resolution_action?: ResolutionAction}` | `Incident` · 409 invalid transition · 403 role · 422 missing reason |
| `POST /api/incidents/{id}/label` | `{label: "true_positive"\|"false_positive"\|"unlabeled"}` | `Incident` |
| `PATCH /api/incidents/{id}` | `{status}` | kept as an alias of transition |
| `GET /api/incidents/{id}/history` | | `{items: AuditEntry[]}` for that case |
| `GET /api/incidents/{id}/warning-list-request.pdf` | | PDF draft of a request to add the entity to the public warnings list (Module 3) |
| `GET /api/settings/thresholds` | | `{flag: number, critical: number, updated_by, updated_at}` (global defaults; clients may preview other values locally) |
| `PUT /api/settings/thresholds` | `{flag, critical}` | same · 403 unless SUPERVISOR; also sets the server `alert:high` threshold to `critical` |
| `GET /api/audit` | `incident_id?`, `actor?`, `limit?` | `{items: AuditEntry[]}` · 403 unless SUPERVISOR |

`AuditEntry = {id, at, actor_email, actor_role, action, incident_id: string|null, previous: unknown, new: unknown, reason: string|null}`; actions: `login`, `assign`, `transition`, `label`, `thresholds`, `export`, `rescan`.
`resolution_action: "enhanced_monitoring"` adds the URL to the watchlist with a 6-hour interval.
`GET /api/calibration` items gain `label_source: "sample" | "analyst"`: seeded ground truth plus cases labelled by analysts.

### Public reports
| Method + path | Request | Response |
|---|---|---|
| `POST /api/public/reports` | `{url: string, category_hint?: 1\|2\|3\|null, comment?: string (≤ 500)}` | `202 {status: "accepted", known: boolean}` · 422 · 429 |

No login. The URL is normalised (tracking parameters such as `fbclid`, `gclid`, `utm_*` removed; fragment dropped) and hashed; a known URL increments `user_reports_count` and recomputes `priority_score`; a new one is queued through the normal scraper with `platform` detected as usual and `source: "user_report"` recorded on the report. Limits: one report per IP and URL per 24 h, `PUBLIC_REPORTS_PER_HOUR` per IP (default 20), a cap on queued report scans; SSRF guard applies. No browser fingerprinting.
Events: `incident:updated` on every count change; `alert:viral` (`IncidentSummary`) when a case with `risk_score >= critical` threshold reaches 5 reports.
