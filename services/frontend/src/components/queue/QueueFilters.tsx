import { Download, Search, X } from "lucide-react";
import { LEVEL_LABEL, MODULE_SHORT, MODULES, PLATFORM_LABEL, PLATFORMS, STATUS_LABEL, STATUSES } from "../../domain/labels";
import { LEVELS } from "../../domain/levels";
import { activeFilterCount, type QueueFilters as Filters } from "../../domain/queue";
import type { ModuleId, Platform, RiskLevel, Status } from "../../types/incident";
import { Button, ButtonLink } from "../ui/Button";

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
  shown: number;
  total: number;
  exportHref: string;
}

export function QueueFilters({ filters, onChange, onReset, shown, total, exportHref }: Props) {
  const active = activeFilterCount(filters);
  return (
    <>
      <form className="filters" role="search" aria-label="Filtry kolejki" onSubmit={(e) => e.preventDefault()}>
        <label className="field filters__search">
          <span className="field__label">Szukaj</span>
          <Search aria-hidden="true" />
          <input className="input" type="search" value={filters.q} placeholder="Tytuł, podmiot, adres" onChange={(e) => onChange({ q: e.target.value })} />
        </label>
        <label className="field">
          <span className="field__label">Poziom ryzyka</span>
          <select className="select" value={filters.level} onChange={(e) => onChange({ level: e.target.value as RiskLevel | "" })}>
            <option value="">Wszystkie</option>
            {LEVELS.map((l) => <option key={l} value={l}>{LEVEL_LABEL[l]}</option>)}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Moduł</span>
          <select className="select" value={filters.module} onChange={(e) => onChange({ module: Number(e.target.value) as ModuleId | 0 })}>
            <option value={0}>Wszystkie</option>
            {MODULES.map((m) => <option key={m} value={m}>{m}. {MODULE_SHORT[m]}</option>)}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Źródło</span>
          <select className="select" value={filters.platform} onChange={(e) => onChange({ platform: e.target.value as Platform | "" })}>
            <option value="">Wszystkie</option>
            {PLATFORMS.map((p) => <option key={p} value={p}>{PLATFORM_LABEL[p]}</option>)}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Status</span>
          <select className="select" value={filters.status} onChange={(e) => onChange({ status: e.target.value as Status | "" })}>
            <option value="">Wszystkie</option>
            {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Wykryto od</span>
          <input className="input" type="date" value={filters.from} max={filters.to || undefined} onChange={(e) => onChange({ from: e.target.value })} />
        </label>
        <label className="field">
          <span className="field__label">Wykryto do</span>
          <input className="input" type="date" value={filters.to} min={filters.from || undefined} onChange={(e) => onChange({ to: e.target.value })} />
        </label>
      </form>
      <div className="filters__meta">
        <span role="status" data-testid="queue-count">
          {active > 0 ? `Pokazano ${shown} z ${total} spraw` : `${total} spraw`} · od najgroźniejszych
        </span>
        <span className="filters__meta-actions">
          {active > 0 && (
            <Button variant="ghost" size="sm" onClick={onReset}><X aria-hidden="true" />Wyczyść filtry ({active})</Button>
          )}
          <ButtonLink variant="ghost" size="sm" href={exportHref} download>
            <Download aria-hidden="true" />Eksportuj CSV
          </ButtonLink>
        </span>
      </div>
    </>
  );
}
