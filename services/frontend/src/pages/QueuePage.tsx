import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, exportListCsvUrl } from "../api/endpoints";
import { AlertBanner } from "../components/queue/AlertBanner";
import { LevelTabs, levelTabId } from "../components/queue/LevelTabs";
import { QueueFilters } from "../components/queue/QueueFilters";
import { QueueTable } from "../components/queue/QueueTable";
import { TrendStrip } from "../components/queue/TrendStrip";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { LEVEL_LABEL, MODULE_LABEL } from "../domain/labels";
import { countLevels } from "../domain/levels";
import { apiDate, clampDateTime, SYSTEM_START_LOCAL, warsawInput } from "../domain/dates";
import { pl, plN } from "../domain/plural";
import { activeFilterCount, applyQueue, EMPTY_FILTERS, filtersFromSearch, filtersToApiQuery, filtersToSearch, matchesFilters, type QueueFilters as Filters } from "../domain/queue";
import { trendRows, type TrendRow } from "../domain/trends";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import { useUi } from "../hooks/useUi";

const PANEL_ID = "kolejka-panel";

/** WatchIT: quick ranges for the inflow chart. 24 h is drawn per hour, the others per day. */
type Range = "24h" | "7d" | "30d" | "custom";
const RANGES: { key: Range; label: string }[] = [
  { key: "24h", label: "24 godz." },
  { key: "7d", label: "7 dni" },
  { key: "30d", label: "30 dni" },
  { key: "custom", label: "Własny zakres" },
];

/** "W ostatnich 24 godzinach wpłynęły 3 sprawy." from the trend rows (nothing invented). */
function inflowSentence(rows: TrendRow[], range: Range): string {
  const total = rows.reduce((sum, r) => sum + r.red + r.orange + r.green, 0);
  const period = range === "custom" ? "W wybranym okresie" : range === "24h" ? "W ostatnich 24 godzinach" : `W ostatnich ${rows.length} ${rows.length === 1 ? "dniu" : "dniach"}`;
  if (total === 0) return `${period} nie wpłynęła żadna sprawa.`;
  return `${period} ${pl(total, "wpłynęła", "wpłynęły", "wpłynęło")} ${plN(total, "sprawa", "sprawy", "spraw")}.`;
}

export function QueuePage() {
  const { thresholds, isGlobal } = useThresholds();
  const incidents = useIncidents();
  const { setScanOpen } = useUi();
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => filtersFromSearch(params), [params]);

  const [range, setRange] = useState<Range>("7d");
  const [draft, setDraft] = useState({ from: SYSTEM_START_LOCAL, to: warsawInput(new Date()) });
  const [custom, setCustom] = useState(draft);
  const invalidRange = draft.from > draft.to || !draft.from || !draft.to;
  const trends = useResource(
    (signal) => (range === "custom" ? api.trendsRange(apiDate(custom.from), apiDate(custom.to), signal) : range === "24h" ? api.trendsHourly(24, signal) : api.trends(range === "7d" ? 7 : 30, signal)),
    `trends:${range}:${custom.from}:${custom.to}`,
  );
  const { refresh: refreshTrends } = trends;
  useEffect(() => {
    if (incidents.revision > 0) refreshTrends();
  }, [incidents.revision, refreshTrends]);

  const setFilters = useCallback(
    (patch: Partial<Filters>) => setParams(filtersToSearch({ ...filters, ...patch }), { replace: true }),
    [filters, setParams],
  );
  const resetFilters = useCallback(() => setParams(filtersToSearch(EMPTY_FILTERS), { replace: true }), [setParams]);

  const pinned = useMemo(() => incidents.alerts.map((a) => a.id), [incidents.alerts]);
  const visible = useMemo(() => applyQueue(incidents.items, filters, thresholds, pinned), [incidents.items, filters, thresholds, pinned]);

  // Tab counts include everything that matches the other filters, so they stay useful while a level is selected.
  const counts = useMemo(() => {
    const withoutLevel = { ...filters, level: "" as const };
    return countLevels(incidents.items.filter((it) => matchesFilters(it, withoutLevel, thresholds)).map((it) => it.risk_score), thresholds);
  }, [incidents.items, filters, thresholds]);
  const all = useMemo(() => countLevels(incidents.items.map((i) => i.risk_score), thresholds), [incidents.items, thresholds]);

  const rows = useMemo(
    () => (trends.resource.phase === "ready" ? trendRows(trends.resource.data.days ?? [], thresholds, filters.module) : []),
    [trends.resource, thresholds, filters.module],
  );

  const loading = incidents.phase === "loading";
  const filtered = activeFilterCount(filters) > 0;
  const total = incidents.items.length;
  const filterSummary = [
    filters.level && `Poziom: ${LEVEL_LABEL[filters.level].toLowerCase()}.`,
    filters.module && `Moduł ${filters.module}: ${MODULE_LABEL[filters.module]}.`,
    filters.q && `Szukana fraza: „${filters.q}”.`,
  ].filter(Boolean).join(" ");

  return (
    <div className="page">
      <div className="page__head">
        <h1 className="page__title">Kolejka spraw</h1>
        {loading ? (
          <p className="page__sub" aria-hidden="true"><Skeleton width={420} height={16} /></p>
        ) : incidents.phase === "error" ? null : (
          <p className="page__sub">
            {plN(total, "sprawa", "sprawy", "spraw")} w kolejce. {all.red === 0 ? "Żadna nie jest krytyczna" : `${plN(all.red, "krytyczna", "krytyczne", "krytycznych")}`}
            {", "}{plN(all.orange, "do weryfikacji", "do weryfikacji", "do weryfikacji")}.
          </p>
        )}
        <p className="page__note" data-testid="queue-thresholds">
          Poziomy według progów {isGlobal ? "globalnych" : "z podglądu w tej przeglądarce"}: oznaczenie od <b className="num">{thresholds.orange}</b>, krytyczne od <b className="num">{thresholds.red}</b>.
        </p>
      </div>

      <AlertBanner alerts={incidents.alerts} onDismiss={incidents.dismissAlert} />

      {incidents.phase === "error" ? (
        <div className="panel panel--flush">
          <ErrorState title="Nie udało się wczytać kolejki" message={incidents.error ?? "Spróbuj ponownie."} onRetry={incidents.reload} />
        </div>
      ) : (
        <>
          <section className="strip" aria-labelledby="naplyw-h">
            <div className="strip__head">
              <h2 className="strip__title" id="naplyw-h">Napływ spraw</h2>
              <div className="seg" role="group" aria-label="Zakres wykresu">
                {RANGES.map((r) => (
                  <button key={r.key} type="button" className={`seg__btn${range === r.key ? " seg__btn--on" : ""}`} aria-pressed={range === r.key} onClick={() => setRange(r.key)}>
                    {r.label}
                  </button>
                ))}
              </div>
              {trends.resource.phase === "ready" && rows.length > 0 && <p className="strip__text">{inflowSentence(rows, range)} Słupki według poziomu przy obecnych progach.</p>}
            </div>
            {range === "custom" && <form className="qtool__row chart-range" onSubmit={(e) => { e.preventDefault(); if (!invalidRange) setCustom(draft); }}>
              <label className="field"><span className="field__label">Wykres od (czas polski)</span><input className="input" type="datetime-local" required min={SYSTEM_START_LOCAL} max={draft.to || warsawInput(new Date())} value={draft.from} onChange={(e) => setDraft({ ...draft, from: clampDateTime(e.target.value) })} /></label>
              <label className="field"><span className="field__label">Wykres do (czas polski)</span><input className="input" type="datetime-local" required min={draft.from || SYSTEM_START_LOCAL} max={warsawInput(new Date())} value={draft.to} onChange={(e) => setDraft({ ...draft, to: clampDateTime(e.target.value) })} /></label>
              <Button type="submit" disabled={invalidRange}>Zastosuj zakres</Button>
              {invalidRange && <p className="form-error" role="alert">Wybierz początek nie późniejszy niż koniec zakresu.</p>}
            </form>}
            {trends.resource.phase === "loading" && <div className="trend"><Skeleton height="100%" /></div>}
            {trends.resource.phase === "error" && <ErrorState compact title="Nie udało się wczytać napływu spraw" message={trends.resource.error} onRetry={trends.reload} />}
            {trends.resource.phase === "ready" && (rows.some((r) => r.red + r.orange + r.green > 0)
              ? <TrendStrip rows={rows} />
              : <EmptyState compact title="Brak incydentów w tym okresie" text="Wykres wypełni się po pierwszych wykryciach." />)}
          </section>

          <section aria-label="Lista spraw" className="qbox">
            <LevelTabs counts={counts} active={filters.level} onSelect={(level) => setFilters({ level })} panelId={PANEL_ID} />
            <div className="qpanel" id={PANEL_ID} role="tabpanel" aria-labelledby={levelTabId(filters.level)}>
              <QueueFilters filters={filters} onChange={setFilters} onReset={resetFilters} exportHref={exportListCsvUrl(filtersToApiQuery(filters))} />
              {incidents.error && incidents.phase === "ready" && (
                <p className="form-error" role="alert">Odświeżenie listy nie powiodło się: {incidents.error}</p>
              )}
              <QueueTable
                items={visible}
                thresholds={thresholds}
                freshIds={incidents.fresh}
                sort={filters.sort}
                dir={filters.dir}
                onSort={(sort, dir) => setFilters({ sort, dir })}
                loading={loading}
                filtered={filtered}
                filterSummary={filterSummary}
                emptyAction={filtered
                  ? <Button onClick={resetFilters}>Wyczyść filtry</Button>
                  : <Button variant="primary" onClick={() => setScanOpen(true)}>Analiza URL</Button>}
              />
              <div className="qfoot">
                <span role="status" data-testid="queue-count">
                  {filtered ? `Pokazano ${visible.length} z ${total} spraw` : `${plN(total, "sprawa", "sprawy", "spraw")}`}
                </span>
              </div>
              <p className="qleg">
                Moduły: 1 Reklamy podmiotów trzecich, 2 Zgodność i informacja o ryzyku, 3 Doradztwo bez zezwolenia. Kryteria według załącznika UKNF (18 kryteriów);
                najedź na numer kryterium, aby zobaczyć jego definicję. Skala przy wyniku: kreski oznaczają progi oznaczenia i krytyczny.
              </p>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
