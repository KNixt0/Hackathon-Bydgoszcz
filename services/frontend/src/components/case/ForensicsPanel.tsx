import { TriangleAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatDayMonth, formatPercent } from "../../domain/format";
import { ANOMALY_LABEL } from "../../domain/labels";
import type { Forensics } from "../../types/incident";
import { ChartTip } from "../ui/ChartTip";
import { EmptyState } from "../ui/States";

const TIMELINE_LABELS = { count: "Liczba opinii", share: "Udział nowych kont (%)" };
const COUNT_LABELS = { count: "Liczba kont" };

function MiniBars({ data, xKey, testId }: { data: Record<string, string | number>[]; xKey: string; testId: string }) {
  return (
    <div className="chart" data-testid={testId}>
      <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 320, height: 180 }}>
        <BarChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: 0 }} accessibilityLayer>
          <CartesianGrid vertical={false} />
          <XAxis dataKey={xKey} tickLine={false} axisLine={{ stroke: "var(--ink-2)" }} interval={0} />
          <YAxis allowDecimals={false} width={32} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: "rgba(22,22,22,0.06)" }} isAnimationActive={false} content={<ChartTip labels={COUNT_LABELS} />} />
          <Bar dataKey="count" fill="var(--accent)" isAnimationActive={false} maxBarSize={34} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Block 2b: opinions over time and who is behind them (account age, origin, handle patterns). */
export function ForensicsPanel({ forensics }: { forensics: Forensics | null }) {
  if (!forensics) {
    return (
      <EmptyState
        title="Brak analizy opinii i kont"
        text="Do tego materiału nie dołączono komentarzy ani opinii, więc silnik nie badał wieku, pochodzenia i wzorców nazw kont."
      />
    );
  }
  const timeline = forensics.opinion_timeline.map((p) => ({ ...p, share: Math.round(p.new_account_share * 100) }));
  const { accounts } = forensics;
  return (
    <div className="vbody">
      <dl className="kv kv--compact facts">
        <dt>Konta komentujące</dt><dd className="num">{accounts.total.toLocaleString("pl-PL")}</dd>
        <dt>Konta młodsze niż 14 dni</dt><dd className="num">{formatPercent(accounts.share_younger_14d)}</dd>
        <dt>Wykryte anomalie</dt><dd className="num">{forensics.anomalies.length}</dd>
      </dl>

      {forensics.anomalies.length > 0 && (
        <ul className="anomalies" aria-label="Anomalie">
          {forensics.anomalies.map((a, i) => (
            <li key={i} className={`anomaly anomaly--${a.severity}`}>
              <TriangleAlert aria-hidden="true" />
              <span className="sr-only">Waga: {a.severity === "high" ? "wysoka" : a.severity === "medium" ? "średnia" : "niska"}. </span>
              <span><span className="anomaly__type">{ANOMALY_LABEL[a.type] ?? a.type}.</span> {a.description}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="vsub">
        <h3 className="subhead">Opinie w czasie</h3>
        {timeline.length === 0 ? (
          <p className="muted">Brak danych o rozkładzie opinii w czasie.</p>
        ) : (
          <>
            <div className="chart" style={{ height: 210 }} data-testid="opinion-timeline">
              <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 600, height: 210 }}>
                <ComposedChart data={timeline} margin={{ top: 6, right: 0, bottom: 0, left: 0 }} accessibilityLayer>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="date" tickFormatter={formatDayMonth} tickLine={false} axisLine={{ stroke: "var(--ink-2)" }} minTickGap={20} />
                  <YAxis yAxisId="count" allowDecimals={false} width={32} tickLine={false} axisLine={false} />
                  <YAxis yAxisId="share" orientation="right" domain={[0, 100]} width={40} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v}%`} />
                  <Tooltip cursor={{ fill: "rgba(22,22,22,0.06)" }} isAnimationActive={false} content={<ChartTip labels={TIMELINE_LABELS} />} />
                  <Bar yAxisId="count" dataKey="count" fill="var(--accent)" isAnimationActive={false} maxBarSize={22} />
                  <Line yAxisId="share" dataKey="share" stroke="var(--ink)" strokeWidth={2} strokeDasharray="4 3" dot={{ r: 2.5, fill: "var(--ink)", strokeWidth: 0 }} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="legend">
              <span className="legend__item"><span className="legend__swatch" style={{ background: "var(--accent)" }} />Liczba opinii (słupki, lewa oś)</span>
              <span className="legend__item"><span className="legend__swatch legend__swatch--dash" />Udział nowych kont (linia przerywana, prawa oś)</span>
            </div>
          </>
        )}
      </div>

      <div className="vgrid">
        <div className="vsub">
          <h3 className="subhead">Wiek kont</h3>
          {accounts.age_buckets.length ? <MiniBars data={accounts.age_buckets} xKey="bucket" testId="age-buckets" /> : <p className="muted">Brak danych.</p>}
        </div>
        <div className="vsub">
          <h3 className="subhead">Pochodzenie kont</h3>
          {accounts.origins.length ? <MiniBars data={accounts.origins} xKey="country" testId="origins" /> : <p className="muted">Brak danych.</p>}
        </div>
        <div className="vsub">
          <h3 className="subhead">Wzorce nazw kont</h3>
          {accounts.name_patterns.length === 0 ? <p className="muted">Nie wykryto powtarzalnych wzorców.</p> : (
            <table className="rt">
              <thead><tr><th scope="col">Wzorzec</th><th scope="col" className="r">Kont</th><th scope="col">Przykłady</th></tr></thead>
              <tbody>
                {accounts.name_patterns.map((p) => (
                  <tr key={p.pattern}>
                    <td>{p.pattern}</td>
                    <td className="r num">{p.count}</td>
                    <td className="muted">{p.examples.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
