import { X } from "lucide-react";
import { LEVEL_LABEL, MODULE_SHORT, MODULES, PLATFORM_LABEL, PLATFORMS, STATUS_LABEL, STATUSES } from "../../domain/labels";
import { LEVELS } from "../../domain/levels";
import { activeFilterCount, EMPTY_FILTERS, type QueueFilters } from "../../domain/queue";
import type { ModuleId, Platform, RiskLevel, Status } from "../../types/incident";
import { Button } from "../ui/Button";

interface Props {
  filters: QueueFilters;
  onChange: (next: QueueFilters) => void;
}

export function Filters({ filters, onChange }: Props) {
  const set = <K extends keyof QueueFilters>(key: K, value: QueueFilters[K]) => onChange({ ...filters, [key]: value });
  const count = activeFilterCount(filters);
  return (
    <form className="filters" role="search" aria-label="Filtry kolejki" onSubmit={(e) => e.preventDefault()}>
      <label className="field filters__q">
        <span className="field__label">Szukaj</span>
        <input className="input" type="search" value={filters.q} placeholder="Tytuł, podmiot, adres"
          onChange={(e) => set("q", e.target.value)} />
      </label>
      <label className="field">
        <span className="field__label">Moduł</span>
        <select className="select" value={filters.module} onChange={(e) => set("module", Number(e.target.value) as ModuleId | 0)}>
          <option value={0}>Wszystkie</option>
          {MODULES.map((m) => <option key={m} value={m}>{m}. {MODULE_SHORT[m]}</option>)}
        </select>
      </label>
      <label className="field">
        <span className="field__label">Poziom ryzyka</span>
        <select className="select" value={filters.level} onChange={(e) => set("level", e.target.value as RiskLevel | "")}>
          <option value="">Wszystkie</option>
          {LEVELS.map((l) => <option key={l} value={l}>{LEVEL_LABEL[l]}</option>)}
        </select>
      </label>
      <label className="field">
        <span className="field__label">Źródło</span>
        <select className="select" value={filters.platform} onChange={(e) => set("platform", e.target.value as Platform | "")}>
          <option value="">Wszystkie</option>
          {PLATFORMS.map((p) => <option key={p} value={p}>{PLATFORM_LABEL[p]}</option>)}
        </select>
      </label>
      <label className="field">
        <span className="field__label">Status</span>
        <select className="select" value={filters.status} onChange={(e) => set("status", e.target.value as Status | "")}>
          <option value="">Wszystkie</option>
          {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
        </select>
      </label>
      <label className="field">
        <span className="field__label">Od</span>
        <input className="input" type="date" value={filters.from} max={filters.to || undefined} onChange={(e) => set("from", e.target.value)} />
      </label>
      <label className="field">
        <span className="field__label">Do</span>
        <input className="input" type="date" value={filters.to} min={filters.from || undefined} onChange={(e) => set("to", e.target.value)} />
      </label>
      <Button variant="ghost" onClick={() => onChange(EMPTY_FILTERS)} disabled={count === 0}>
        <X aria-hidden="true" />Wyczyść{count > 0 ? ` (${count})` : ""}
      </Button>
    </form>
  );
}
