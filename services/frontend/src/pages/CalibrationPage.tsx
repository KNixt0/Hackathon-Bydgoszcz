import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import { ConfusionMatrix } from "../components/calibration/ConfusionMatrix";
import { CriticalThreshold } from "../components/calibration/CriticalThreshold";
import { Details } from "../components/calibration/Details";
import { LiveSentence } from "../components/calibration/LiveSentence";
import { CaseTable, MisclassifiedList } from "../components/calibration/MisclassifiedList";
import { PrCurve } from "../components/calibration/PrCurve";
import { PreviewNote } from "../components/calibration/PreviewNote";
import { RecommendedThreshold } from "../components/calibration/RecommendedThreshold";
import { ScoreHistogram } from "../components/calibration/ScoreHistogram";
import { SecondaryMeasures } from "../components/calibration/SecondaryMeasures";
import { ThresholdControl } from "../components/calibration/ThresholdControl";
import { TradeOff } from "../components/calibration/TradeOff";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { bestF1Threshold, histogram, metricsAt, metricsCurve, misclassifiedAt } from "../domain/calibration";
import { flagSentence, precisionFraction, queueOnlySentence, recallFraction } from "../domain/calibrationCopy";
import { formatDate, formatPercent } from "../domain/format";
import { countLevels } from "../domain/levels";
import { pl, plN } from "../domain/plural";
import { useUser } from "../hooks/useAuth";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import { useUi } from "../hooks/useUi";
import type { CalibrationItem } from "../types/api";

const EMPTY: CalibrationItem[] = [];
/** Below this many labelled cases the figures are flagged as unstable. */
const SMALL_SET = 30;

export function CalibrationPage() {
  const { thresholds, setThresholds, reset, isGlobal, global, globalThresholds, saveGlobal } = useThresholds();
  const user = useUser();
  const { notify } = useUi();
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const supervisor = user.role === "SUPERVISOR";
  const incidents = useIncidents();
  const calibration = useResource((signal) => api.calibration(signal), "calibration");
  const ready = calibration.resource.phase === "ready";
  const items = calibration.resource.phase === "ready" ? calibration.resource.data.items ?? EMPTY : EMPTY;
  const labelled = ready && items.length > 0;

  // Threshold-independent work is done once per data set; only cheap lookups rerun while dragging.
  const curve = useMemo(() => metricsCurve(items), [items]);
  const bins = useMemo(() => histogram(items), [items]);
  const suggested = useMemo(() => bestF1Threshold(items), [items]);
  const metrics = useMemo(() => metricsAt(items, thresholds.orange), [items, thresholds.orange]);
  const atSuggested = useMemo(() => (suggested === null ? null : metricsAt(items, suggested)), [items, suggested]);
  const wrong = useMemo(() => misclassifiedAt(items, thresholds.orange), [items, thresholds.orange]);
  const analystItems = useMemo(() => items.filter((i) => i.label_source === "analyst"), [items]);
  const queueCounts = useMemo(() => countLevels(incidents.items.map((i) => i.risk_score), thresholds), [incidents.items, thresholds]);
  const bothClasses = metrics.tp + metrics.fn > 0 && metrics.fp + metrics.tn > 0;

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    const failure = await saveGlobal();
    setSaving(false);
    if (failure) setSaveError(failure);
    else notify("success", `Zapisano progi globalne: oznaczenie od ${thresholds.orange}, krytyczne od ${thresholds.red}. Obowiązują wszystkich analityków i alert na żywo.`);
  };

  const n = items.length;
  const sentence = labelled
    ? flagSentence(thresholds.orange, metrics)
    : queueOnlySentence(thresholds.orange, queueCounts.red + queueCounts.orange, incidents.items.length);

  return (
    <div className="page calib">
      <div className="page__head">
        <h1 className="page__title">Kalibracja progów</h1>
        <p className="page__sub">
          Wybierz, od jakiego wyniku ryzyka system oznacza sprawę do kolejki.
          {labelled && <> Sprawdzamy to na {n} {pl(n, "sprawie", "sprawach", "sprawach")}, które analitycy już ocenili.</>}
        </p>
        {labelled && n < SMALL_SET && (
          <p className="page__note" data-testid="small-set">Zbiór jest mały ({plN(n, "sprawa", "sprawy", "spraw")}). Wyniki mogą się zmienić po ocenie kolejnych spraw.</p>
        )}
      </div>

      <PreviewNote
        thresholds={thresholds} globalThresholds={globalThresholds} global={global} isGlobal={isGlobal}
        supervisor={supervisor} saving={saving} saveError={saveError}
        onSave={() => void save()} onReset={() => { setSaveError(null); reset(); }}
      />

      <section className="panel calib__panel" aria-label="Próg oznaczenia i jego skutki">
        <div className="calib__sec">
          <ThresholdControl value={thresholds.orange} onChange={(orange) => setThresholds({ orange })} />
          {calibration.resource.phase === "loading" ? (
            <div aria-busy="true" style={{ display: "grid", gap: 8 }}><Skeleton height={20} width="90%" /><Skeleton height={20} width="70%" /></div>
          ) : calibration.resource.phase === "error" ? null : (
            <LiveSentence segments={sentence} />
          )}
        </div>

        {calibration.resource.phase === "loading" && (
          <div className="calib__sec" aria-hidden="true" style={{ display: "grid", gap: 12 }}>
            <Skeleton height={20} width="40%" /><Skeleton height={28} width="30%" /><Skeleton height={16} />
          </div>
        )}
        {calibration.resource.phase === "error" && (
          <div className="calib__sec">
            <ErrorState compact title="Nie udało się wczytać zbioru oznaczonego" message={calibration.resource.error} onRetry={calibration.reload} />
          </div>
        )}
        {ready && !labelled && (
          <div className="calib__sec">
            <EmptyState
              compact title="Brak ocenionych spraw"
              text="Żeby pokazać, ile fałszywych alarmów i przeoczonych naruszeń daje próg, system potrzebuje spraw ocenionych jako „naruszenie” lub „zgodne”. Oceń trafność alarmów w sprawach albo zaimportuj próbki z etykietami."
              action={<Link to="/">Przejdź do kolejki</Link>}
            />
          </div>
        )}
        {labelled && (
          <>
            <div className="calib__sec"><TradeOff confusion={metrics} /></div>
            <div className="calib__sec"><SecondaryMeasures metrics={metrics} /></div>
            {suggested !== null && atSuggested && bothClasses && (
              <div className="calib__sec">
                <RecommendedThreshold suggested={suggested} current={thresholds.orange} metrics={atSuggested} onApply={() => setThresholds({ orange: suggested })} />
              </div>
            )}
          </>
        )}

        <div className="calib__sec">
          <CriticalThreshold thresholds={thresholds} onChange={(red) => setThresholds({ red })} counts={queueCounts} />
        </div>
        {!supervisor && (
          <p className="calib__foot" data-testid="global-owner">
            {global?.updated_by
              ? `Progi globalne ustawił ${global.updated_by}, ${formatDate(global.updated_at)}. Zmienia je kierownik.`
              : "Progi globalne mają wartości domyślne. Zmienia je kierownik."}
          </p>
        )}
      </section>

      {labelled && (
        <Details summary="Szczegóły dla analityka" hint="macierz pomyłek, miary, rozkład wyników, krzywa, lista spraw">
          {() => (
            <>
              <section className="disc__sec" aria-labelledby="cm-h">
                <h2 className="section-title" id="cm-h">Macierz pomyłek</h2>
                <ConfusionMatrix confusion={metrics} threshold={thresholds.orange} />
              </section>
              <section className="disc__sec" aria-labelledby="mtab-h">
                <h2 className="section-title" id="mtab-h">Miary</h2>
                <div className="table-wrap">
                  <table className="rt mtab">
                    <caption className="sr-only">Miary jakości przy progu {thresholds.orange}</caption>
                    <thead><tr><th scope="col">Miara</th><th scope="col" className="r">Wartość</th><th scope="col">Z czego wynika</th></tr></thead>
                    <tbody>
                      <tr><td>Trafność alertów (precyzja, precision)</td><td className="r v num">{formatPercent(metrics.precision)}</td><td>{precisionFraction(metrics.tp, metrics.tp + metrics.fp)}</td></tr>
                      <tr><td>Wykrywalność naruszeń (czułość, recall)</td><td className="r v num">{formatPercent(metrics.recall)}</td><td>{recallFraction(metrics.tp, metrics.tp + metrics.fn)}</td></tr>
                      <tr><td>F1</td><td className="r v num" data-testid="metric-f1">{formatPercent(metrics.f1)}</td><td>średnia harmoniczna obu miar; według niej wyznaczamy zalecany próg</td></tr>
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="disc__sec" aria-labelledby="hist-h">
                <h2 className="section-title" id="hist-h">Rozkład wyników ryzyka</h2>
                <p className="field__hint">Liczba ocenionych spraw w przedziałach wyniku, według oceny analityków.</p>
                <ScoreHistogram bins={bins} thresholds={thresholds} />
              </section>
              <section className="disc__sec" aria-labelledby="pr-h">
                <h2 className="section-title" id="pr-h">Precyzja i czułość a próg</h2>
                <p className="field__hint">Wartości obu miar dla każdego możliwego progu oznaczenia.</p>
                <PrCurve curve={curve} threshold={thresholds.orange} />
              </section>
              <section className="disc__sec" aria-labelledby="miss-h">
                <h2 className="section-title" id="miss-h">Sprawy błędnie sklasyfikowane przy tym progu</h2>
                <MisclassifiedList data={wrong} />
              </section>
              {analystItems.length > 0 && (
                <section className="disc__sec" aria-labelledby="al-h">
                  <h2 className="section-title" id="al-h">Oznaczone przez analityków</h2>
                  <p className="field__hint">
                    W zbiorze {plN(n, "sprawa", "sprawy", "spraw")}, w tym {analystItems.length} {pl(analystItems.length, "oznaczona", "oznaczone", "oznaczonych")} przez analityków.
                    Ocena analityka w sprawie zastępuje etykietę próbki.
                  </p>
                  <div data-testid="analyst-labelled" className="miss__scroll">
                    <CaseTable
                      items={analystItems} caption="Sprawy oznaczone przez analityków"
                      extra={(it) => (it.ground_truth === "violation" ? "trafny alarm" : "fałszywy alarm")}
                    />
                  </div>
                </section>
              )}
            </>
          )}
        </Details>
      )}
    </div>
  );
}
