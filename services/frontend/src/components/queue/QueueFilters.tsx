import { warsawInput, type DateBounds } from "../../domain/dates";
import { Download } from "lucide-react";
import { MODULE_SHORT, MODULES, PLATFORM_LABEL, PLATFORMS, STATUS_LABEL, STATUSES } from "../../domain/labels";
import { activeFilterCount, type QueueFilters as Filters } from "../../domain/queue";
import type { ModuleId, Platform, Status } from "../../types/incident";

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
  exportHref: string;
  bounds: DateBounds;
}

/** Toolbar inside the tab panel: search left, the other filters right, each with a visible label. Filtering is live. */
export function QueueFilters({ filters, onChange, onReset, exportHref, bounds }: Props) {
  const active = activeFilterCount({ ...filters, level: "" });
  return (
    <div className="filters-shell">
      <details className="disclosure filters-disclosure">
        <summary>Filtry{active > 0 && ` (${active})`}</summary>
        <form className="qtool" role="search" aria-label="Filtry kolejki" onSubmit={(e) => e.preventDefault()}>
      <div className="qtool__row">
        <div className="field qtool__search">
          <label className="field__label" htmlFor="q-search">Szukaj w kolejce</label>
          <input
            id="q-search" className="input" type="search" value={filters.q} placeholder="np. Tradeon"
            aria-describedby="q-search-hint" onChange={(e) => onChange({ q: e.target.value })}
          />
          <span className="sr-only" id="q-search-hint">Szuka w tytule, opisie, podmiotach i adresie. Lista zmienia się w trakcie pisania.</span>
        </div>
        <span className="qtool__links">
          {active > 0 && (
            <button type="button" className="linkbtn" onClick={onReset}>Wyczyść filtry<span className="num"> ({active})</span></button>
          )}
        </span>
      </div>
      <div className="qtool__row qtool__row--filters">
        <label className="field">
          <span className="field__label">Moduł</span>
          <select className="select" value={filters.module} onChange={(e) => onChange({ module: Number(e.target.value) as ModuleId | 0 })}>
            <option value={0}>Wszystkie</option>
            {MODULES.map((m) => <option key={m} value={m}>{m} {MODULE_SHORT[m]}</option>)}
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
        <label className="field qtool__date">
          <span className="field__label">Wykryto od</span>
          <input className="input" type="datetime-local" step={60} value={filters.from} min={warsawInput(bounds.earliest)} max={filters.to || warsawInput(new Date())} onChange={(e) => onChange({ from: e.target.value })} />
        </label>
        <label className="field qtool__date">
          <span className="field__label">Wykryto do</span>
          <input className="input" type="datetime-local" step={60} value={filters.to} min={filters.from || warsawInput(bounds.earliest)} max={warsawInput(new Date())} onChange={(e) => onChange({ to: e.target.value })} />
        </label>
      </div>
      <p className="field__hint">Daty w czasie polskim. Monitorowanie od {warsawInput(bounds.earliest).replace("T", " ")}. Przyszłe daty są niedostępne.</p>
        </form>
      </details>
      <a className="dl filters-export" href={exportHref} download><Download aria-hidden="true" />Eksportuj CSV</a>
    </div>
  );
}
