import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatShortDay } from "../../domain/format";
import { LEVEL_LABEL } from "../../domain/labels";
import type { TrendRow } from "../../domain/trends";
import type { RiskLevel } from "../../types/incident";

const SERIES: { key: RiskLevel; color: string }[] = [
  { key: "green", color: "var(--green)" },
  { key: "orange", color: "var(--orange)" },
  { key: "red", color: "var(--red)" },
];

interface TipProps {
  active?: boolean;
  label?: string | number;
  payload?: readonly { dataKey?: unknown; value?: unknown; color?: string }[];
}

export function ChartTip({ active, label, payload, labels }: TipProps & { labels: Record<string, string> }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <p className="chart-tip__title">{typeof label === "string" && /^\d{4}-\d{2}-\d{2}/.test(label) ? formatShortDay(label) : label}</p>
      {[...payload].reverse().map((p) => (
        <p key={String(p.dataKey)} className="chart-tip__row">
          <span><span className="chart-tip__swatch" style={{ background: p.color }} />{labels[String(p.dataKey)] ?? String(p.dataKey)}</span>
          <strong className="num">{typeof p.value === "number" ? Math.round(p.value * 100) / 100 : String(p.value ?? "")}</strong>
        </p>
      ))}
    </div>
  );
}

/** Incidents per day, stacked by the level derived from the current thresholds. */
export function TrendChart({ rows }: { rows: TrendRow[] }) {
  return (
    <div className="trend" data-testid="trend-chart">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 600, height: 160 }}>
        <BarChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }} barCategoryGap="22%" accessibilityLayer>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatShortDay} tickLine={false} axisLine={{ stroke: "var(--line-strong)" }} minTickGap={28} />
          <YAxis allowDecimals={false} width={30} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: "rgba(20,24,33,0.05)" }} content={<ChartTip labels={LEVEL_LABEL} />} isAnimationActive={false} />
          {SERIES.map((s) => (
            <Bar key={s.key} dataKey={s.key} name={LEVEL_LABEL[s.key]} stackId="level" fill={s.color} isAnimationActive={false} maxBarSize={18} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
