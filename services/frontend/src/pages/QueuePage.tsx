import { useCallback, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { api, exportListCsvUrl } from "../api/endpoints";
import { AlertBanner } from "../components/queue/AlertBanner";
import { LevelSummary } from "../components/queue/LevelSummary";
import { QueueFilters } from "../components/queue/QueueFilters";
import { QueueTable } from "../components/queue/QueueTable";
import { TrendChart } from "../components/queue/TrendChart";
import { Button } from "../components/ui/Button";
import { Panel } from "../components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { countLevels } from "../domain/levels";
import { activeFilterCount, applyQueue, EMPTY_FILTERS, filtersFromSearch, filtersToApiQuery, filtersToSearch, matchesFilters, type QueueFilters as Filters } from "../domain/queue";
import { trendRows } from "../domain/trends";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import { useUi } from "../hooks/useUi";

export function QueuePage() {
  const { thresholds } = useThresholds();
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

  // Tiles count everything that matches the other filters, so they stay useful while a level is selected.
  const counts = useMemo(() => {
    const withoutLevel = { ...filters, level: "" as const };
    return countLevels(incidents.items.filter((it) => matchesFilters(it, withoutLevel, thresholds)).map((it) => it.risk_score), thresholds);
  }, [incidents.items, filters, thresholds]);

  const rows = useMemo(
    () => (trends.resource.phase === "ready" ? trendRows(trends.resource.data.days ?? [], thresholds, filters.module) : []),
    [trends.resource, thresholds, filters.module],
  );

  const loading = incidents.phase === "loading";
  const filtered = activeFilterCount(filters) > 0;

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Kolejka spraw</h1>
          <p className="page__sub">Incydenty wykryte przez silnik, uporządkowane od najgroźniejszych. Poziomy wynikają z progów ustawionych w kalibracji.</p>
        </div>
      </div>

      <AlertBanner alerts={incidents.alerts} onDismiss={incidents.dismissAlert} viral={incidents.viralAlerts} onDismissViral={incidents.dismissViralAlert} />

      {incidents.phase === "error" ? (
        <div className="panel"><ErrorState message={incidents.error ?? ""} onRetry={incidents.reload} /></div>
      ) : (
        <>
          <div className="overview">
            <Panel title="Poziomy ryzyka" hint={`Progi: ${thresholds.orange} i ${thresholds.red}`} flush>
              {loading ? (
                <div style={{ padding: 16, display: "grid", gap: 14 }}><Skeleton height={34} /><Skeleton height={34} /><Skeleton height={34} /></div>
              ) : (
                <LevelSummary counts={counts} thresholds={thresholds} active={filters.level} onSelect={(level) => setFilters({ level })} />
              )}
            </Panel>
            <Panel title="Incydenty w czasie" hint="Ostatnie 30 dni, według poziomu przy obecnych progach" flush>
              {trends.resource.phase === "loading" && <div className="trend" style={{ padding: 16 }}><Skeleton height="100%" /></div>}
              {trends.resource.phase === "error" && <ErrorState compact title="Nie udało się wczytać trendu" message={trends.resource.error} onRetry={trends.reload} />}
              {trends.resource.phase === "ready" && (rows.some((r) => r.red + r.orange + r.green > 0)
                ? <TrendChart rows={rows} />
                : <EmptyState compact title="Brak incydentów w tym okresie" text="Wykres wypełni się po pierwszych wykryciach." />)}
            </Panel>
          </div>

          <section className="panel" aria-label="Lista spraw">
            <QueueFilters
              filters={filters}
              onChange={setFilters}
              onReset={resetFilters}
              shown={visible.length}
              total={incidents.items.length}
              exportHref={exportListCsvUrl(filtersToApiQuery(filters))}
            />
            {incidents.error && incidents.phase === "ready" && (
              <p className="form-error" role="alert" style={{ padding: "8px 16px" }}>Odświeżenie listy nie powiodło się: {incidents.error}</p>
            )}
            <QueueTable
              items={visible}
              thresholds={thresholds}
              freshIds={incidents.fresh}
              loading={loading}
              filtered={filtered}
              emptyAction={filtered
                ? <Button onClick={resetFilters}>Wyczyść filtry</Button>
                : <Button variant="primary" onClick={() => setScanOpen(true)}>Skanuj URL</Button>}
            />
          </section>
        </>
      )}
    </div>
  );
}
