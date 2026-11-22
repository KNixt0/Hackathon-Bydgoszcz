import { ChevronDown, Download, SlidersHorizontal } from "lucide-react";
import { useId, useState } from "react";
import { clampDateTime, SYSTEM_START_LOCAL, warsawInput } from "../../domain/dates";
import { MODULE_SHORT, MODULES, PLATFORM_LABEL, PLATFORMS, STATUS_LABEL, STATUSES } from "../../domain/labels";
import { activeFilterCount, type QueueFilters as Filters } from "../../domain/queue";
import type { ModuleId, Platform, Status } from "../../types/incident";

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
  exportHref: string;
}

/**
 * Under the level tabs: search and export stay visible; the other filters sit in a panel that folds away.
 * Filtering is live. Dates run from the system start (21.11.2026) to today, never later.
 */
export function QueueFilters({ filters, onChange, onReset, exportHref }: Props) {
  const panelId = useId();
  const extra = [filters.module ? "m" : "", filters.platform, filters.status, filters.from, filters.to].filter(Boolean).length;
  const [open, setOpen] = useState(extra > 0);
  const active = activeFilterCount({ ...filters, level: "" });
  const today = warsawInput(new Date());
  return (
    <form className="qtool" role="search" aria-label="Filtry kolejki" onSubmit={(e) => e.preventDefault()}>
      <div className="qtool__row">
        <div className="field qtool__search">
          <label className="field__label" htmlFor="q-search">Szukaj w kolejce</label>
          <input
            id="q-search" className="input" type="search" value={filters.q} placeholder="np. Tradeon"
            aria-describedby="q-search-hint" onChange={(e) => onChange({ q: e.target.value })}
          />
          <span className="sr-only" id="q-search-hint">Szuka w tytule, opisie, podmiotach i adresie URL. Lista zmienia się w trakcie pisania.</span>
        </div>
        <button
          type="button" className={`btn qtool__toggle${open ? " qtool__toggle--on" : ""}`}
          aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((v) => !v)}
        >
          <SlidersHorizontal aria-hidden="true" />Więcej filtrów{extra > 0 && <span className="num"> ({extra})</span>}
          <ChevronDown aria-hidden="true" className="qtool__chev" />
        </button>
        <span className="qtool__links">
          {active > 0 && (
            <button type="button" className="linkbtn" onClick={onReset}>Wyczyść filtry<span className="num"> ({active})</span></button>
          )}
          <a className="dl" href={exportHref} download>
            <Download aria-hidden="true" />Eksportuj do arkusza
          </a>
        </span>
      </div>
      <div className="qtool__row qtool__row--filters" id={panelId} hidden={!open} data-testid="filters-panel">
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
          <input
            className="input" type="datetime-local" value={filters.from ? clampDateTime(filters.from) : ""} min={SYSTEM_START_LOCAL} max={filters.to || today}
            onChange={(e) => onChange({ from: clampDateTime(e.target.value, filters.to || today) })}
          />
        </label>
        <label className="field qtool__date">
          <span className="field__label">Wykryto do</span>
          <input
            className="input" type="datetime-local" value={filters.to ? clampDateTime(filters.to) : ""} min={filters.from || SYSTEM_START_LOCAL} max={today}
            onChange={(e) => onChange({ to: e.target.value ? [clampDateTime(e.target.value, today), filters.from].sort().at(-1) || "" : "" })}
          />
        </label>
      </div>
    </form>
  );
}
