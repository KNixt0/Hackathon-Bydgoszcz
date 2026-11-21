import { CircleAlert, Save } from "lucide-react";
import { useMemo, useState } from "react";
import { api } from "../api/endpoints";
import { ConfusionMatrix } from "../components/calibration/ConfusionMatrix";
import { MetricsRow } from "../components/calibration/MetricsRow";
import { MisclassifiedList } from "../components/calibration/MisclassifiedList";
import { PrCurve } from "../components/calibration/PrCurve";
import { ScoreHistogram } from "../components/calibration/ScoreHistogram";
import { ThresholdControl } from "../components/calibration/ThresholdControl";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { LevelBadge } from "../components/ui/LevelBadge";
import { Panel } from "../components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { bestF1Threshold, histogram, metricsAt, metricsCurve, misclassifiedAt } from "../domain/calibration";
import { formatDateTime, formatScore } from "../domain/format";
import { countLevels, LEVELS } from "../domain/levels";
import { useUser } from "../hooks/useAuth";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import { useUi } from "../hooks/useUi";
import type { CalibrationItem } from "../types/api";

const EMPTY: CalibrationItem[] = [];

export function CalibrationPage() {
  const { thresholds, setThresholds, reset, isGlobal, global, globalThresholds, saveGlobal } = useThresholds();
  const user = useUser();
  const { notify } = useUi();
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const supervisor = user.role === "SUPERVISOR";
  const incidents = useIncidents();
  const calibration = useResource((signal) => api.calibration(signal), "calibration");
  const items = calibration.resource.phase === "ready" ? calibration.resource.data.items ?? EMPTY : EMPTY;

  // Threshold-independent work is done once per data set; only cheap lookups rerun while dragging.
  const curve = useMemo(() => metricsCurve(items), [items]);
  const bins = useMemo(() => histogram(items), [items]);
  const suggested = useMemo(() => bestF1Threshold(items), [items]);
  const metrics = useMemo(() => metricsAt(items, thresholds.orange), [items, thresholds.orange]);
  const wrong = useMemo(() => misclassifiedAt(items, thresholds.orange), [items, thresholds.orange]);
  const analystLabelled = useMemo(() => items.filter((i) => i.label_source === "analyst").length, [items]);

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    const failure = await saveGlobal();
    setSaving(false);
    if (failure) setSaveError(failure);
    else notify("success", `Zapisano progi globalne: flagowanie od ${thresholds.orange}, krytyczne od ${thresholds.red}. Obowiązują wszystkich analityków i alert na żywo.`);
  };

  const queueCounts = useMemo(() => countLevels(incidents.items.map((i) => i.risk_score), thresholds), [incidents.items, thresholds]);

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Kalibracja progów</h1>
          <p className="page__sub">Progi działają na surowym wyniku ryzyka 0–100 z silnika. Przesunięcie suwaka to podgląd: działa od razu w kolejce, licznikach i na wykresach, ale tylko w tej przeglądarce. Progi globalne zapisuje kierownik.</p>
        </div>
      </div>

      <Panel title="Progi ryzyka" hint="Przeciągnij suwak, użyj strzałek na klawiaturze albo wpisz wartość">
        <div className="thr">
          <div className="thr__global" data-testid="global-thresholds">
            <span>
              Progi globalne: flagowanie od <strong className="num">{globalThresholds.orange}</strong>, krytyczne od <strong className="num">{globalThresholds.red}</strong>
              {global?.updated_by
                ? <span className="muted">. Ustawił {global.updated_by}, {formatDateTime(global.updated_at)}.</span>
                : <span className="muted">. Wartości domyślne, jeszcze nie zmieniane.</span>}
            </span>
            {!isGlobal && <span className="thr__preview">Podgląd lokalny: {thresholds.orange} / {thresholds.red}</span>}
            {supervisor ? (
              <Button variant="primary" onClick={() => void save()} disabled={isGlobal || saving}>
                <Save aria-hidden="true" />{saving ? "Zapisywanie…" : "Zapisz jako progi globalne"}
              </Button>
            ) : (
              <span className="muted thr__note">Progi globalne zmienia kierownik.</span>
            )}
          </div>
          {saveError && <p className="form-error" role="alert" style={{ gridColumn: "1 / -1" }}><CircleAlert aria-hidden="true" />Nie zapisano progów. {saveError}</p>}
          <ThresholdControl thresholds={thresholds} onChange={setThresholds} onReset={reset} isGlobal={isGlobal} globalThresholds={globalThresholds} suggested={suggested} />
          <div className="thr__effect" role="status" aria-label="Kolejka przy tych progach">
            <span className="muted">Kolejka przy tych progach:</span>
            <span className="thr__effect-item">
              <strong className="num" data-testid="queue-flagged">{queueCounts.red + queueCounts.orange}</strong>
              <span>oflagowane</span>
            </span>
            {LEVELS.map((level) => (
              <span key={level} className="thr__effect-item">
                <strong className="num" data-testid={`queue-${level}`}>{queueCounts[level]}</strong>
                <LevelBadge level={level} />
              </span>
            ))}
          </div>
          <p className="thr__explain">
            Sprawa jest oflagowana, gdy jej wynik ryzyka jest co najmniej równy progowi flagowania (poziom „do weryfikacji” lub „krytyczne”): obniżenie progu daje mniej przeoczonych naruszeń, ale więcej fałszywych alarmów, a podniesienie działa odwrotnie. Próg krytyczny rozdziela tylko sprawy „do weryfikacji” od „krytycznych” i nie wpływa na macierz pomyłek.
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
          <EmptyState title="Brak oznaczonych spraw" text="Miary jakości wymagają spraw z etykietą „naruszenie” lub „zgodne”. Zaimportuj próbki z etykietami albo oceń trafność alarmów w sprawach." />
        </div>
      )}
      {calibration.resource.phase === "ready" && items.length > 0 && (
        <>
          <div className="calib-grid">
            <div className="calib-col">
              <Panel title="Jakość przy progu flagowania" hint={`Próg ${thresholds.orange} · ${items.length} oznaczonych spraw${analystLabelled ? `, w tym ${analystLabelled} oznaczonych przez analityków` : ""}`} flush>
                <MetricsRow metrics={metrics} />
              </Panel>
              <Panel title="Macierz pomyłek" hint="Alarm = wynik ryzyka co najmniej równy progowi flagowania">
                <ConfusionMatrix confusion={metrics} />
              </Panel>
            </div>
            <div className="calib-col">
              <Panel title="Rozkład wyników ryzyka" hint="Liczba oznaczonych spraw w przedziałach wyniku, według stanu faktycznego" flush>
                <ScoreHistogram bins={bins} thresholds={thresholds} />
              </Panel>
              <Panel title="Precyzja i czułość a próg" hint="Wartości miar dla każdego możliwego progu flagowania" flush>
                <PrCurve curve={curve} threshold={thresholds.orange} />
              </Panel>
            </div>
          </div>
          <Panel title="Sprawy błędnie sklasyfikowane przy tym progu" hint="Lista zmienia się razem z progiem flagowania" flush>
            <MisclassifiedList data={wrong} />
          </Panel>
          {analystLabelled > 0 && (
            <Panel title="Oznaczone przez analityków" hint="Sprawy, którym analityk nadał ocenę trafności w postępowaniu; ta ocena zastępuje etykietę próbki" flush>
              <ul className="miss__list" data-testid="analyst-labelled">
                {items.filter((i) => i.label_source === "analyst").map((it) => (
                  <li key={it.id} className="miss__item">
                    <span className="miss__score num" title="Surowy wynik ryzyka">{formatScore(it.risk_score)}</span>
                    <Link to={`/sprawy/${it.id}`} className="miss__name truncate" title={it.title}>{it.title}</Link>
                    <Badge tone={it.ground_truth === "violation" ? "red" : "green"}>{it.ground_truth === "violation" ? "trafny alarm" : "fałszywy alarm"}</Badge>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}
