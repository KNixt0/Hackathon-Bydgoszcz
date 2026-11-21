import { TriangleAlert } from "lucide-react";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart } from "recharts";
import { formatDate, formatPercent, formatShortDay } from "../../domain/format";
import { ANOMALY_LABEL, SEVERITY_LABEL } from "../../domain/labels";
import type { Forensics } from "../../types/incident";
import { Badge } from "../ui/Badge";

const tip = { borderRadius: 6, border: "1px solid var(--line)", fontSize: 12.5 };

export function ForensicsView({ data }: { data: Forensics }) {
  const timeline = data.opinion_timeline.map((d) => ({ ...d, share: Math.round(d.new_account_share * 100) }));
  return (
    <div className="stack">
      <div className="metrics metrics--3">
        <div className="metric"><span className="metric__label">Analizowane konta</span><span className="metric__value num">{data.accounts.total}</span><span className="metric__hint">autorzy opinii</span></div>
        <div className="metric"><span className="metric__label">Konta młodsze niż 14 dni</span><span className="metric__value num">{formatPercent(data.accounts.share_younger_14d)}</span><span className="metric__hint">w chwili publikacji opinii</span></div>
        <div className="metric"><span className="metric__label">Wykryte anomalie</span><span className="metric__value num">{data.anomalies.length}</span><span className="metric__hint">wzorce nienaturalne</span></div>
      </div>

      {data.anomalies.length > 0 && (
        <ul className="anomalies">
          {data.anomalies.map((a, i) => (
            <li key={i} className={`anomaly anomaly--${a.severity}`}>
              <TriangleAlert aria-hidden="true" />
              <div>
                <strong>{ANOMALY_LABEL[a.type]}</strong> <Badge tone={a.severity === "high" ? "red" : a.severity === "medium" ? "orange" : "neutral"}>{SEVERITY_LABEL[a.severity]}</Badge>
                <p>{a.description}</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="grid-2">
        <section aria-label="Opinie w czasie">
          <h3 className="subhead">Opinie w czasie</h3>
          <div className="chart" role="img" aria-label="Liczba opinii dziennie i udział świeżych kont">
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={timeline} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickFormatter={formatShortDay} tickLine={false} axisLine={false} minTickGap={24} />
                <YAxis yAxisId="l" allowDecimals={false} tickLine={false} axisLine={false} />
                <YAxis yAxisId="r" orientation="right" domain={[0, 100]} unit="%" tickLine={false} axisLine={false} />
                <Tooltip labelFormatter={(v) => formatDate(String(v))} contentStyle={tip} />
                <Legend iconType="circle" iconSize={8} />
                <Bar yAxisId="l" dataKey="count" name="Liczba opinii" fill="var(--accent)" isAnimationActive={false} />
                <Line yAxisId="r" dataKey="share" name="Udział nowych kont (%)" stroke="var(--red)" strokeWidth={2} dot={false} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section aria-label="Wiek kont">
          <h3 className="subhead">Wiek kont w chwili opinii</h3>
          <div className="chart" role="img" aria-label="Rozkład wieku kont autorów">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data.accounts.age_buckets} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="bucket" tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: "rgba(27,42,92,0.06)" }} contentStyle={tip} />
                <Bar dataKey="count" name="Konta" fill="var(--accent)" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <div className="grid-2">
        <section aria-label="Pochodzenie kont">
          <h3 className="subhead">Kraj pochodzenia kont</h3>
          <ul className="bars">
            {data.accounts.origins.map((o) => (
              <li key={o.country}>
                <span>{o.country}</span>
                <span className="bars__track"><span style={{ width: `${(o.count / Math.max(1, data.accounts.total)) * 100}%` }} /></span>
                <span className="num">{o.count}</span>
              </li>
            ))}
          </ul>
        </section>
        <section aria-label="Wzorce nazw">
          <h3 className="subhead">Powtarzalne wzorce nazw kont</h3>
          {data.accounts.name_patterns.length === 0 ? <p className="muted">Nie wykryto.</p> : (
            <ul className="patterns">
              {data.accounts.name_patterns.map((p) => (
                <li key={p.pattern}><code>{p.pattern}</code> <span className="num">×{p.count}</span><span className="muted"> np. {p.examples.slice(0, 3).join(", ")}</span></li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {data.sample_accounts.length > 0 && (
        <section aria-label="Przykładowe konta">
          <h3 className="subhead">Przykładowe konta</h3>
          <div className="table-wrap">
            <table className="table table--static">
              <thead><tr><th scope="col">Konto</th><th scope="col">Założone</th><th scope="col">Kraj</th><th scope="col">Treść opinii</th></tr></thead>
              <tbody>
                {data.sample_accounts.map((a) => (
                  <tr key={a.handle}><td>{a.handle}</td><td className="nowrap">{formatDate(a.created_at)}</td><td>{a.country}</td><td>{a.text}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
