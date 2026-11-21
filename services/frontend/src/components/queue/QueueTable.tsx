import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatDateTime, hostOf, relativeTime, reportsLabel } from "../../domain/format";
import { PLATFORM_LABEL, STATUS_LABEL } from "../../domain/labels";
import { deriveLevel, type Thresholds } from "../../domain/levels";
import { reportsOf, tierOf } from "../../domain/priority";
import type { IncidentSummary } from "../../types/incident";
import { Badge } from "../ui/Badge";
import { LevelBadge } from "../ui/LevelBadge";
import { ModuleList } from "../ui/ModuleTag";
import { PriorityTierTag } from "../ui/PriorityTierTag";
import { ScoreRail } from "../ui/ScoreRail";
import { EmptyState, Skeleton } from "../ui/States";

/** Short case reference shown in the queue, on the case page and in the palette. */
export const caseRef = (id: string) => id.replace(/-/g, "").slice(-8).toUpperCase();

interface RowProps {
  incident: IncidentSummary;
  thresholds: Thresholds;
  fresh: boolean;
}

export function QueueRow({ incident: it, thresholds, fresh }: RowProps) {
  const level = deriveLevel(it.risk_score, thresholds);
  const parties = [it.advertiser, it.firm && it.firm !== it.advertiser ? it.firm : null].filter(Boolean).join(" → ");
  const reports = reportsOf(it);
  const tier = tierOf(it, thresholds);
  return (
    <tr className={fresh ? "queue__row--fresh" : undefined} data-testid="queue-row" data-level={level}>
      <td>
        <span className="queue__level">
          <LevelBadge level={level} />
          <ScoreRail riskScore={it.risk_score} thresholds={thresholds} />
        </span>
      </td>
      <td className="queue__case">
        <Link to={`/sprawy/${it.id}`} className="queue__title" title={it.title}>{it.title}</Link>
        <span className="queue__sub truncate">
          <span className="num">{caseRef(it.id)}</span>, {parties || "podmiot nieustalony"}
        </span>
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
            <span aria-hidden="true">kryt. </span>
            <span className="sr-only">Naruszone kryteria: </span>
            {it.failed_rules.join(", ")}
          </span>
        )}
      </td>
      <td>
        {reports > 0 || tier !== "low_watch" ? (
          <span className="queue__crowd">
            {reports > 0 && <span className="queue__reports" data-testid="report-count">{reportsLabel(reports)}</span>}
            <PriorityTierTag tier={tier} />
          </span>
        ) : <span className="muted">brak</span>}
      </td>
      <td>
        {/* Transitions need context (reasons, escalation path): they happen on the case page. */}
        <span className="queue__status">
          <span>
            <Link to={`/sprawy/${it.id}#werdykt`} aria-label={`Status sprawy: ${it.title}: ${STATUS_LABEL[it.status] ?? it.status}`} data-status={it.status}>
              {STATUS_LABEL[it.status] ?? it.status}
            </Link>
            {fresh && <span className="queue__new"><Badge tone="accent">Nowa</Badge></span>}
          </span>
          <span className="queue__sub truncate" title={it.workflow?.assigned_to ?? undefined}>
            {it.workflow?.assigned_to ?? "nieprzypisana"}
          </span>
        </span>
      </td>
      <td className="queue__when" title={formatDateTime(it.created_at)}>{relativeTime(it.created_at)}</td>
    </tr>
  );
}

interface Props {
  items: IncidentSummary[];
  thresholds: Thresholds;
  freshIds: readonly string[];
  loading?: boolean;
  emptyAction?: ReactNode;
  filtered?: boolean;
  /** what the filter is, for the filtered-to-zero message */
  filterSummary?: string;
}

const HEAD = (
  <thead>
    <tr>
      <th scope="col">Poziom i ryzyko</th>
      <th scope="col">Sprawa</th>
      <th scope="col">Źródło</th>
      <th scope="col">Moduł</th>
      <th scope="col">Naruszone kryteria</th>
      <th scope="col">Zgłoszenia i priorytet</th>
      <th scope="col">Status i prowadzący</th>
      <th scope="col">Wykryto</th>
    </tr>
  </thead>
);

export function QueueTable({ items, thresholds, freshIds, loading = false, emptyAction, filtered = false, filterSummary }: Props) {
  if (!loading && items.length === 0) {
    return filtered ? (
      <EmptyState title="Żadna sprawa nie spełnia filtrów" text={filterSummary ? `${filterSummary} Zmień kryteria albo wyczyść filtry.` : "Zmień kryteria albo wyczyść filtry, aby zobaczyć całą kolejkę."} action={emptyAction} />
    ) : (
      <EmptyState title="Kolejka jest pusta" text="Nowe sprawy pojawią się tutaj automatycznie. Możesz też zeskanować adres URL lub zaimportować próbki." action={emptyAction} />
    );
  }
  return (
    <div className="table-wrap" role="region" aria-label="Tabela spraw" tabIndex={0}>
      <table className="queue" aria-busy={loading}>
        <caption className="sr-only">Kolejka spraw</caption>
        <colgroup>
          <col className="c-level" /><col /><col className="c-src" /><col className="c-mod" />
          <col className="c-rules" /><col className="c-crowd" /><col className="c-status" /><col className="c-when" />
        </colgroup>
        {HEAD}
        <tbody>
          {loading
            ? Array.from({ length: 8 }, (_, i) => (
                <tr key={i} className="skeleton-row">
                  <td><Skeleton width={110} /><Skeleton width={84} height={10} style={{ marginTop: 8 }} /></td>
                  <td><Skeleton width={`${72 - (i % 3) * 12}%`} /><Skeleton width="40%" height={10} style={{ marginTop: 8 }} /></td>
                  <td><Skeleton width={70} /></td>
                  <td><Skeleton width={28} /></td>
                  <td><Skeleton width={80} /></td>
                  <td><Skeleton width={90} /></td>
                  <td><Skeleton width={110} /></td>
                  <td><Skeleton width={70} /></td>
                </tr>
              ))
            : items.map((it) => (
                <QueueRow key={it.id} incident={it} thresholds={thresholds} fresh={freshIds.includes(it.id)} />
              ))}
        </tbody>
      </table>
    </div>
  );
}
