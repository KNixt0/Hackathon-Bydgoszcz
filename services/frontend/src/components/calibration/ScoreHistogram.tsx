import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HistogramBin } from "../../domain/calibration";
import type { Thresholds } from "../../domain/levels";
import { ChartTip } from "../queue/TrendChart";

const LABELS = { violation: "Faktyczne naruszenia", ok: "Faktycznie zgodne" };

interface Props {
  bins: HistogramBin[];
  thresholds: Thresholds;
}

/** Distribution of raw risk scores split by ground truth; the threshold lines move with the slider. */
export function ScoreHistogram({ bins, thresholds }: Props) {
  const data = bins.map((b) => ({ ...b, mid: (b.from + b.to) / 2 }));
  return (
    <>
      <div className="chart" data-testid="score-histogram">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 600, height: 220 }}>
          <BarChart data={data} margin={{ top: 18, right: 12, bottom: 0, left: 0 }} accessibilityLayer>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="mid" type="number" domain={[0, 100]} ticks={[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]} tickLine={false} axisLine={{ stroke: "var(--line-strong)" }} />
            <YAxis allowDecimals={false} width={30} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: "rgba(20,24,33,0.05)" }} isAnimationActive={false}
              content={({ active, payload }) => {
                const bin = payload?.[0]?.payload as HistogramBin | undefined;
                return <ChartTip active={active} payload={payload} label={bin ? `Ryzyko ${bin.label}` : ""} labels={LABELS} />;
              }}
            />
            <Bar dataKey="ok" stackId="gt" fill="var(--line-strong)" isAnimationActive={false} barSize={26} />
            <Bar dataKey="violation" stackId="gt" fill="var(--accent)" isAnimationActive={false} barSize={26} />
            <ReferenceLine x={thresholds.orange} stroke="var(--orange)" strokeWidth={2} label={{ value: `${thresholds.orange}`, position: "top", fill: "var(--orange-ink)", fontSize: 12, fontWeight: 600 }} />
            <ReferenceLine x={thresholds.red} stroke="var(--red)" strokeWidth={2} strokeDasharray="4 3" label={{ value: `${thresholds.red}`, position: "top", fill: "var(--red-ink)", fontSize: 12, fontWeight: 600 }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="legend">
        <span className="legend__item"><span className="legend__swatch" style={{ background: "var(--accent)" }} />Faktyczne naruszenia</span>
        <span className="legend__item"><span className="legend__swatch" style={{ background: "var(--line-strong)" }} />Faktycznie zgodne</span>
        <span className="legend__item"><span className="legend__swatch legend__swatch--dash" style={{ borderColor: "var(--red)" }} />Próg krytyczny</span>
        <span className="legend__item"><span className="legend__swatch legend__swatch--line" style={{ background: "var(--orange)" }} />Próg flagowania</span>
      </div>
    </>
  );
}
