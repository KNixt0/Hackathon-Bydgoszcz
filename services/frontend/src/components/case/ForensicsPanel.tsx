import { MessagesSquare, TriangleAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatPercent, formatShortDay } from "../../domain/format";
import { ANOMALY_LABEL } from "../../domain/labels";
import type { Forensics } from "../../types/incident";
import { ChartTip } from "../queue/TrendChart";
import { EmptyState } from "../ui/States";

const TIMELINE_LABELS = { count: "Liczba opinii", share: "Udział nowych kont (%)" };
const COUNT_LABELS = { count: "Liczba kont" };

function MiniBars({ data, xKey, testId }: { data: Record<string, string | number>[]; xKey: string; testId: string }) {
  return (
    <div className="chart" data-testid={testId}>
      <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 320, height: 180 }}>
        <BarChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: 0 }} accessibilityLayer>
          <CartesianGrid vertical={false} />
          <XAxis dataKey={xKey} tickLine={false} axisLine={{ stroke: "var(--line-strong)" }} interval={0} />
          <YAxis allowDecimals={false} width={32} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: "rgba(20,24,33,0.05)" }} isAnimationActive={false} content={<ChartTip labels={COUNT_LABELS} />} />
          <Bar dataKey="count" fill="var(--accent)" isAnimationActive={false} maxBarSize={34} radius={[2, 2, 0, 0]} />
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
        icon={<MessagesSquare />}
        title="Brak analizy opinii i kont"
        text="Do tego materiału nie dołączono komentarzy ani opinii, więc silnik nie badał wieku, pochodzenia i wzorców nazw kont."
      />
    );
  }
  const timeline = forensics.opinion_timeline.map((p) => ({ ...p, share: Math.round(p.new_account_share * 100) }));
  const { accounts } = forensics;
  return (
    <div style={{ padding: 16, display: "grid", gap: 16 }}>
      <div className="stat-row">
        <div><p className="stat__value num">{accounts.total.toLocaleString("pl-PL")}</p><p className="stat__label">kont komentujących</p></div>
        <div><p className="stat__value num">{formatPercent(accounts.share_younger_14d)}</p><p className="stat__label">kont młodszych niż 14 dni</p></div>
        <div><p className="stat__value num">{forensics.anomalies.length}</p><p className="stat__label">wykrytych anomalii</p></div>
      </div>

      {forensics.anomalies.length > 0 && (
        <ul className="anomalies" aria-label="Anomalie">
          {forensics.anomalies.map((a, i) => (
            <li key={i} className={`anomaly anomaly--${a.severity}`}>
              <TriangleAlert aria-hidden="true" />
              <span><span className="anomaly__type">{ANOMALY_LABEL[a.type] ?? a.type}.</span> {a.description}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="subcard">
        <p className="subhead">Opinie w czasie</p>
        {timeline.length === 0 ? (
          <p className="muted">Brak danych o rozkładzie opinii w czasie.</p>
        ) : (
          <>
            <div className="chart" style={{ height: 210 }} data-testid="opinion-timeline">
              <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 600, height: 210 }}>
                <ComposedChart data={timeline} margin={{ top: 6, right: 0, bottom: 0, left: 0 }} accessibilityLayer>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="date" tickFormatter={formatShortDay} tickLine={false} axisLine={{ stroke: "var(--line-strong)" }} minTickGap={20} />
                  <YAxis yAxisId="count" allowDecimals={false} width={32} tickLine={false} axisLine={false} />
                  <YAxis yAxisId="share" orientation="right" domain={[0, 100]} width={40} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v}%`} />
                  <Tooltip cursor={{ fill: "rgba(20,24,33,0.05)" }} isAnimationActive={false} content={<ChartTip labels={TIMELINE_LABELS} />} />
                  <Bar yAxisId="count" dataKey="count" fill="var(--accent)" isAnimationActive={false} maxBarSize={22} radius={[2, 2, 0, 0]} />
                  <Line yAxisId="share" dataKey="share" stroke="var(--red)" strokeWidth={2} dot={{ r: 2.5, fill: "var(--red)", strokeWidth: 0 }} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="legend" style={{ padding: "8px 0 0" }}>
              <span className="legend__item"><span className="legend__swatch" style={{ background: "var(--accent)" }} />Liczba opinii (lewa oś)</span>
              <span className="legend__item"><span className="legend__swatch legend__swatch--line" style={{ background: "var(--red)" }} />Udział nowych kont (prawa oś)</span>
            </div>
          </>
        )}
      </div>

      <div className="subgrid">
        <div className="subcard">
          <p className="subhead">Wiek kont</p>
          {accounts.age_buckets.length ? <MiniBars data={accounts.age_buckets} xKey="bucket" testId="age-buckets" /> : <p className="muted">Brak danych.</p>}
        </div>
        <div className="subcard">
          <p className="subhead">Pochodzenie kont</p>
          {accounts.origins.length ? <MiniBars data={accounts.origins} xKey="country" testId="origins" /> : <p className="muted">Brak danych.</p>}
        </div>
        <div className="subcard">
          <p className="subhead">Wzorce nazw kont</p>
          {accounts.name_patterns.length === 0 ? <p className="muted">Nie wykryto powtarzalnych wzorców.</p> : (
            <table className="plain-table">
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
