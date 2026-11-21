import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HistogramBin } from "../../domain/calibration";
import type { Thresholds } from "../../domain/levels";
import { ChartTip } from "../ui/ChartTip";

const LABELS = { violation: "Naruszenia", ok: "Zgodne" };

/** Distribution of risk scores split by the analysts' verdict; the threshold lines move with the slider. */
export function ScoreHistogram({ bins, thresholds }: { bins: HistogramBin[]; thresholds: Thresholds }) {
  const data = bins.map((b) => ({ ...b, mid: (b.from + b.to) / 2 }));
  return (
    <>
      <div className="chart" data-testid="score-histogram" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 600, height: 220 }}>
          <BarChart data={data} margin={{ top: 18, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="mid" type="number" domain={[0, 100]} ticks={[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]} tickLine={false} axisLine={{ stroke: "var(--ink-2)" }} />
            <YAxis allowDecimals={false} width={30} tickLine={false} axisLine={false} tickCount={3} />
            <Tooltip
              cursor={{ fill: "rgba(22,22,22,0.06)" }} isAnimationActive={false}
              content={({ active, payload }) => {
                const bin = payload?.[0]?.payload as HistogramBin | undefined;
                return <ChartTip active={active} payload={payload} label={bin ? `Ryzyko ${bin.label}` : ""} labels={LABELS} />;
              }}
            />
            <Bar dataKey="ok" stackId="gt" fill="var(--u-off)" isAnimationActive={false} barSize={28} />
            <Bar dataKey="violation" stackId="gt" fill="var(--accent)" isAnimationActive={false} barSize={28} />
            <ReferenceLine x={thresholds.orange} stroke="var(--ink)" strokeWidth={2} label={{ value: `${thresholds.orange}`, position: "top", fill: "var(--ink)", fontSize: 12, fontWeight: 700 }} />
            <ReferenceLine x={thresholds.red} stroke="var(--ink-2)" strokeWidth={1} strokeDasharray="4 3" label={{ value: `${thresholds.red}`, position: "top", fill: "var(--ink)", fontSize: 12, fontWeight: 700 }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="legend">
        <span className="legend__item"><span className="legend__swatch" style={{ background: "var(--accent)" }} />Naruszenia</span>
        <span className="legend__item"><span className="legend__swatch" style={{ background: "var(--u-off)" }} />Sprawy zgodne</span>
        <span className="legend__item"><span className="legend__swatch legend__swatch--line" style={{ background: "var(--ink)" }} />Próg oznaczenia ({thresholds.orange})</span>
        <span className="legend__item"><span className="legend__swatch legend__swatch--dash" style={{ borderTopWidth: 1, borderColor: "var(--ink-2)" }} />Próg krytyczny ({thresholds.red})</span>
      </div>
    </>
  );
}
