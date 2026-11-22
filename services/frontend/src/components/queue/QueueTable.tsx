import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatDate, formatDateTime, formatTime, hostOf, relativeTime } from "../../domain/format";
import { processingDuration } from "../../domain/dates";
import { PLATFORM_LABEL, STATUS_LABEL } from "../../domain/labels";
import { deriveLevel, type Thresholds } from "../../domain/levels";
import type { QueueFilters } from "../../domain/queue";
import type { IncidentSummary } from "../../types/incident";
import { Badge } from "../ui/Badge";
import { LevelBadge } from "../ui/LevelBadge";
import { ModuleList } from "../ui/ModuleTag";
import { ScoreRail } from "../ui/ScoreRail";
import { RuleTip } from "../ui/RuleTip";
import { SortHeader } from "../ui/SortHeader";
import { EmptyState, Skeleton } from "../ui/States";

export const caseRef = (id: string) => id.replace(/-/g, "").slice(-8).toUpperCase();

export function QueueRow({ incident: it, thresholds, fresh, now = Date.now() }: { incident: IncidentSummary; thresholds: Thresholds; fresh: boolean; now?: number }) {
  const level = deriveLevel(it.risk_score, thresholds);
  const parties = [it.advertiser, it.firm && it.firm !== it.advertiser ? it.firm : null].filter(Boolean).join(" → ");
  const started = it.workflow?.processing_started_at;
  const finished = it.workflow?.processing_finished_at;
  return <tr className={fresh ? "queue__row--fresh" : undefined} data-testid="queue-row" data-level={level}>
    <td data-label="Poziom i ryzyko"><span className="queue__level"><LevelBadge level={level} /><ScoreRail riskScore={it.risk_score} thresholds={thresholds} /></span></td>
    <td className="num" data-label="ID sprawy"><Link to={`/sprawy/${it.id}`} title={it.id}>{caseRef(it.id)}</Link></td>
    <td className="queue__case" data-label="Sprawa"><Link to={`/sprawy/${it.id}`} className="queue__title" title={it.title}>{it.title}</Link><span className="queue__sub truncate">{parties || "Podmiot do ustalenia"}</span></td>
    <td data-label="Źródło"><span className="queue__cell-main">{PLATFORM_LABEL[it.source.platform] ?? it.source.platform}</span><span className="queue__sub truncate" title={it.source.url}>{hostOf(it.source.url)}</span></td>
    <td data-label="Moduł"><ModuleList modules={it.modules} /></td>
    <td data-label="Naruszone kryteria">{it.failed_rules.length ? <span className="queue__rules"><span className="sr-only">Naruszone kryteria: </span>{it.failed_rules.map((id, index) => <span key={id}>{index > 0 && ", "}<RuleTip id={id} definition={it.failed_rule_details?.find((r) => r.id === id)} /></span>)}</span> : <span className="muted">brak</span>}</td>
    <td data-label="Status i prowadzący"><span className="queue__status"><Link to={`/sprawy/${it.id}#workflow-h`} aria-label={`Status sprawy: ${it.title}: ${STATUS_LABEL[it.status]}`} data-status={it.status}>{STATUS_LABEL[it.status]}</Link>{fresh && <Badge tone="accent">Nowa</Badge>}<span className="queue__sub truncate" title={it.workflow?.assigned_to ?? undefined}>{it.workflow?.assigned_to ?? "nieprzypisana"}</span></span></td>
    <td className="queue__when" data-label="Wykryto"><time dateTime={it.created_at} aria-label={formatDateTime(it.created_at)} title={relativeTime(it.created_at)}><span>{formatDate(it.created_at)}</span><span className="queue__sub">{formatTime(it.created_at)}</span></time></td>
    <td className="queue__when" data-label="Rozpoczęto obsługę">{started ? <time dateTime={started} aria-label={formatDateTime(started)}><span>{formatDate(started)}</span><span className="queue__sub">{formatTime(started)}</span></time> : <span className="muted">Nie rozpoczęto</span>}</td>
    <td data-label="Czas obsługi"><span className="nowrap num">{processingDuration(started, finished, now)}</span>{finished && <span className="queue__sub">zakończono</span>}</td>
  </tr>;
}

interface Props {
  items: IncidentSummary[];
  thresholds: Thresholds;
  freshIds: readonly string[];
  loading?: boolean;
  emptyAction?: ReactNode;
  filtered?: boolean;
  filterSummary?: string;
  sort?: QueueFilters["sort"];
  direction?: "asc" | "desc";
  onSort?: (sort: QueueFilters["sort"]) => void;
}
const COLUMNS: [QueueFilters["sort"], string][] = [["risk", "Poziom i ryzyko"], ["id", "ID sprawy"], ["title", "Sprawa"], ["source", "Źródło"], ["module", "Moduł"], ["rules", "Naruszone kryteria"], ["status", "Status i prowadzący"], ["detected", "Wykryto"], ["processing", "Rozpoczęto obsługę"], ["duration", "Czas obsługi"]];

export function QueueTable({ items, thresholds, freshIds, loading = false, emptyAction, filtered = false, filterSummary, sort = "risk", direction = "desc", onSort }: Props) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 60000); return () => window.clearInterval(timer); }, []);
  if (!loading && items.length === 0) return <EmptyState title={filtered ? "Żadna sprawa nie spełnia filtrów" : "Kolejka jest pusta"} text={filtered ? `${filterSummary ?? ""} Zmień kryteria albo wyczyść filtry.` : "Nowe sprawy pojawią się automatycznie. Możesz też zlecić analizę adresu URL."} action={emptyAction} />;
  return <>
    <div className="queue-sort" aria-label="Sortowanie spraw">
      <label className="field"><span className="field__label">Sortuj według</span><select className="select" value={sort} onChange={(event) => onSort?.(event.target.value as QueueFilters["sort"])}>{COLUMNS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <button type="button" className="btn" onClick={() => onSort?.(sort)} aria-label={`Zmień kierunek sortowania: ${direction === "asc" ? "rosnąco" : "malejąco"}`}>{direction === "asc" ? "Rosnąco ↑" : "Malejąco ↓"}</button>
    </div>
    <div className="table-wrap" role="region" aria-label="Tabela spraw" tabIndex={0}>
    <table className="queue" aria-busy={loading}>
      <caption className="sr-only">Kolejka spraw</caption>
      <colgroup><col className="c-level" /><col className="c-id" /><col /><col className="c-src" /><col className="c-mod" /><col className="c-rules" /><col className="c-status" /><col className="c-when" /><col className="c-when" /><col className="c-duration" /></colgroup>
      <thead><tr>{COLUMNS.map(([key, label]) => <SortHeader key={key} label={label} active={sort === key} direction={direction} onSort={() => onSort?.(key)} />)}</tr></thead>
      <tbody>{loading ? Array.from({ length: 8 }, (_, i) => <tr key={i} className="skeleton-row">{COLUMNS.map(([key]) => <td key={key}><Skeleton width="80%" /></td>)}</tr>) : items.map((it) => <QueueRow key={it.id} incident={it} thresholds={thresholds} fresh={freshIds.includes(it.id)} now={now} />)}</tbody>
    </table>
  </div></>;
}
