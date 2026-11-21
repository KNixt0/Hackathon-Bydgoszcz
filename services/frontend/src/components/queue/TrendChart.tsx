import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatShortDay } from "../../domain/format";
import { LEVEL_LABEL } from "../../domain/labels";
import type { Thresholds } from "../../domain/levels";
import { trendRows } from "../../domain/trends";
import type { TrendDay } from "../../types/api";
import type { ModuleId } from "../../types/incident";

interface Props {
  days: TrendDay[];
  thresholds: Thresholds;
  module: ModuleId | 0;
}

export function TrendChart({ days, thresholds, module }: Props) {
  const rows = trendRows(days, thresholds, module);
  const total = rows.reduce((n, r) => n + r.red + r.orange + r.green, 0);
  return (
    <div
      className="chart"
      role="img"
      aria-label={`Wykres liczby wykryć dziennie, łącznie ${total}, podział według poziomów przy obecnych progach`}
    >
      <ResponsiveContainer width="100%" height={190}>
        <BarChart data={rows} margin={{ top: 6, right: 8, left: -18, bottom: 0 }} barCategoryGap={3}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatShortDay} tickLine={false} axisLine={false} minTickGap={24} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
          <Tooltip
            labelFormatter={(v) => formatShortDay(String(v))}
            cursor={{ fill: "rgba(27,42,92,0.06)" }}
            contentStyle={{ borderRadius: 6, border: "1px solid var(--line)", fontSize: 12.5 }}
          />
          <Legend iconType="circle" iconSize={8} />
          <Bar dataKey="red" name={LEVEL_LABEL.red} stackId="a" fill="var(--red)" isAnimationActive={false} />
          <Bar dataKey="orange" name={LEVEL_LABEL.orange} stackId="a" fill="var(--orange)" isAnimationActive={false} />
          <Bar dataKey="green" name={LEVEL_LABEL.green} stackId="a" fill="var(--green)" isAnimationActive={false} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
