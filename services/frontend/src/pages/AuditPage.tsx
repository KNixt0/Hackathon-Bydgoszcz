import { ArrowDown, ArrowUp, ArrowUpDown, ChevronDown, Download, Filter, X } from "lucide-react";
import { useCallback, useEffect, useId, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import { caseRef } from "../components/queue/QueueTable";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { describeChange } from "../domain/audit";
import { apiDate, clampDateTime, SYSTEM_START_LOCAL, todayIso, warsawInput } from "../domain/dates";
import { formatDateTime } from "../domain/format";
import { AUDIT_ACTION_LABEL, ROLE_LABEL } from "../domain/labels";
import { useUser } from "../hooks/useAuth";
import { useResource } from "../hooks/useResource";
import type { AuditAction, AuditEntry } from "../types/api";
import type { Role } from "../types/incident";

const LIMIT = 1000;
const ACTIONS: AuditAction[] = ["login", "assign", "transition", "label", "thresholds", "calibration_preview", "export", "rescan"];
type Range = "24h" | "7d" | "30d" | "all" | "custom";
const RANGE_LABEL: Record<Range, string> = { "24h": "ostatnie 24 godz.", "7d": "ostatnie 7 dni", "30d": "ostatnie 30 dni", all: "od uruchomienia systemu", custom: "własny zakres" };
type SortKey = "at" | "actor" | "action" | "object";

interface Filters {
  range: Range;
  from: string;
  to: string;
  actions: AuditAction[];
  role: Role | "";
  actor: string;
  caseId: string;
  q: string;
}

function readFilters(p: URLSearchParams): Filters {
  const range = (["24h", "7d", "30d", "all", "custom"] as Range[]).find((r) => r === p.get("zakres")) ?? "24h";
  const role = p.get("rola");
  return {
    range,
    from: clampDateTime(p.get("od") ?? ""),
    to: clampDateTime(p.get("do") ?? ""),
    actions: (p.get("dzialanie") ?? "").split(",").filter((a): a is AuditAction => (ACTIONS as string[]).includes(a)),
    role: role === "ANALYST" || role === "SUPERVISOR" ? role : "",
    actor: p.get("kto") ?? "",
    caseId: p.get("sprawa") ?? "",
    q: p.get("szukaj") ?? "",
  };
}

function writeFilters(f: Filters): URLSearchParams {
  const p = new URLSearchParams();
  if (f.range !== "24h") p.set("zakres", f.range);
  if (f.range === "custom" && f.from) p.set("od", f.from);
  if (f.range === "custom" && f.to) p.set("do", f.to);
  if (f.actions.length) p.set("dzialanie", f.actions.join(","));
  if (f.role) p.set("rola", f.role);
  if (f.actor) p.set("kto", f.actor);
  if (f.caseId) p.set("sprawa", f.caseId);
  if (f.q) p.set("szukaj", f.q);
  return p;
}

/** The server-side window for the chosen range (the system start is the floor). */
function rangeWindow(f: Filters): { from?: string; to?: string } {
  const now = Date.now();
  if (f.range === "24h") return { from: new Date(now - 864e5).toISOString() };
  if (f.range === "7d") return { from: new Date(now - 7 * 864e5).toISOString().slice(0, 10) };
  if (f.range === "30d") return { from: new Date(now - 30 * 864e5).toISOString().slice(0, 10) };
  if (f.range === "custom") return { from: f.from ? apiDate(f.from) : undefined, to: f.to ? apiDate(f.to) : undefined };
  return {};
}

const objectLabel = (e: AuditEntry) =>
  e.incident_id ? `Sprawa ${caseRef(e.incident_id)}` : e.action === "thresholds" || e.action === "calibration_preview" ? "Kalibracja" : "—";

function csvOf(entries: AuditEntry[]): string {
  const cell = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const rows = entries.map((e) => [
    formatDateTime(e.at), e.actor_email, ROLE_LABEL[e.actor_role] ?? e.actor_role, AUDIT_ACTION_LABEL[e.action] ?? e.action,
    objectLabel(e), describeChange(e).map((c) => `${c.label}: ${c.before ?? "—"} -> ${c.after}`).join("; "), e.reason ?? "",
  ].map(cell).join(";"));
  return ["Data i godzina;Kto;Rola;Działanie;Obiekt;Zmiany;Uzasadnienie", ...rows].join("\r\n");
}

/** Ruled audit register; the server enforces each user’s visibility. */
export function AuditPage() {
  const user = useUser();
  const supervisor = user.role === "SUPERVISOR";
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => readFilters(params), [params]);
  const setFilters = useCallback(
    (patch: Partial<Filters>) => setParams((prev) => {
      const next = writeFilters({ ...readFilters(prev), ...patch });
      const entry = prev.get("wpis");
      if (entry) next.set("wpis", entry);
      return next;
    }, { replace: true }),
    [setParams],
  );
  const [open, setOpen] = useState(false);
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "at", dir: "desc" });

  const win = rangeWindow(filters);
  const key = JSON.stringify([filters, win.from?.slice(0, 13)]);
  const log = useResource(
    (signal) => api.audit({
      incident_id: filters.caseId.trim() || undefined,
      actor: supervisor ? filters.actor || undefined : undefined,
      action: filters.actions.join(",") || undefined,
      role: supervisor ? filters.role || undefined : undefined,
      from: win.from,
      to: win.to,
      q: filters.q.trim() || undefined,
      limit: LIMIT,
    }, signal),
    `audit:${key}`,
  );
  const entries = useMemo(() => (log.resource.phase === "ready" ? log.resource.data.items ?? [] : []), [log.resource]);
  const sorted = useMemo(() => {
    const value = (e: AuditEntry) =>
      sort.key === "at" ? e.at : sort.key === "actor" ? e.actor_email : sort.key === "action" ? (AUDIT_ACTION_LABEL[e.action] ?? e.action) : objectLabel(e);
    const sign = sort.dir === "asc" ? 1 : -1;
    return [...entries].sort((a, b) => value(a).localeCompare(value(b), "pl") * sign || (Number(b.id) - Number(a.id)));
  }, [entries, sort]);
  const actors = useMemo(() => [...new Set([...entries.map((e) => e.actor_email), ...(filters.actor ? [filters.actor] : [])])].sort(), [entries, filters.actor]);

  const selectedId = params.get("wpis");
  const index = sorted.findIndex((e) => String(e.id) === selectedId);
  const selected = index >= 0 ? sorted[index] : null;
  const select = useCallback(
    (id: string | null) => setParams((prev) => { const p = new URLSearchParams(prev); if (id) p.set("wpis", id); else p.delete("wpis"); return p; }, { replace: true }),
    [setParams],
  );

  // Esc closes the pane; arrow keys move to the neighbouring entry (not while typing in a field).
  useEffect(() => {
    if (!selected) return;
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && /^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName);
      if (e.key === "Escape") select(null);
      else if (!typing && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
        const next = sorted[index + (e.key === "ArrowDown" ? 1 : -1)];
        if (next) {
          e.preventDefault();
          select(String(next.id));
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [selected, sorted, index, select]);

  const active = [filters.range !== "24h", filters.actions.length > 0, Boolean(filters.role), Boolean(filters.actor), Boolean(filters.caseId), Boolean(filters.q)].filter(Boolean).length;
  const exportCsv = () => {
    const blob = new Blob(["﻿", csvOf(sorted)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dziennik-audytu-${todayIso()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const bodyId = useId();
  const today = warsawInput(new Date());
  const sortBy = (k: SortKey) => setSort((s) => ({ key: k, dir: s.key === k && s.dir === "desc" ? "asc" : "desc" }));

  return (
    <div className="page">
      <div className="page__head">
        <h1 className="page__title">Dziennik audytu</h1>
        <p className="page__sub">
          {supervisor
            ? "Każde logowanie, decyzja w sprawie, zmiana progów, eksport i sprawdzenie źródła: kto, kiedy, co zmienił i dlaczego. Wpisów nie można zmienić ani usunąć."
            : "Twoje wpisy: logowania, decyzje w sprawach, zmiany progów, eksporty i sprawdzenia źródła. Pełny dziennik widzi kierownik. Wpisów nie można zmienić ani usunąć."}
        </p>
      </div>

      <section className="fbar" aria-label="Filtry dziennika">
        <div className="fbar__head">
          <span className="fbar__title"><Filter aria-hidden="true" />Filtry{active > 0 && <span className="muted"> ({active} {active === 1 ? "aktywny" : "aktywne"})</span>}</span>
          <button type="button" className="linkbtn" aria-expanded={open} aria-controls={bodyId} onClick={() => setOpen((v) => !v)}>
            {open ? "Zwiń" : "Rozwiń"}<ChevronDown aria-hidden="true" className={open ? "chev chev--up" : "chev"} />
          </button>
        </div>
        <div className="fbar__body" id={bodyId} hidden={!open} data-testid="audit-filters">
          <label className="field"><span className="field__label">Zakres dat</span>
            <select className="select" value={filters.range} onChange={(e) => setFilters({ range: e.target.value as Range })}>
              {(Object.keys(RANGE_LABEL) as Range[]).map((r) => <option key={r} value={r}>{RANGE_LABEL[r]}</option>)}
            </select>
          </label>
          {filters.range === "custom" && <>
            <label className="field"><span className="field__label">Od (czas polski)</span><input className="input" type="datetime-local" min={SYSTEM_START_LOCAL} max={filters.to || today} value={filters.from} onChange={(e) => setFilters({ from: clampDateTime(e.target.value, filters.to || today) })} /></label>
            <label className="field"><span className="field__label">Do (czas polski)</span><input className="input" type="datetime-local" min={filters.from || SYSTEM_START_LOCAL} max={today} value={filters.to} onChange={(e) => { const to = clampDateTime(e.target.value, today); setFilters({ to: to && filters.from && to < filters.from ? filters.from : to }); }} /></label>
          </>}
          <fieldset className="audit-actions"><legend>Działanie</legend>
            {ACTIONS.map((a) => <label key={a}><input type="checkbox" checked={filters.actions.includes(a)} onChange={(e) => setFilters({ actions: e.target.checked ? [...filters.actions, a] : filters.actions.filter((x) => x !== a) })} /> {AUDIT_ACTION_LABEL[a] ?? a}</label>)}
          </fieldset>
          {supervisor && <>
            <label className="field"><span className="field__label">Rola</span><select className="select" value={filters.role} onChange={(e) => setFilters({ role: e.target.value as Role | "" })}><option value="">Wszystkie</option>{(["ANALYST", "SUPERVISOR"] as const).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</select></label>
            <label className="field"><span className="field__label">Kto</span><select className="select" value={filters.actor} onChange={(e) => setFilters({ actor: e.target.value })}><option value="">Wszyscy</option>{actors.map((a) => <option key={a} value={a}>{a}</option>)}</select></label>
          </>}
          <label className="field fbar__case">
            <span className="field__label">ID sprawy</span>
            <input className="input" value={filters.caseId} placeholder="np. 429655D5" onChange={(e) => setFilters({ caseId: e.target.value })} />
          </label>
          <label className="field fbar__search">
            <span className="field__label">Szukaj w uzasadnieniach</span>
            <input className="input" type="search" value={filters.q} onChange={(e) => setFilters({ q: e.target.value })} />
          </label>
          {active > 0 && <button type="button" className="linkbtn" onClick={() => setParams(new URLSearchParams(), { replace: true })}>Wyczyść</button>}
        </div>
      </section>

      <p className="audit__meta">
        <span role="status">
          {log.resource.phase === "ready" ? `Pokazano ${sorted.length} ${sorted.length === 1 ? "wpis" : "wpisów"}${sorted.length === LIMIT ? " (limit)" : ""}, ${RANGE_LABEL[filters.range]}` : "Wczytywanie wpisów…"}
        </span>
        <button type="button" className="dl linkbtn" onClick={exportCsv} disabled={sorted.length === 0}><Download aria-hidden="true" />Eksportuj do arkusza</button>
      </p>

      {log.resource.phase === "error" && <ErrorState title="Nie udało się wczytać dziennika" message={log.resource.error} onRetry={log.reload} />}
      {log.resource.phase === "loading" && <div style={{ display: "grid", gap: 12 }} aria-busy="true"><Skeleton height={14} /><Skeleton height={14} /><Skeleton height={14} width="70%" /></div>}
      {log.resource.phase === "ready" && sorted.length === 0 && (
        <EmptyState compact title="Brak wpisów" text={active ? "Żaden wpis nie spełnia filtrów. Zmień je albo wyczyść." : "W ostatnich 24 godzinach nie było żadnych zdarzeń. Wybierz dłuższy zakres dat."} />
      )}
      {log.resource.phase === "ready" && sorted.length > 0 && (
        <div className="audit-register">
          <div className="table-wrap" role="region" aria-label="Wpisy dziennika" tabIndex={0}>
            <table className="audit audit--striped" data-testid="audit-table">
              <caption className="sr-only">Wpisy dziennika audytu. Wybierz wpis, aby zobaczyć szczegóły pod tabelą.</caption>
              <thead>
                <tr>
                  {([["at", "Data i godzina"], ["actor", "Kto i rola"], ["action", "Działanie"], ["object", "Obiekt"]] as [SortKey, string][]).map(([k, label]) => {
                    const on = sort.key === k;
                    const Icon = !on ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;
                    return (
                      <th key={k} scope="col" aria-sort={on ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
                        <button type="button" className={`sortbtn${on ? " sortbtn--on" : ""}`} onClick={() => sortBy(k)}>{label}<Icon aria-hidden="true" /></button>
                      </th>
                    );
                  })}
                  <th scope="col">Wynik</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((e) => {
                  const on = selected?.id === e.id;
                  return (
                    <tr key={e.id} data-testid="audit-row" className={on ? "audit__row--on" : undefined} aria-selected={on} onClick={() => select(String(e.id))}>
                      <td className="nowrap">
                        <button type="button" className="audit__open" aria-controls="audit-pane" aria-expanded={on} onClick={(ev) => { ev.stopPropagation(); select(String(e.id)); }}>
                          {formatDateTime(e.at)}
                        </button>
                      </td>
                      <td>{e.actor_email}<span className="rt__sub">{(ROLE_LABEL[e.actor_role] ?? e.actor_role).toLowerCase()}</span></td>
                      <td className="audit__act">{AUDIT_ACTION_LABEL[e.action] ?? e.action}</td>
                      <td>{objectLabel(e)}{e.incident_title && <span className="rt__sub truncate">{e.incident_title}</span>}</td>
                      <td className="audit__ok">Zapisano</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {selected && <DetailPane entry={selected} onClose={() => select(null)} />}
        </div>
      )}
    </div>
  );
}

function DetailPane({ entry, onClose }: { entry: AuditEntry; onClose: () => void }) {
  const changes = describeChange(entry);
  return (
    <section className="audit-details" id="audit-pane" aria-label="Szczegóły wpisu" data-testid="audit-pane">
      <div className="apane__head">
        <h2 className="apane__title">{AUDIT_ACTION_LABEL[entry.action] ?? entry.action}</h2>
        <Button variant="ghost" iconOnly aria-label="Zamknij szczegóły" onClick={onClose}><X aria-hidden="true" /></Button>
      </div>
      <dl className="kv">
        <dt>Data i godzina</dt><dd>{formatDateTime(entry.at)} · wpis nr {entry.id}</dd>
        <dt>Kto</dt><dd>{entry.actor_email} ({ROLE_LABEL[entry.actor_role] ?? entry.actor_role})</dd>
        <dt>Obiekt</dt><dd>{objectLabel(entry)}</dd>
        {entry.incident_id && <><dt>ID sprawy</dt><dd><Link to={`/sprawy/${entry.incident_id}#historia`}>{caseRef(entry.incident_id)}</Link></dd></>}
        <dt>Uzasadnienie</dt><dd>{entry.reason ?? <span className="muted">brak</span>}</dd>
      </dl>
      {changes.length > 0 ? <div className="table-wrap"><table className="rt" data-testid="audit-changes">
        <caption>Zmienione wartości</caption>
        <thead><tr><th scope="col">Pole</th><th scope="col">Było</th><th scope="col">Jest</th></tr></thead>
        <tbody>{changes.map((c) => <tr key={c.field}><td>{c.label}</td><td>{c.before ?? "—"}</td><td>{c.after}</td></tr>)}</tbody>
      </table></div> : <p className="muted">Ten wpis nie zmienił żadnej wartości.</p>}
      <p className="apane__hint">Esc zamyka szczegóły, strzałki w górę i w dół przechodzą do sąsiednich wpisów.</p>
    </section>
  );
}
