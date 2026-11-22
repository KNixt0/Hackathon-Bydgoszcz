import { useEffect, useState } from "react";
import { CircleAlert } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { SortHeader } from "../components/ui/SortHeader";
import { Button } from "../components/ui/Button";
import { describeChange } from "../domain/audit";
import { apiDate, validDateInput, warsawInput } from "../domain/dates";
import { formatDateTime } from "../domain/format";
import { AUDIT_ACTION_LABEL, ROLE_LABEL } from "../domain/labels";
import { useUser } from "../hooks/useAuth";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";

const LIMIT = 100;
const COLUMNS = [["at", "Data i godzina"], ["actor", "Użytkownik"], ["action", "Zdarzenie"], ["incident_id", "Sprawa"], ["details", "Szczegóły"], ["reason", "Uzasadnienie"]] as const;
export function AuditPage() {
  const user = useUser();
  if (user.role !== "SUPERVISOR") return <div className="page"><h1 className="page__title">Dziennik audytu</h1><div className="callout callout--error" role="status"><p className="callout__lead"><CircleAlert aria-hidden="true" />Dziennik audytu jest dostępny dla kierownika</p><p>Historię decyzji znajdziesz na stronie sprawy.</p><Link to="/">Wróć do kolejki</Link></div></div>;
  return <AuditLog />;
}
function AuditLog() {
  const [params, setParams] = useSearchParams();
  const incidents = useIncidents();
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 60000); return () => window.clearInterval(timer); }, []);
  const incidentId = params.get("sprawa") ?? "";
  const actor = params.get("kto") ?? "";
  const action = params.get("zdarzenie") ?? "";
  const from = validDateInput(params.get("od") ?? "") ? params.get("od")! : "";
  const to = validDateInput(params.get("do") ?? "") ? params.get("do")! : "";
  const sort = COLUMNS.some(([key]) => key === params.get("sortowanie")) ? params.get("sortowanie")! : "at";
  const order = params.get("kierunek") === "asc" ? "asc" : "desc";
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const log = useResource((signal) => api.audit({ incident_id: incidentId, actor, action, from: from ? apiDate(from) : undefined, to: to ? apiDate(to) : undefined, sort, order, offset, limit: LIMIT }, signal), `audit:${params.toString()}`);
  const entries = log.resource.phase === "ready" ? log.resource.data.items ?? [] : [];
  const total = log.resource.phase === "ready" ? log.resource.data.total ?? entries.length : 0;
  const active = [incidentId, actor, action, from, to].filter(Boolean).length;
  const setFilter = (key: string, value: string) => setParams((previous) => { const p = new URLSearchParams(previous); if (value) p.set(key, value); else p.delete(key); if (key !== "offset") p.delete("offset"); return p; }, { replace: true });
  const setSort = (key: string) => setParams((previous) => { const p = new URLSearchParams(previous); p.set("sortowanie", key); p.set("kierunek", sort === key && order === "asc" ? "desc" : "asc"); p.delete("offset"); return p; }, { replace: true });
  const titles = new Map(incidents.items.map((item) => [item.id, item.title]));
  return <div className="page">
    <div className="page__head"><h1 className="page__title">Dziennik audytu</h1><p className="page__sub">Historia logowań, przypisań, decyzji, zmian progów i eksportów. Wpisów nie można edytować ani usuwać. Kliknij nagłówek, aby zmienić kolejność.</p></div>
    <section className="qpanel" aria-label="Wpisy dziennika">
      <details className="disclosure filters-disclosure"><summary>Filtry dziennika{active > 0 && ` (${active})`}</summary>
        <form className="qtool" role="search" aria-label="Filtry dziennika" onSubmit={(e) => e.preventDefault()}><div className="qtool__row">
          <label className="field audit__f-case"><span className="field__label">Sprawa</span><select className="select" value={incidentId} onChange={(e) => setFilter("sprawa", e.target.value)}><option value="">Wszystkie</option>{incidentId && !titles.has(incidentId) && <option value={incidentId}>{incidentId}</option>}{incidents.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <label className="field"><span className="field__label">Użytkownik</span><input className="input" type="search" placeholder="Adres e-mail" value={actor} onChange={(e) => setFilter("kto", e.target.value)} /></label>
          <label className="field"><span className="field__label">Zdarzenie</span><select className="select" value={action} onChange={(e) => setFilter("zdarzenie", e.target.value)}><option value="">Wszystkie</option>{Object.entries(AUDIT_ACTION_LABEL).filter(([key]) => key !== "public_report").map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label className="field"><span className="field__label">Data od</span><input className="input" type="datetime-local" min={warsawInput(incidents.dateBounds.earliest)} max={to || warsawInput(now)} value={from} onChange={(e) => setFilter("od", e.target.value)} /></label>
          <label className="field"><span className="field__label">Data do</span><input className="input" type="datetime-local" min={from || warsawInput(incidents.dateBounds.earliest)} max={warsawInput(now)} value={to} onChange={(e) => setFilter("do", e.target.value)} /></label>
          {active > 0 && <Button onClick={() => setParams({})}>Wyczyść filtry</Button>}
        </div></form>
      </details>
      {log.resource.phase === "loading" && <div aria-busy="true"><Skeleton height={14} /><Skeleton height={14} /></div>}
      {log.resource.phase === "error" && <ErrorState title="Nie udało się wczytać dziennika" message={log.resource.error} onRetry={log.reload} />}
      {log.resource.phase === "ready" && !entries.length && <EmptyState compact title="Brak wpisów" text={active ? "Żaden wpis nie spełnia filtrów." : "Wpisy pojawią się po pierwszych logowaniach i decyzjach."} />}
      {log.resource.phase === "ready" && entries.length > 0 && <div className="table-wrap" role="region" aria-label="Tabela wpisów" tabIndex={0}><table className="audit" data-testid="audit-table">
        <caption className="sr-only">Dziennik audytu</caption><thead><tr>{COLUMNS.map(([key, label]) => <SortHeader key={key} label={label} active={sort === key} direction={order} onSort={() => setSort(key)} />)}</tr></thead>
        <tbody>{entries.map((entry) => <tr key={entry.id} data-testid="audit-row">
          <td className="audit__when">{formatDateTime(entry.at)}</td>
          <td>{entry.actor_email}<span className="audit__role">{ROLE_LABEL[entry.actor_role].toLowerCase()}</span></td>
          <td>{AUDIT_ACTION_LABEL[entry.action] ?? entry.action}</td>
          <td className="audit__case">{entry.incident_id ? <Link to={`/sprawy/${entry.incident_id}#historia`} title={entry.incident_id}>{titles.get(entry.incident_id) ?? entry.incident_id}</Link> : <span className="muted">nie dotyczy</span>}</td>
          <td>{describeChange(entry).map((change) => <span key={change.field} className="audit__change">{change.label}: {change.before !== null && <>{change.before} → </>}<b>{change.after}</b></span>)}</td>
          <td className="audit__reason">{entry.reason ?? <span className="muted">brak</span>}</td>
        </tr>)}</tbody>
      </table></div>}
      <div className="qfoot"><span>{total} wpisów. {entries.length > 0 && `Pokazano ${offset + 1}–${offset + entries.length}.`}</span><span><Button disabled={offset === 0} onClick={() => setFilter("offset", String(Math.max(0, offset - LIMIT)))}>Poprzednie</Button> <Button disabled={offset + LIMIT >= total} onClick={() => setFilter("offset", String(offset + LIMIT))}>Następne</Button></span></div>
    </section>
  </div>;
}
