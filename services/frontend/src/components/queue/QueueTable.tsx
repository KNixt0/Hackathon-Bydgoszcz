import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatDateTime, formatDuration, hostOf, relativeTime } from "../../domain/format";
import { FOLLOW_UP_OUTCOME_LABEL, PLATFORM_LABEL, STATUS_LABEL } from "../../domain/labels";
import { deriveLevel, type Thresholds } from "../../domain/levels";
import type { SortDir, SortKey } from "../../domain/queue";
import { ruleTooltip } from "../../domain/rules";
import { useNow } from "../../hooks/useNow";
import type { IncidentSummary } from "../../types/incident";
import { Badge } from "../ui/Badge";
import { Hint } from "../ui/Hint";
import { LevelBadge } from "../ui/LevelBadge";
import { ModuleList } from "../ui/ModuleTag";
import { ScoreRail } from "../ui/ScoreRail";
import { EmptyState, Skeleton } from "../ui/States";

/** Short case reference shown in the queue, on the case page and in the palette. */
export const caseRef = (id: string) => id.replace(/-/g, "").slice(-8).toUpperCase();

interface RowProps {
  incident: IncidentSummary;
  thresholds: Thresholds;
  fresh: boolean;
  now: number;
}

/** When somebody started working on the case and for how long it has been (or was) in progress. */
function Processing({ incident: it, now }: { incident: IncidentSummary; now: number }) {
  const started = it.workflow?.started_at;
  if (!started) return <span className="muted">nie rozpoczęto</span>;
  const closed = it.workflow?.closed_at;
  const end = closed ? Date.parse(closed) : now;
  const took = formatDuration(end - Date.parse(started));
  return (
    <>
      <span className="queue__cell-main" title={formatDateTime(started)}>{formatDateTime(started)}</span>
      <span className="queue__sub" data-testid="processing-time">{closed ? `zamknięto po ${took}` : `w toku od ${took}`}</span>
    </>
  );
}

export function QueueRow({ incident: it, thresholds, fresh, now }: RowProps) {
  const level = deriveLevel(it.risk_score, thresholds);
  const parties = [it.advertiser, it.firm && it.firm !== it.advertiser ? it.firm : null].filter(Boolean).join(" → ");
  return (
    <tr className={fresh ? "queue__row--fresh" : undefined} data-testid="queue-row" data-level={level}>
      <td>
        <span className="queue__level">
          <LevelBadge level={level} />
          <ScoreRail riskScore={it.risk_score} thresholds={thresholds} />
        </span>
      </td>
      <td className="num" data-testid="case-id" title={it.id}>{caseRef(it.id)}</td>
      <td className="queue__case">
        <Link to={`/sprawy/${it.id}`} className="queue__title" title={it.title}>{it.title}</Link>
        <span className="queue__sub truncate">{parties || "podmiot nieustalony"}</span>
      </td>
      <td>
        <span className="queue__cell-main">{PLATFORM_LABEL[it.source.platform] ?? it.source.platform}</span>
        <span className="queue__sub truncate" title={it.source.url}>{hostOf(it.source.url)}</span>
      </td>
      <td><ModuleList modules={it.modules} /></td>
      <td>
        {it.failed_rules.length === 0 ? (
          <span className="muted">brak</span>
        ) : (
          <span className="queue__rules">
            <span className="sr-only">Naruszone kryteria: </span>
            {it.failed_rules.map((id, i) => (
              <span key={id}>
                {i > 0 && ", "}
                <Hint text={ruleTooltip(id)}><span className="num">{id}</span></Hint>
              </span>
            ))}
          </span>
        )}
      </td>
      <td>
        {/* Transitions need context (reasons, escalation path): they happen on the case page. */}
        <span className="queue__status">
          <span>
            <Link to={`/sprawy/${it.id}#workflow-h`} aria-label={`Status sprawy: ${it.title}: ${STATUS_LABEL[it.status] ?? it.status}`} data-status={it.status}>
              {STATUS_LABEL[it.status] ?? it.status}
            </Link>
            {fresh && <span className="queue__new"><Badge tone="accent">Nowa</Badge></span>}
          </span>
          <span className="queue__sub truncate" title={it.workflow?.assigned_to ?? undefined}>
            {it.workflow?.assigned_to ?? "nieprzypisana"}
          </span>
          {it.follow_up?.outcome && (
            <span className="queue__sub" data-testid="follow-up">{FOLLOW_UP_OUTCOME_LABEL[it.follow_up.outcome]}</span>
          )}
        </span>
      </td>
      <td className="queue__when" title={formatDateTime(it.created_at)}>
        <span className="queue__cell-main">{formatDateTime(it.created_at)}</span>
        <span className="queue__sub">{relativeTime(it.created_at)}</span>
      </td>
      <td className="queue__when"><Processing incident={it} now={now} /></td>
    </tr>
  );
}

const COLUMNS: { key: SortKey; label: string; col?: string }[] = [
  { key: "risk", label: "Poziom i ryzyko", col: "c-level" },
  { key: "id", label: "ID sprawy", col: "c-id" },
  { key: "title", label: "Sprawa" },
  { key: "source", label: "Źródło", col: "c-src" },
  { key: "module", label: "Moduł", col: "c-mod" },
  { key: "rules", label: "Naruszone kryteria", col: "c-rules" },
  { key: "status", label: "Status i prowadzący", col: "c-status" },
  { key: "detected", label: "Wykryto", col: "c-when" },
  { key: "started", label: "Rozpoczęto pracę", col: "c-started" },
];
const DIR_LABEL: Record<SortDir, string> = { asc: "rosnąco", desc: "malejąco" };

interface Props {
  items: IncidentSummary[];
  thresholds: Thresholds;
  freshIds: readonly string[];
  sort: SortKey;
  dir: SortDir;
  /** a header click: the same column flips the direction, another column starts descending */
  onSort: (key: SortKey, dir: SortDir) => void;
  loading?: boolean;
  emptyAction?: ReactNode;
  filtered?: boolean;
  /** what the filter is, for the filtered-to-zero message */
  filterSummary?: string;
}

export function QueueTable({ items, thresholds, freshIds, sort, dir, onSort, loading = false, emptyAction, filtered = false, filterSummary }: Props) {
  const now = useNow();
  if (!loading && items.length === 0) {
    return filtered ? (
      <EmptyState title="Żadna sprawa nie spełnia filtrów" text={filterSummary ? `${filterSummary} Zmień kryteria albo wyczyść filtry.` : "Zmień kryteria albo wyczyść filtry, aby zobaczyć całą kolejkę."} action={emptyAction} />
    ) : (
      <EmptyState title="Kolejka jest pusta" text="Nowe sprawy pojawią się tutaj automatycznie. Możesz też przeanalizować adres URL." action={emptyAction} />
    );
  }
  return (
    <div className="table-wrap" role="region" aria-label="Tabela spraw" tabIndex={0}>
      <table className="queue queue--striped" aria-busy={loading}>
        <caption className="sr-only">Kolejka spraw. Kliknij nagłówek kolumny, aby posortować rosnąco lub malejąco.</caption>
        <colgroup>
          {COLUMNS.map((c) => <col key={c.key} className={c.col} />)}
        </colgroup>
        <thead>
          <tr>
            {COLUMNS.map((c) => {
              const active = sort === c.key;
              const Icon = !active ? ArrowUpDown : dir === "asc" ? ArrowUp : ArrowDown;
              const next: SortDir = active && dir === "desc" ? "asc" : "desc";
              return (
                <th key={c.key} scope="col" aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}>
                  <button
                    type="button" className={`sortbtn${active ? " sortbtn--on" : ""}`} onClick={() => onSort(c.key, next)}
                    title={`Sortuj ${DIR_LABEL[next]}`}
                  >
                    {c.label}<Icon aria-hidden="true" />
                    {active && <span className="sr-only">, posortowano {DIR_LABEL[dir]}</span>}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: 8 }, (_, i) => (
                <tr key={i} className="skeleton-row">
                  <td><Skeleton width={110} /><Skeleton width={84} height={10} style={{ marginTop: 8 }} /></td>
                  <td><Skeleton width={70} /></td>
                  <td><Skeleton width={`${72 - (i % 3) * 12}%`} /><Skeleton width="40%" height={10} style={{ marginTop: 8 }} /></td>
                  <td><Skeleton width={70} /></td>
                  <td><Skeleton width={28} /></td>
                  <td><Skeleton width={80} /></td>
                  <td><Skeleton width={110} /></td>
                  <td><Skeleton width={80} /></td>
                  <td><Skeleton width={80} /></td>
                </tr>
              ))
            : items.map((it) => (
                <QueueRow key={it.id} incident={it} thresholds={thresholds} fresh={freshIds.includes(it.id)} now={now} />
              ))}
        </tbody>
      </table>
    </div>
  );
}
