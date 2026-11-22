import { useEffect } from "react";
import { api } from "../../api/endpoints";
import { formatDateTime } from "../../domain/format";
import { ROLE_LABEL } from "../../domain/labels";
import { useResource } from "../../hooks/useResource";
import type { AuditEntry } from "../../types/api";
import { ErrorState, Skeleton } from "../ui/States";

const KIND: Record<string, string> = { thresholds: "Progi globalne", calibration_preview: "Podgląd własny" };

function pair(v: unknown): string {
  if (!v || typeof v !== "object") return "domyślne";
  const t = v as { flag?: number; critical?: number };
  return `oznaczenie ${t.flag ?? "?"}, krytyczne ${t.critical ?? "?"}`;
}

/**
 * WatchIt: who changed the calibration and how. Global changes (supervisor) and the thresholds each user set
 * for their own view, newest first. Recorded on the server; nothing pops up when a change is saved.
 */
export function CalibrationHistory({ revision }: { revision: number }) {
  const history = useResource((signal) => api.thresholdsHistory(signal), "calibration-history");
  const { refresh } = history;
  useEffect(() => {
    if (revision > 0) refresh();
  }, [revision, refresh]);
  const items: AuditEntry[] = history.resource.phase === "ready" ? history.resource.data.items ?? [] : [];
  return (
    <section className="calib__section" aria-labelledby="calib-history-h" data-testid="calibration-history">
      <h2 className="section-title" id="calib-history-h">Historia zmian kalibracji</h2>
      {history.resource.phase === "error" ? (
        <ErrorState compact title="Nie udało się wczytać historii zmian" message={history.resource.error} onRetry={history.reload} />
      ) : history.resource.phase === "loading" ? (
        <div aria-busy="true" style={{ display: "grid", gap: 8 }}><Skeleton height={14} width="60%" /><Skeleton height={14} width="45%" /></div>
      ) : items.length === 0 ? (
        <p className="muted">Nikt jeszcze nie zmieniał progów.</p>
      ) : (
        <div className="table-wrap">
          <table className="rt">
            <caption className="sr-only">Historia zmian kalibracji, od najnowszych</caption>
            <thead>
              <tr><th scope="col">Kiedy</th><th scope="col">Kto</th><th scope="col">Rodzaj</th><th scope="col">Zmiana</th></tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} data-testid="calibration-change">
                  <td className="nowrap">{formatDateTime(e.at)}</td>
                  <td>{e.actor_email}<span className="rt__sub">{(ROLE_LABEL[e.actor_role] ?? e.actor_role).toLowerCase()}</span></td>
                  <td>{KIND[e.action] ?? e.action}</td>
                  <td>{e.previous ? <>{pair(e.previous)} → </> : null}<b>{pair(e.new)}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
