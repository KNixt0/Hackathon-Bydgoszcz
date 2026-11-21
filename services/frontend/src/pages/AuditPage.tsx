import { ShieldAlert } from "lucide-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import { Panel } from "../components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { describeChange } from "../domain/audit";
import { formatDateTime } from "../domain/format";
import { AUDIT_ACTION_LABEL, ROLE_LABEL } from "../domain/labels";
import { useUser } from "../hooks/useAuth";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";

const LIMIT = 500;

/** Supervisor only: the append-only audit trail, filterable by case and by actor (server-side). */
export function AuditPage() {
  const user = useUser();
  if (user.role !== "SUPERVISOR") {
    return (
      <div className="page">
        <div className="panel">
          <EmptyState icon={<ShieldAlert />} title="Dziennik audytu jest dostępny dla kierownika" text="Historię decyzji w konkretnej sprawie znajdziesz na stronie sprawy." action={<Link className="btn" to="/">Wróć do kolejki</Link>} />
        </div>
      </div>
    );
  }
  return <AuditLog />;
}

function AuditLog() {
  const [params, setParams] = useSearchParams();
  const incidentId = params.get("sprawa") ?? "";
  const actor = params.get("kto") ?? "";
  const incidents = useIncidents();
  const log = useResource((signal) => api.audit({ incident_id: incidentId || undefined, actor: actor || undefined, limit: LIMIT }, signal), `audit:${incidentId}:${actor}`);

  const entries = useMemo(() => (log.resource.phase === "ready" ? log.resource.data.items ?? [] : []), [log.resource]);
  // Actor options come from the entries shown (the API has no user list); "Wszyscy" widens them again.
  const seen = useMemo(() => [...new Set([...entries.map((e) => e.actor_email), ...(actor ? [actor] : [])])].sort(), [entries, actor]);

  const titles = useMemo(() => new Map(incidents.items.map((i) => [i.id, i.title])), [incidents.items]);
  const setFilter = (key: "sprawa" | "kto", value: string) =>
    setParams((prev) => { const p = new URLSearchParams(prev); if (value) p.set(key, value); else p.delete(key); return p; }, { replace: true });

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Dziennik audytu</h1>
          <p className="page__sub">Każde logowanie, przypisanie, zmiana etapu, ocena, zmiana progów, eksport i ponowne skanowanie, z wartością poprzednią i nową. Wpisów nie można zmienić ani usunąć.</p>
        </div>
      </div>
      <Panel title="Wpisy" hint={`Od najnowszych, do ${LIMIT} wpisów`} flush>
        <form className="filters audit__filters" role="search" aria-label="Filtry dziennika" onSubmit={(e) => e.preventDefault()}>
          <label className="field">
            <span className="field__label">Sprawa</span>
            <select className="select" value={incidentId} onChange={(e) => setFilter("sprawa", e.target.value)}>
              <option value="">Wszystkie</option>
              {incidentId && !titles.has(incidentId) && <option value={incidentId}>{incidentId}</option>}
              {incidents.items.map((i) => <option key={i.id} value={i.id}>{i.title}</option>)}
            </select>
          </label>
          <label className="field">
            <span className="field__label">Użytkownik</span>
            <select className="select" value={actor} onChange={(e) => setFilter("kto", e.target.value)}>
              <option value="">Wszyscy</option>
              {seen.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </label>
        </form>
        {log.resource.phase === "loading" && <div style={{ padding: 16, display: "grid", gap: 10 }} aria-busy="true"><Skeleton height={14} /><Skeleton height={14} /><Skeleton height={14} width="70%" /></div>}
        {log.resource.phase === "error" && <ErrorState title="Nie udało się wczytać dziennika" message={log.resource.error} onRetry={log.reload} />}
        {log.resource.phase === "ready" && entries.length === 0 && (
          <EmptyState compact title="Brak wpisów" text={incidentId || actor ? "Żaden wpis nie spełnia filtrów." : "Dziennik zapełni się po pierwszych logowaniach i decyzjach."} />
        )}
        {log.resource.phase === "ready" && entries.length > 0 && (
          <div className="table-wrap">
            <table className="audit" data-testid="audit-table">
              <caption className="sr-only">Wpisy dziennika audytu od najnowszych</caption>
              <thead>
                <tr><th scope="col">Kiedy</th><th scope="col">Kto</th><th scope="col">Działanie</th><th scope="col">Sprawa</th><th scope="col">Zmiana</th><th scope="col">Uzasadnienie</th></tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id} data-testid="audit-row">
                    <td className="audit__when">{formatDateTime(e.at)}</td>
                    <td>{e.actor_email}<span className="muted audit__role">{ROLE_LABEL[e.actor_role] ?? e.actor_role}</span></td>
                    <td>{AUDIT_ACTION_LABEL[e.action] ?? e.action}</td>
                    <td className="audit__case">
                      {e.incident_id ? <Link to={`/sprawy/${e.incident_id}#historia`} className="truncate" title={titles.get(e.incident_id) ?? e.incident_id}>{titles.get(e.incident_id) ?? `Sprawa ${e.incident_id.slice(0, 8)}`}</Link> : <span className="muted">nie dotyczy</span>}
                    </td>
                    <td>
                      {describeChange(e).map((c) => (
                        <span key={c.field} className="audit__change">{c.label}: {c.before !== null && <>{c.before} → </>}<strong>{c.after}</strong></span>
                      ))}
                    </td>
                    <td className="audit__reason">{e.reason ?? <span className="muted">brak</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
