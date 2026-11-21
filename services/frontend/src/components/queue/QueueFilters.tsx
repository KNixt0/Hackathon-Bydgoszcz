import { Download } from "lucide-react";
import { MODULE_SHORT, MODULES, PLATFORM_LABEL, PLATFORMS, STATUS_LABEL, STATUSES, TIER_FILTER_LABEL } from "../../domain/labels";
import { TIERS, type PriorityTier } from "../../domain/priority";
import { activeFilterCount, type QueueFilters as Filters } from "../../domain/queue";
import type { ModuleId, Platform, Status } from "../../types/incident";

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
  exportHref: string;
}

/** Toolbar inside the tab panel: search left, the other filters right, each with a visible label. Filtering is live. */
export function QueueFilters({ filters, onChange, onReset, exportHref }: Props) {
  const active = activeFilterCount({ ...filters, level: "" });
  return (
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
        <label className="field">
          <span className="field__label">Sortowanie</span>
          <select className="select" value={filters.sort} onChange={(e) => onChange({ sort: e.target.value as Filters["sort"] })}>
            <option value="risk">Ryzyko, od najwyższego</option>
            <option value="priority">Priorytet: ryzyko i zgłoszenia</option>
          </select>
        </label>
        <span className="qtool__links">
          {active > 0 && (
            <button type="button" className="linkbtn" onClick={onReset}>Wyczyść filtry<span className="num"> ({active})</span></button>
          )}
          <a className="dl" href={exportHref} download>
            <Download aria-hidden="true" />Eksportuj CSV
          </a>
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
        <label className="field">
          <span className="field__label">Priorytet zgłoszeń</span>
          <select className="select" value={filters.tier} onChange={(e) => onChange({ tier: e.target.value as PriorityTier | "" })}>
            <option value="">Wszystkie</option>
            {TIERS.map((t) => <option key={t} value={t}>{TIER_FILTER_LABEL[t]}</option>)}
          </select>
        </label>
        <label className="field qtool__date">
          <span className="field__label">Wykryto od</span>
          <input className="input" type="date" value={filters.from} max={filters.to || undefined} onChange={(e) => onChange({ from: e.target.value })} />
        </label>
        <label className="field qtool__date">
          <span className="field__label">Wykryto do</span>
          <input className="input" type="date" value={filters.to} min={filters.from || undefined} onChange={(e) => onChange({ to: e.target.value })} />
        </label>
      </div>
    </form>
  );
}
