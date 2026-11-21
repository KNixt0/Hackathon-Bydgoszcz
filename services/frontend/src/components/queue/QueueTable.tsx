import { SearchX } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatDateTime, hostOf, relativeTime } from "../../domain/format";
import { PLATFORM_LABEL } from "../../domain/labels";
import { deriveLevel, type Thresholds } from "../../domain/levels";
import type { IncidentSummary, Status } from "../../types/incident";
import { Badge } from "../ui/Badge";
import { LevelBadge } from "../ui/LevelBadge";
import { ModuleTag } from "../ui/ModuleTag";
import { ScoreRail } from "../ui/ScoreRail";
import { EmptyState, Skeleton } from "../ui/States";
import { StatusSelect } from "./StatusSelect";

interface RowProps {
  incident: IncidentSummary;
  thresholds: Thresholds;
  fresh: boolean;
  busy: boolean;
  onStatusChange: (id: string, status: Status) => void;
}

export function QueueRow({ incident: it, thresholds, fresh, busy, onStatusChange }: RowProps) {
  const level = deriveLevel(it.risk_score, thresholds);
  const parties = [it.advertiser, it.firm && it.firm !== it.advertiser ? it.firm : null].filter(Boolean).join(" → ");
  const shownRules = it.failed_rules.slice(0, 5);
  return (
    <tr className={`queue__row--${level}${fresh ? " queue__row--fresh" : ""}`} data-testid="queue-row" data-level={level}>
      <td>
        <span className="queue__level">
          <LevelBadge level={level} />
          <ScoreRail riskScore={it.risk_score} thresholds={thresholds} />
        </span>
      </td>
      <td className="queue__case">
        <Link to={`/sprawy/${it.id}`} className="queue__title truncate" title={it.title}>{it.title}</Link>
        <span className="queue__parties truncate">
          {parties || "Podmiot nieustalony"}
          {fresh && <span className="queue__new"><Badge tone="accent">Nowa</Badge></span>}
        </span>
      </td>
      <td>
        <span className="queue__modules">
          {it.modules.map((m) => <ModuleTag key={m} module={m} compact />)}
        </span>
      </td>
      <td>
        <span style={{ display: "block" }}>{PLATFORM_LABEL[it.source.platform] ?? it.source.platform}</span>
        <span className="muted truncate" style={{ display: "block", maxWidth: 150, fontSize: "var(--fs-sm)" }} title={it.source.url}>{hostOf(it.source.url)}</span>
      </td>
      <td>
        {it.failed_rules.length === 0 ? (
          <span className="muted">brak</span>
        ) : (
          <span className="queue__rules" aria-label={`Naruszone kryteria: ${it.failed_rules.join(", ")}`}>
            {shownRules.map((r) => <span key={r} className="rule-pill">{r}</span>)}
            {it.failed_rules.length > shownRules.length && <span className="rule-pill rule-pill--more">+{it.failed_rules.length - shownRules.length}</span>}
          </span>
        )}
      </td>
      <td className="queue__when" title={formatDateTime(it.created_at)}>{relativeTime(it.created_at)}</td>
      <td>
        <StatusSelect value={it.status} disabled={busy} label={`Status sprawy: ${it.title}`} onChange={(s) => onStatusChange(it.id, s)} />
      </td>
    </tr>
  );
}

interface Props {
  items: IncidentSummary[];
  thresholds: Thresholds;
  freshIds: readonly string[];
  busyIds: readonly string[];
  loading?: boolean;
  onStatusChange: (id: string, status: Status) => void;
  emptyAction?: ReactNode;
  filtered?: boolean;
}

export function QueueTable({ items, thresholds, freshIds, busyIds, loading = false, onStatusChange, emptyAction, filtered = false }: Props) {
  if (!loading && items.length === 0) {
    return filtered ? (
      <EmptyState icon={<SearchX />} title="Żadna sprawa nie spełnia filtrów" text="Zmień kryteria albo wyczyść filtry, aby zobaczyć całą kolejkę." action={emptyAction} />
    ) : (
      <EmptyState title="Kolejka jest pusta" text="Nowe incydenty pojawią się tutaj automatycznie. Możesz też zeskanować adres URL lub zaimportować próbki." action={emptyAction} />
    );
  }
  return (
    <div className="table-wrap">
      <table className="queue" aria-busy={loading}>
        <caption className="sr-only">Kolejka spraw posortowana od najgroźniejszych</caption>
        <colgroup>
          <col className="c-level" /><col /><col className="c-mod" />
          <col className="c-src" /><col className="c-rules" /><col className="c-when" /><col className="c-status" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">Poziom i ryzyko</th>
            <th scope="col">Sprawa</th>
            <th scope="col">Moduł</th>
            <th scope="col">Źródło</th>
            <th scope="col">Naruszone kryteria</th>
            <th scope="col">Wykryto</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: 8 }, (_, i) => (
                <tr key={i} className="skeleton-row">
                  <td><Skeleton width={96} /><Skeleton width={120} height={8} style={{ marginTop: 8 }} /></td>
                  <td><Skeleton width={`${70 - (i % 3) * 12}%`} /><Skeleton width="40%" height={10} style={{ marginTop: 6 }} /></td>
                  <td><Skeleton width={24} /></td>
                  <td><Skeleton width={70} /></td>
                  <td><Skeleton width={60} /></td>
                  <td><Skeleton width={70} /></td>
                  <td><Skeleton width={110} height={22} /></td>
                </tr>
              ))
            : items.map((it) => (
                <QueueRow
                  key={it.id}
                  incident={it}
                  thresholds={thresholds}
                  fresh={freshIds.includes(it.id)}
                  busy={busyIds.includes(it.id)}
                  onStatusChange={onStatusChange}
                />
              ))}
        </tbody>
      </table>
    </div>
  );
}
