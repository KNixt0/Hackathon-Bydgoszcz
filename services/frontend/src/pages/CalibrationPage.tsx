import { useMemo } from "react";
import { api } from "../api/endpoints";
import { ConfusionMatrix } from "../components/calibration/ConfusionMatrix";
import { MetricsRow } from "../components/calibration/MetricsRow";
import { MisclassifiedList } from "../components/calibration/MisclassifiedList";
import { PrCurve } from "../components/calibration/PrCurve";
import { ScoreHistogram } from "../components/calibration/ScoreHistogram";
import { ThresholdControl } from "../components/calibration/ThresholdControl";
import { LevelBadge } from "../components/ui/LevelBadge";
import { Panel } from "../components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { bestF1Threshold, histogram, metricsAt, metricsCurve, misclassifiedAt } from "../domain/calibration";
import { countLevels, LEVELS } from "../domain/levels";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import type { CalibrationItem } from "../types/api";

const EMPTY: CalibrationItem[] = [];

export function CalibrationPage() {
  const { thresholds, setThresholds, reset, isDefault } = useThresholds();
  const incidents = useIncidents();
  const calibration = useResource((signal) => api.calibration(signal), "calibration");
  const items = calibration.resource.phase === "ready" ? calibration.resource.data.items ?? EMPTY : EMPTY;

  // Threshold-independent work is done once per data set; only cheap lookups rerun while dragging.
  const curve = useMemo(() => metricsCurve(items), [items]);
  const bins = useMemo(() => histogram(items), [items]);
  const suggested = useMemo(() => bestF1Threshold(items), [items]);
  const metrics = useMemo(() => metricsAt(items, thresholds.red), [items, thresholds.red]);
  const wrong = useMemo(() => misclassifiedAt(items, thresholds.red), [items, thresholds.red]);
  const queueCounts = useMemo(() => countLevels(incidents.items.map((i) => i.risk_score), thresholds), [incidents.items, thresholds]);

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Kalibracja progów</h1>
          <p className="page__sub">Progi działają na surowym wyniku ryzyka 0–100 z silnika. Zmiana obowiązuje natychmiast w kolejce, licznikach i na wykresach oraz jest zapamiętywana w tej przeglądarce.</p>
        </div>
      </div>

      <Panel title="Progi ryzyka" hint="Przeciągnij uchwyty, użyj strzałek na klawiaturze albo wpisz wartość">
        <div className="thr">
          <ThresholdControl thresholds={thresholds} onChange={setThresholds} onReset={reset} isDefault={isDefault} suggested={suggested} />
          <div className="thr__effect" role="status" aria-label="Kolejka przy tych progach">
            <span className="muted">Kolejka przy tych progach:</span>
            {LEVELS.map((level) => (
              <span key={level} className="thr__effect-item">
                <strong className="num" data-testid={`queue-${level}`}>{queueCounts[level]}</strong>
                <LevelBadge level={level} />
              </span>
            ))}
          </div>
          <p className="thr__explain">
            Obniżenie progu krytycznego oznacza więcej spraw jako krytyczne: mniej przeoczonych naruszeń, ale więcej fałszywych alarmów. Podniesienie progu działa odwrotnie.
          </p>
        </div>
      </Panel>

      {calibration.resource.phase === "loading" && (
        <div className="panel" style={{ padding: 16, display: "grid", gap: 12 }} aria-busy="true">
          <Skeleton height={28} width="40%" /><Skeleton height={180} /><Skeleton height={14} width="70%" />
        </div>
      )}
      {calibration.resource.phase === "error" && (
        <div className="panel"><ErrorState title="Nie udało się wczytać zbioru oznaczonego" message={calibration.resource.error} onRetry={calibration.reload} /></div>
      )}
      {calibration.resource.phase === "ready" && items.length === 0 && (
        <div className="panel">
          <EmptyState title="Brak oznaczonych spraw" text="Miary jakości wymagają spraw z etykietą „naruszenie” lub „zgodne”. Zaimportuj próbki z etykietami, aby skalibrować próg na danych." />
        </div>
      )}
      {calibration.resource.phase === "ready" && items.length > 0 && (
        <>
          <div className="calib-grid">
            <div className="calib-col">
              <Panel title="Jakość przy progu krytycznym" hint={`Próg ${thresholds.red} · ${items.length} oznaczonych spraw`} flush>
                <MetricsRow metrics={metrics} />
              </Panel>
              <Panel title="Macierz pomyłek" hint="Alarm = wynik ryzyka co najmniej równy progowi krytycznemu">
                <ConfusionMatrix confusion={metrics} />
              </Panel>
            </div>
            <div className="calib-col">
              <Panel title="Rozkład wyników ryzyka" hint="Liczba oznaczonych spraw w przedziałach wyniku, według stanu faktycznego" flush>
                <ScoreHistogram bins={bins} thresholds={thresholds} />
              </Panel>
              <Panel title="Precyzja i czułość a próg" hint="Wartości miar dla każdego możliwego progu krytycznego" flush>
                <PrCurve curve={curve} threshold={thresholds.red} />
              </Panel>
            </div>
          </div>
          <Panel title="Sprawy błędnie sklasyfikowane przy tym progu" hint="Lista zmienia się razem z progiem krytycznym" flush>
            <MisclassifiedList data={wrong} />
          </Panel>
        </>
      )}
    </div>
  );
}
