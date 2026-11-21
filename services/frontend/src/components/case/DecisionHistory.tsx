import { describeChange } from "../../domain/audit";
import { formatDateTime } from "../../domain/format";
import { AUDIT_ACTION_LABEL, ROLE_LABEL } from "../../domain/labels";
import type { AuditEntry } from "../../types/api";
import { EmptyState, ErrorState, Skeleton } from "../ui/States";

const DECISIONS = new Set(["assign", "transition", "label"]);

interface Props {
  items: AuditEntry[] | null;
  error: string | null;
  onRetry: () => void;
}

/** Block 5: who decided what and why, oldest first (from GET /api/incidents/{id}/history). */
export function DecisionHistory({ items, error, onRetry }: Props) {
  return (
    <section className="panel block" id="historia" aria-labelledby="historia-h">
      <header className="panel__head">
        <h2 className="panel__title" id="historia-h"><span className="block__n">5</span>Historia decyzji</h2>
      </header>
      {error ? (
        <ErrorState compact title="Nie udało się wczytać historii" message={error} onRetry={onRetry} />
      ) : items === null ? (
        <div className="panel__body" aria-busy="true"><Skeleton height={14} width="60%" /><Skeleton height={14} width="45%" style={{ marginTop: 8 }} /></div>
      ) : (
        <HistoryList items={items.filter((e) => DECISIONS.has(e.action))} />
      )}
    </section>
  );
}

function HistoryList({ items }: { items: AuditEntry[] }) {
  if (items.length === 0) return <EmptyState compact title="Brak decyzji" text="Przejęcie sprawy, zmiany etapu i ocena trafności pojawią się tutaj." />;
  return (
    <ol className="history" data-testid="decision-history">
      {items.map((e) => (
        <li key={e.id} className="history__item">
          <span className="history__when">{formatDateTime(e.at)}</span>
          <span className="history__body">
            <span className="history__what">
              <strong>{AUDIT_ACTION_LABEL[e.action] ?? e.action}</strong>
              <span className="muted"> · {e.actor_email} ({ROLE_LABEL[e.actor_role] ?? e.actor_role})</span>
            </span>
            {describeChange(e).map((c) => (
              <span key={c.field} className="history__change">
                {c.label}: {c.before !== null && <>{c.before} → </>}<strong>{c.after}</strong>
              </span>
            ))}
            {e.reason && <span className="history__reason">Uzasadnienie: {e.reason}</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}
