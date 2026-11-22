import { useId, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatDate, formatDayMonth } from "../../domain/format";
import { LEVEL_LABEL } from "../../domain/labels";
import { LEVELS } from "../../domain/levels";
import type { TrendRow } from "../../domain/trends";
import type { RiskLevel } from "../../types/incident";
import { ChartTip } from "../ui/ChartTip";

const COLOR: Record<RiskLevel, string> = { green: "var(--m-grn)", orange: "var(--m-amb)", red: "var(--m-red)" };
const STACK: RiskLevel[] = ["green", "orange", "red"];

/** New cases per day, stacked by the level at the current thresholds; 120px, square bars, a text legend and a data table. */
export function TrendStrip({ rows, hourly = false }: { rows: TrendRow[]; hourly?: boolean }) {
  const [table, setTable] = useState(false);
  // Below 640 px the strip collapses to the sentence and the table link (the chart is not mounted at all).
  const tick = (value: string) => hourly ? new Intl.DateTimeFormat("pl-PL", { timeZone: "Europe/Warsaw", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : formatDayMonth(value);
  const tableId = useId();
  const max = Math.max(1, ...rows.map((r) => r.red + r.orange + r.green));
  return (
    <>
      {<div className="trend" data-testid="trend-chart" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 900, height: 120 }}>
          <BarChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickFormatter={tick} tickLine={false} axisLine={{ stroke: "var(--ink-2)" }} minTickGap={24} height={22} />
            <YAxis allowDecimals={false} width={28} tickLine={false} axisLine={false} tickCount={3} domain={[0, Math.ceil(max / 2) * 2]} />
            <Tooltip cursor={{ fill: "rgba(22,22,22,0.06)" }} content={<ChartTip labels={LEVEL_LABEL} hourly={hourly} />} isAnimationActive={false} />
            {STACK.map((k) => (
              <Bar key={k} dataKey={k} name={LEVEL_LABEL[k]} stackId="level" fill={COLOR[k]} isAnimationActive={false} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>}
      <div className="trend__foot">
        {<span className="legend" aria-hidden="true">
          {LEVELS.map((k) => (
            <span key={k} className="legend__item"><span className="legend__swatch" style={{ background: COLOR[k] }} />{LEVEL_LABEL[k]}</span>
          ))}
        </span>}
        <button type="button" className="linkbtn" aria-expanded={table} aria-controls={tableId} onClick={() => setTable((v) => !v)}>
          {table ? "Ukryj tabelę" : "Pokaż dane jako tabelę"}
        </button>
      </div>
      <div id={tableId} className={table ? "trend__table table-wrap" : "sr-only"}>
        <table className="rt">
          <caption className="sr-only">Nowe sprawy dziennie według poziomu przy obecnych progach</caption>
          <thead>
            <tr><th scope="col">Dzień</th>{LEVELS.map((k) => <th key={k} scope="col" className="r">{LEVEL_LABEL[k]}</th>)}<th scope="col" className="r">Razem</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.date}>
                <td>{hourly ? `${formatDate(r.date)} ${tick(r.date)}` : formatDate(r.date)}</td>
                {LEVELS.map((k) => <td key={k} className="r num">{r[k]}</td>)}
                <td className="r num">{r.red + r.orange + r.green}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
