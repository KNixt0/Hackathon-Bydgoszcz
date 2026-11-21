import { useState } from "react";
import { describeChange } from "../../domain/audit";
import { formatDateTime } from "../../domain/format";
import { AUDIT_ACTION_LABEL, ROLE_LABEL } from "../../domain/labels";
import type { AuditEntry } from "../../types/api";
import { ErrorState, Skeleton } from "../ui/States";

const DECISIONS = new Set(["assign", "transition", "label"]);
const PAGE = 10;

interface Props {
  items: AuditEntry[] | null;
  error: string | null;
  onRetry: () => void;
}

/** Who decided what and why (GET /api/incidents/{id}/history), newest first, as a ruled table. */
export function DecisionHistory({ items, error, onRetry }: Props) {
  return (
    <section className="csec" id="historia" aria-labelledby="historia-h">
      <h2 className="section-title" id="historia-h">Historia decyzji</h2>
      {error ? (
        <ErrorState compact title="Nie udało się wczytać historii" message={error} onRetry={onRetry} />
      ) : items === null ? (
        <div aria-busy="true" style={{ display: "grid", gap: 8 }}><Skeleton height={14} width="60%" /><Skeleton height={14} width="45%" /></div>
      ) : (
        <HistoryTable items={items.filter((e) => DECISIONS.has(e.action))} />
      )}
    </section>
  );
}

function HistoryTable({ items }: { items: AuditEntry[] }) {
  const [all, setAll] = useState(false);
  if (items.length === 0) return <p className="muted">Brak decyzji. Pierwszy wpis powstanie po przejęciu sprawy lub zmianie statusu.</p>;
  const newestFirst = [...items].sort((a, b) => b.at.localeCompare(a.at));
  const shown = all ? newestFirst : newestFirst.slice(0, PAGE);
  return (
    <>
      <div className="table-wrap">
        <table className="rt history" data-testid="decision-history">
          <caption className="sr-only">Historia decyzji, od najnowszych</caption>
          <thead><tr><th scope="col">Data i kto</th><th scope="col">Decyzja</th><th scope="col">Uzasadnienie</th></tr></thead>
          <tbody>
            {shown.map((e) => (
              <tr key={e.id} data-testid="decision-row">
                <td className="history__who">
                  <span className="nowrap">{formatDateTime(e.at)}</span>
                  <span className="rt__sub">{e.actor_email}, {(ROLE_LABEL[e.actor_role] ?? e.actor_role).toLowerCase()}</span>
                </td>
                <td>
                  <span className="history__what">{AUDIT_ACTION_LABEL[e.action] ?? e.action}</span>
                  {describeChange(e).map((c) => (
                    <span key={c.field} className="history__change">
                      {c.label}: {c.before !== null && <>{c.before} → </>}<b>{c.after}</b>
                    </span>
                  ))}
                </td>
                <td className="history__reason">{e.reason ?? <span className="muted">brak</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {newestFirst.length > PAGE && (
        <button type="button" className="linkbtn" onClick={() => setAll((v) => !v)}>{all ? "Pokaż tylko najnowsze" : "Pokaż starsze"}</button>
      )}
    </>
  );
}
