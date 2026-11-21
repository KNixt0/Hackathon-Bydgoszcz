import { useCallback, useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
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
import { pl, plN } from "../domain/plural";
import { activeFilterCount, applyQueue, EMPTY_FILTERS, filtersFromSearch, filtersToApiQuery, filtersToSearch, matchesFilters, type QueueFilters as Filters } from "../domain/queue";
import { trendRows, type TrendRow } from "../domain/trends";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import { useUi } from "../hooks/useUi";

const PANEL_ID = "kolejka-panel";

/** "3 nowe sprawy dziś, średnio 2 dziennie w ostatnich 30 dniach." from the trend rows (nothing invented). */
function inflowSentence(rows: TrendRow[]): string {
  const totals = rows.map((r) => r.red + r.orange + r.green);
  const today = totals[totals.length - 1] ?? 0;
  const avg = totals.length ? Math.round(totals.reduce((a, b) => a + b, 0) / totals.length) : 0;
  const todayText = today === 0 ? "Dziś nie wpłynęła żadna sprawa" : `Dziś ${pl(today, "wpłynęła", "wpłynęły", "wpłynęło")} ${plN(today, "nowa sprawa", "nowe sprawy", "nowych spraw")}`;
  return `${todayText}, średnio ${avg} dziennie w ostatnich ${totals.length} dniach.`;
}

export function QueuePage() {
  const { thresholds, isGlobal } = useThresholds();
  const incidents = useIncidents();
  const { setScanOpen } = useUi();
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => filtersFromSearch(params), [params]);

  const trends = useResource((signal) => api.trends(30, signal), "trends");
  const { refresh: refreshTrends } = trends;
  useEffect(() => {
    if (incidents.revision > 0) refreshTrends();
  }, [incidents.revision, refreshTrends]);

  const setFilters = useCallback(
    (patch: Partial<Filters>) => setParams(filtersToSearch({ ...filters, ...patch }), { replace: true }),
    [filters, setParams],
  );
  const resetFilters = useCallback(() => setParams(filtersToSearch(EMPTY_FILTERS), { replace: true }), [setParams]);

  const pinned = useMemo(
    () => [...incidents.alerts, ...incidents.viralAlerts.filter((v) => !incidents.alerts.some((a) => a.id === v.id))].map((a) => a.id),
    [incidents.alerts, incidents.viralAlerts],
  );
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
          Poziomy według progów {isGlobal ? "globalnych" : "z podglądu w tej przeglądarce"}: oznaczenie od <b className="num">{thresholds.orange}</b>, krytyczne od <b className="num">{thresholds.red}</b>.{" "}
          <Link to="/kalibracja">{isGlobal ? "Kalibracja progów" : "Zapisz lub przywróć w kalibracji"}</Link>
        </p>
      </div>

      <AlertBanner alerts={incidents.alerts} onDismiss={incidents.dismissAlert} viral={incidents.viralAlerts} onDismissViral={incidents.dismissViralAlert} />

      {incidents.phase === "error" ? (
        <div className="panel panel--flush">
          <ErrorState title="Nie udało się wczytać kolejki" message={incidents.error ?? "Spróbuj ponownie."} onRetry={incidents.reload} />
        </div>
      ) : (
        <>
          <section className="strip" aria-labelledby="naplyw-h">
            <div className="strip__head">
              <h2 className="strip__title" id="naplyw-h">Napływ spraw</h2>
              {trends.resource.phase === "ready" && rows.length > 0 && <p className="strip__text">{inflowSentence(rows)} Słupki według poziomu przy obecnych progach.</p>}
            </div>
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
                loading={loading}
                filtered={filtered}
                filterSummary={filterSummary}
                emptyAction={filtered
                  ? <Button onClick={resetFilters}>Wyczyść filtry</Button>
                  : <Button variant="primary" onClick={() => setScanOpen(true)}>Skanuj URL</Button>}
              />
              <div className="qfoot">
                <span role="status" data-testid="queue-count">
                  {filtered ? `Pokazano ${visible.length} z ${total} spraw` : `${plN(total, "sprawa", "sprawy", "spraw")}`}, {filters.sort === "priority" ? "od najwyższego priorytetu" : "od najwyższego ryzyka"}
                </span>
              </div>
              <p className="qleg">
                Moduły: 1 Finfluencerzy i podmioty trzecie, 2 Zgodność i informacja o ryzyku, 3 Shadow advisory. Kryteria według załącznika UKNF (18 kryteriów).
                Skala przy wyniku: kreski oznaczają progi oznaczenia i krytyczny.
              </p>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
