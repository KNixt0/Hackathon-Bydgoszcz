import { CircleAlert, RotateCw } from "lucide-react";
import { useState } from "react";
import { formatDate, formatDateTime } from "../../domain/format";
import { CONTENT_STATE_LABEL, FOLLOW_UP_OUTCOME_LABEL } from "../../domain/labels";
import type { Incident, ObservationVersion } from "../../types/incident";
import { Button } from "../ui/Button";
import { ErrorState, Skeleton } from "../ui/States";

const OUTCOME_LABEL: Record<ObservationVersion["outcome"], string> = {
  content: "Treść pobrana",
  removed: "Treść usunięta",
  unreachable: "Źródło niedostępne",
};
const PAGE = 6;

interface Props {
  incident: Incident;
  versions: ObservationVersion[] | null;
  error: string | null;
  onRetry: () => void;
  /** Queues a re-check of the source; resolves to null or a Polish error message. */
  onRescan: () => Promise<string | null>;
}

/**
 * Contract v4: the post, its detection and every later check are separate facts. The detection is
 * frozen as evidence; later checks are listed here, and after an intervention they decide whether
 * the content was removed, corrected or is still online.
 */
export function ObservationPanel({ incident, versions, error, onRetry, onRescan }: Props) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const obs = incident.observation;
  const follow = incident.follow_up;
  const published = obs?.published_at ?? incident.source.published_at ?? null;

  const rescan = async () => {
    setBusy(true);
    setMessage(null);
    const failure = await onRescan();
    setBusy(false);
    setMessage(failure ? { tone: "error", text: failure } : { tone: "ok", text: "Sprawdzenie zlecone. Wynik pojawi się w tabeli za kilka sekund." });
  };

  return (
    <section className="csec" id="obserwacja" aria-labelledby="obserwacja-h">
      <h2 className="section-title" id="obserwacja-h">Materiał i weryfikacja</h2>
      <dl className="kv" data-testid="observation">
        <dt>Opublikowano</dt>
        <dd>{published ? formatDate(published) : <span className="muted">nie ustalono ze źródła</span>}</dd>
        <dt>Pierwsze wykrycie</dt>
        <dd>
          {formatDateTime(obs?.detected_at ?? incident.created_at)}
          <span className="rt__sub">Cytaty, kryteria i zrzuty w tej sprawie pochodzą z tej obserwacji.</span>
        </dd>
        <dt>Ostatnie sprawdzenie</dt>
        <dd>{obs ? formatDateTime(obs.last_checked_at) : <span className="muted">brak danych</span>}</dd>
        <dt>Stan treści</dt>
        <dd data-testid="content-state"><b>{CONTENT_STATE_LABEL[obs?.content_state ?? "online"]}</b></dd>
        {follow && (
          <>
            <dt>Interwencja</dt>
            <dd>{formatDate(follow.intervention_at)}: {follow.note}</dd>
            <dt>Termin weryfikacji</dt>
            <dd>{follow.due ? formatDate(follow.due) : <span className="muted">brak</span>}</dd>
            <dt>Wynik weryfikacji</dt>
            <dd data-testid="follow-up-outcome">
              {follow.outcome ? <b>{FOLLOW_UP_OUTCOME_LABEL[follow.outcome]}</b> : <span className="muted">jeszcze nie sprawdzono</span>}
            </dd>
          </>
        )}
      </dl>

      <div className="observation__acts">
        <Button onClick={() => void rescan()} disabled={busy}>
          <RotateCw aria-hidden="true" />{busy ? "Zlecanie…" : "Sprawdź źródło teraz"}
        </Button>
        {message && (
          <p className={message.tone === "error" ? "form-error" : "muted"} role={message.tone === "error" ? "alert" : "status"}>
            {message.tone === "error" && <CircleAlert aria-hidden="true" />}{message.text}
          </p>
        )}
      </div>

      {error ? (
        <ErrorState compact title="Nie udało się wczytać historii sprawdzeń" message={error} onRetry={onRetry} />
      ) : versions === null ? (
        <div aria-busy="true" style={{ display: "grid", gap: 8 }}><Skeleton height={14} width="55%" /><Skeleton height={14} width="40%" /></div>
      ) : (
        <VersionsTable versions={versions} />
      )}
    </section>
  );
}

function VersionsTable({ versions }: { versions: ObservationVersion[] }) {
  const [all, setAll] = useState(false);
  if (versions.length === 0) return null;
  const shown = all ? versions : versions.slice(0, PAGE);
  return (
    <>
      <div className="table-wrap">
        <table className="rt" data-testid="observations">
          <caption className="sr-only">Sprawdzenia źródła, od najnowszych</caption>
          <thead>
            <tr><th scope="col">Data</th><th scope="col">Wynik</th><th scope="col" className="num">Ryzyko</th></tr>
          </thead>
          <tbody>
            {shown.map((v) => (
              <tr key={v.id}>
                <td className="nowrap">{formatDateTime(v.created_at)}</td>
                <td>
                  {OUTCOME_LABEL[v.outcome]}
                  {v.outcome === "content" && (v.changed ? ", treść zmieniona" : ", bez zmian")}
                  {v.http_status && v.outcome !== "content" ? ` (HTTP ${v.http_status})` : ""}
                  {v.is_evidence && <span className="rt__sub"><b>Wykrycie: materiał dowodowy sprawy</b></span>}
                </td>
                <td className="num">{v.outcome === "content" ? v.risk_score.toFixed(1).replace(".", ",") : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {versions.length > PAGE && (
        <button type="button" className="linkbtn" onClick={() => setAll((v) => !v)}>{all ? "Pokaż tylko najnowsze" : "Pokaż starsze"}</button>
      )}
    </>
  );
}
