import { BellRing, Download, FileSearch, RotateCw, SearchX, X } from "lucide-react";
import { useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, exportListCsvUrl } from "../api/endpoints";
import { Filters } from "../components/queue/Filters";
import { IncidentTable } from "../components/queue/IncidentTable";
import { TrendChart } from "../components/queue/TrendChart";
import { Button, ButtonLink } from "../components/ui/Button";
import { LevelBadge } from "../components/ui/LevelBadge";
import { Panel } from "../components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { LEVEL_LABEL } from "../domain/labels";
import { countLevels, LEVELS } from "../domain/levels";
import { applyQueue, filtersFromSearch, filtersToApiQuery, filtersToSearch } from "../domain/queue";
import { relativeTime } from "../domain/format";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";

export function QueuePage() {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => filtersFromSearch(params), [params]);
  const { thresholds } = useThresholds();
  const incidents = useIncidents();
  const trends = useResource((signal) => api.trends(30, signal), "trends");
  const { refresh } = trends;

  useEffect(() => {
    if (incidents.revision > 0) refresh();
  }, [incidents.revision, refresh]);

  const alertIds = useMemo(() => incidents.alerts.map((a) => a.id), [incidents.alerts]);
  const visible = useMemo(
    () => applyQueue(incidents.items, filters, thresholds, alertIds),
    [incidents.items, filters, thresholds, alertIds],
  );
  const counts = useMemo(() => countLevels(incidents.items.map((i) => i.risk_score), thresholds), [incidents.items, thresholds]);
  const isFiltered = filtersToSearch(filters).size > 0;

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Kolejka spraw</h1>
          <p className="page__sub">
            Wykryte reklamy i oferty uporządkowane od najgroźniejszych. Poziomy wynikają z surowego wyniku ryzyka (0–100)
            i progów ustawionych w <Link to="/kalibracja">kalibracji</Link>.
          </p>
        </div>
        <div className="page__actions">
          <Button onClick={incidents.reload} aria-label="Odśwież listę"><RotateCw aria-hidden="true" />Odśwież</Button>
          <ButtonLink href={exportListCsvUrl(filtersToApiQuery(filters))} download>
            <Download aria-hidden="true" />Eksport CSV
          </ButtonLink>
        </div>
      </div>

      {incidents.alerts.length > 0 && (
        <section className="alerts" aria-label="Alerty wysokiego ryzyka" role="region">
          <div className="alerts__head"><BellRing aria-hidden="true" /><strong>Nowe alerty wysokiego ryzyka ({incidents.alerts.length})</strong></div>
          <ul>
            {incidents.alerts.map((a) => (
              <li key={a.id} className="alerts__item">
                <span className="alerts__score num">{Math.round(a.risk_score)}</span>
                <Link to={`/sprawy/${a.id}`} className="alerts__title truncate">{a.title}</Link>
                <span className="muted nowrap">{relativeTime(a.created_at)}</span>
                <Link to={`/sprawy/${a.id}`} className="btn btn--sm"><FileSearch aria-hidden="true" />Otwórz</Link>
                <Button size="sm" variant="ghost" iconOnly aria-label={`Zamknij alert: ${a.title}`} onClick={() => incidents.dismissAlert(a.id)}>
                  <X aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="kpis" role="group" aria-label="Liczba spraw według poziomu">
        {LEVELS.map((level) => {
          const active = filters.level === level;
          return (
            <button
              key={level}
              type="button"
              className={`kpi kpi--${level}${active ? " kpi--active" : ""}`}
              aria-pressed={active}
              onClick={() => {
                const next = filtersToSearch({ ...filters, level: active ? "" : level });
                setParams(next, { replace: true });
              }}
            >
              <span className="kpi__label"><LevelBadge level={level} /></span>
              <span className="kpi__value num">{incidents.phase === "ready" ? counts[level] : "–"}</span>
              <span className="kpi__hint">
                {level === "red" && `od ${thresholds.red} pkt ryzyka`}
                {level === "orange" && `${thresholds.orange}–${Math.max(thresholds.orange, thresholds.red - 1)} pkt`}
                {level === "green" && `poniżej ${thresholds.orange} pkt`}
              </span>
            </button>
          );
        })}
        <div className="kpi kpi--total">
          <span className="kpi__label">Wszystkie sprawy</span>
          <span className="kpi__value num">{incidents.phase === "ready" ? incidents.items.length : "–"}</span>
          <span className="kpi__hint">w kolejce</span>
        </div>
      </div>

      <Panel title="Wykrycia w czasie" hint="Ostatnie 30 dni, podział według poziomu przy obecnych progach.">
        {trends.resource.phase === "loading" && <Skeleton height={190} />}
        {trends.resource.phase === "error" && <ErrorState compact message={trends.resource.error} onRetry={trends.reload} />}
        {trends.resource.phase === "ready" && (trends.resource.data.days.length > 0
          ? <TrendChart days={trends.resource.data.days} thresholds={thresholds} module={filters.module} />
          : <EmptyState compact title="Brak danych do wykresu" text="Trend pojawi się po pierwszych wykryciach." />)}
      </Panel>

      <Panel title="Sprawy" hint={incidents.phase === "ready" ? `Pokazano ${visible.length} z ${incidents.items.length}` : undefined} flush
        actions={null}>
        <div className="panel__toolbar">
          <Filters filters={filters} onChange={(next) => setParams(filtersToSearch(next), { replace: true })} />
        </div>
        {incidents.phase === "loading" && (
          <div className="table-skeleton" aria-busy="true" aria-label="Wczytywanie spraw">
            {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} height={44} />)}
          </div>
        )}
        {incidents.phase === "error" && <ErrorState message={incidents.error ?? "Nieznany błąd."} onRetry={incidents.reload} />}
        {incidents.phase === "ready" && incidents.error && (
          <p className="inline-warning" role="status">Nie udało się odświeżyć listy: {incidents.error}</p>
        )}
        {incidents.phase === "ready" && incidents.items.length === 0 && (
          <EmptyState
            title="Kolejka jest pusta"
            text="Nie wykryto jeszcze żadnych spraw. Zeskanuj adres URL albo uruchom próbkę demo z menu u góry."
          />
        )}
        {incidents.phase === "ready" && incidents.items.length > 0 && visible.length === 0 && (
          <EmptyState
            icon={<SearchX />}
            title="Żadna sprawa nie pasuje do filtrów"
            text="Zmień kryteria wyszukiwania albo wyczyść filtry."
            action={isFiltered ? <Button onClick={() => setParams(new URLSearchParams(), { replace: true })}>Wyczyść filtry</Button> : undefined}
          />
        )}
        {incidents.phase === "ready" && visible.length > 0 && (
          <IncidentTable items={visible} thresholds={thresholds} fresh={incidents.fresh} alertIds={alertIds} />
        )}
      </Panel>
      <p className="muted legend-note">
        Poziomy: {LEVELS.map((l) => LEVEL_LABEL[l]).join(" · ")}. Wynik ryzyka to surowy wynik silnika AI; poziom jest wyliczany po stronie przeglądarki.
      </p>
    </div>
  );
}
