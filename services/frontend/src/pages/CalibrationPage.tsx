import * as Slider from "@radix-ui/react-slider";
import { Target } from "lucide-react";
import { useMemo } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api/endpoints";
import { Button } from "../components/ui/Button";
import { Panel } from "../components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { Link } from "react-router-dom";
import { bestF1Threshold, histogram, metricsAt, metricsCurve, misclassifiedAt } from "../domain/calibration";
import { formatPercent, formatScore } from "../domain/format";
import { MODULE_SHORT } from "../domain/labels";
import { countLevels, DEFAULT_THRESHOLDS } from "../domain/levels";
import { useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import type { CalibrationItem } from "../types/api";

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="metric">
      <span className="metric__label">{label}</span>
      <span className="metric__value num">{value}</span>
      <span className="metric__hint">{hint}</span>
    </div>
  );
}

function MissList({ title, hint, items }: { title: string; hint: string; items: CalibrationItem[] }) {
  return (
    <Panel title={`${title} (${items.length})`} hint={hint} headingLevel={3}>
      {items.length === 0 ? (
        <p className="muted">Brak takich przypadków przy tym progu.</p>
      ) : (
        <ul className="misslist">
          {items.map((it) => (
            <li key={it.id}>
              <span className="num misslist__score">{formatScore(it.risk_score)}</span>
              <Link to={`/sprawy/${it.id}`} className="truncate">{it.title}</Link>
              <span className="muted nowrap">{MODULE_SHORT[it.module]}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export function CalibrationPage() {
  const { thresholds, setThresholds, reset, isDefault } = useThresholds();
  const incidents = useIncidents();
  const calibration = useResource((signal) => api.calibration(signal), "calibration");

  const items = useMemo(
    () => (calibration.resource.phase === "ready" ? calibration.resource.data.items : []),
    [calibration.resource],
  );
  const metrics = useMemo(() => metricsAt(items, thresholds.red), [items, thresholds.red]);
  const curve = useMemo(() => metricsCurve(items, 2).map((p) => ({
    threshold: p.threshold,
    precision: p.precision === null ? null : Math.round(p.precision * 100),
    recall: p.recall === null ? null : Math.round(p.recall * 100),
  })), [items]);
  const bins = useMemo(() => histogram(items), [items]);
  const miss = useMemo(() => misclassifiedAt(items, thresholds.red), [items, thresholds.red]);
  const best = useMemo(() => bestF1Threshold(items), [items]);
  const queueCounts = useMemo(
    () => countLevels(incidents.items.map((i) => i.risk_score), thresholds),
    [incidents.items, thresholds],
  );

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1 className="page__title">Kalibracja progów</h1>
          <p className="page__sub">
            Przesuń próg krytyczny i zobacz na oznakowanym zbiorze testowym, ilu naruszeń system nie wyłapie (FN) i ile zgodnych
            materiałów oznaczy błędnie (FP). Ten sam próg obowiązuje w kolejce spraw.
          </p>
        </div>
        <div className="page__actions">
          {best !== null && (
            <Button onClick={() => setThresholds({ red: best })} disabled={best === thresholds.red}>
              <Target aria-hidden="true" />Ustaw optymalny próg F1 ({best})
            </Button>
          )}
          <Button onClick={reset} disabled={isDefault}>Przywróć domyślne ({DEFAULT_THRESHOLDS.orange}/{DEFAULT_THRESHOLDS.red})</Button>
        </div>
      </div>

      <Panel title="Progi ryzyka" hint="Wynik ryzyka ≥ próg krytyczny oznacza sprawę krytyczną; ≥ próg weryfikacji, ale poniżej krytycznego, to sprawa do weryfikacji.">
        <div className="threshold">
          <div className="threshold__values">
            <div><span className="muted">Do weryfikacji od</span> <strong className="num threshold__n threshold__n--orange">{thresholds.orange}</strong></div>
            <div><span className="muted">Krytyczne od</span> <strong className="num threshold__n threshold__n--red">{thresholds.red}</strong></div>
          </div>
          <Slider.Root
            className="slider"
            min={0}
            max={100}
            step={1}
            minStepsBetweenThumbs={0}
            value={[thresholds.orange, thresholds.red]}
            onValueChange={([orange, red]) => {
              if (orange === undefined || red === undefined) return;
              setThresholds({ orange, red });
            }}
            aria-label="Progi ryzyka"
          >
            <Slider.Track className="slider__track">
              <span className="slider__zone slider__zone--green" style={{ width: `${thresholds.orange}%` }} />
              <span className="slider__zone slider__zone--orange" style={{ left: `${thresholds.orange}%`, width: `${thresholds.red - thresholds.orange}%` }} />
              <span className="slider__zone slider__zone--red" style={{ left: `${thresholds.red}%`, right: 0 }} />
            </Slider.Track>
            <Slider.Thumb className="slider__thumb slider__thumb--orange" aria-label="Próg do weryfikacji" />
            <Slider.Thumb className="slider__thumb slider__thumb--red" aria-label="Próg krytyczny" />
          </Slider.Root>
          <div className="slider__scale" aria-hidden="true"><span>0</span><span>25</span><span>50</span><span>75</span><span>100</span></div>
          <p className="threshold__queue">
            W kolejce przy tych progach: <strong>{queueCounts.red}</strong> krytycznych, <strong>{queueCounts.orange}</strong> do weryfikacji,{" "}
            <strong>{queueCounts.green}</strong> zgodnych.
          </p>
        </div>
      </Panel>

      {calibration.resource.phase === "loading" && <Skeleton height={260} />}
      {calibration.resource.phase === "error" && (
        <ErrorState message={calibration.resource.error} onRetry={calibration.reload} />
      )}
      {calibration.resource.phase === "ready" && items.length === 0 && (
        <EmptyState title="Brak zbioru testowego" text="Do kalibracji potrzebne są sprawy z etykietą „naruszenie” lub „zgodne”. Zaimportuj próbki z menu demo." />
      )}
      {calibration.resource.phase === "ready" && items.length > 0 && (
        <>
          <div className="metrics" role="group" aria-label={`Metryki przy progu krytycznym ${thresholds.red}`}>
            <Metric label="Precyzja" value={formatPercent(metrics.precision)} hint="Ile oflagowanych to rzeczywiste naruszenia" />
            <Metric label="Czułość (recall)" value={formatPercent(metrics.recall)} hint="Ile naruszeń system wyłapał" />
            <Metric label="F1" value={formatPercent(metrics.f1)} hint="Średnia harmoniczna precyzji i czułości" />
            <div className="confusion" role="group" aria-label="Macierz pomyłek">
              <div className="confusion__cell confusion__cell--good"><span className="num">{metrics.tp}</span><small>Trafione naruszenia (TP)</small></div>
              <div className="confusion__cell confusion__cell--bad"><span className="num">{metrics.fp}</span><small>Fałszywe alarmy (FP)</small></div>
              <div className="confusion__cell confusion__cell--bad"><span className="num">{metrics.fn}</span><small>Przeoczone naruszenia (FN)</small></div>
              <div className="confusion__cell confusion__cell--good"><span className="num">{metrics.tn}</span><small>Poprawnie zgodne (TN)</small></div>
            </div>
          </div>

          <div className="grid-2">
            <Panel title="Rozkład wyników na zbiorze testowym" hint="Linia pokazuje próg krytyczny.">
              <div className="chart" role="img" aria-label="Histogram wyników ryzyka dla naruszeń i materiałów zgodnych">
                <ResponsiveContainer width="100%" height={230}>
                  <BarChart data={bins} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: "rgba(27,42,92,0.06)" }} contentStyle={{ borderRadius: 6, border: "1px solid var(--line)", fontSize: 12.5 }} />
                    <Legend iconType="circle" iconSize={8} />
                    <Bar dataKey="violation" name="Naruszenie" stackId="s" fill="var(--red)" isAnimationActive={false} />
                    <Bar dataKey="ok" name="Zgodne" stackId="s" fill="var(--green)" isAnimationActive={false} />
                    <ReferenceLine x={bins.find((b) => thresholds.red >= b.from && thresholds.red < b.to)?.label ?? bins[bins.length - 1]?.label} stroke="var(--ink)" strokeDasharray="4 3" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Precyzja i czułość względem progu" hint="Kompromis: wyższy próg to mniej fałszywych alarmów, ale więcej przeoczeń.">
              <div className="chart" role="img" aria-label="Krzywe precyzji i czułości dla progów 0–100">
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart data={curve} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="threshold" type="number" domain={[0, 100]} tickLine={false} axisLine={false} />
                    <YAxis domain={[0, 100]} unit="%" tickLine={false} axisLine={false} />
                    <Tooltip formatter={(v) => (v === null || v === undefined ? "n/d" : `${v}%`)} labelFormatter={(v) => `Próg ${v}`}
                      contentStyle={{ borderRadius: 6, border: "1px solid var(--line)", fontSize: 12.5 }} />
                    <Legend iconType="plainline" />
                    <Line dataKey="precision" name="Precyzja" stroke="var(--accent)" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
                    <Line dataKey="recall" name="Czułość" stroke="var(--orange)" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
                    <ReferenceLine x={thresholds.red} stroke="var(--ink)" strokeDasharray="4 3" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>

          <div className="grid-2">
            <MissList title="Fałszywe alarmy" hint="Zgodne materiały oznaczone jako krytyczne" items={miss.falsePositives} />
            <MissList title="Przeoczone naruszenia" hint="Naruszenia poniżej progu krytycznego" items={miss.falseNegatives} />
          </div>
          <p className="muted legend-note">Zbiór testowy: {items.length} oznakowanych spraw (materiał syntetyczny). Metryki liczone są w przeglądarce z surowych wyników silnika AI.</p>
        </>
      )}
    </div>
  );
}
