import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CurvePoint } from "../../domain/calibration";
import { ChartTip } from "../queue/TrendChart";

const LABELS = { precision: "Precyzja", recall: "Czułość", f1: "F1" };

interface Props {
  curve: CurvePoint[];
  threshold: number;
}

/** Precision, recall and F1 for every possible threshold; the vertical line is the current one. */
export function PrCurve({ curve, threshold }: Props) {
  return (
    <>
      <div className="chart" data-testid="pr-curve">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 600, height: 220 }}>
          <LineChart data={curve} margin={{ top: 18, right: 12, bottom: 0, left: 0 }} accessibilityLayer>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="threshold" type="number" domain={[0, 100]} ticks={[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]} tickLine={false} axisLine={{ stroke: "var(--line-strong)" }} />
            <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} width={40} tickLine={false} axisLine={false} />
            <Tooltip
              isAnimationActive={false}
              content={({ active, payload, label }) => <ChartTip active={active} payload={payload} label={`Próg ${label ?? ""}`} labels={LABELS} />}
            />
            <Line dataKey="precision" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} type="stepAfter" connectNulls={false} />
            <Line dataKey="recall" stroke="#0e8f8f" strokeWidth={2} dot={false} isAnimationActive={false} type="stepAfter" />
            <Line dataKey="f1" stroke="var(--faint)" strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} type="stepAfter" />
            <ReferenceLine x={threshold} stroke="var(--orange)" strokeWidth={2} label={{ value: `${threshold}`, position: "top", fill: "var(--orange-ink)", fontSize: 12, fontWeight: 600 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="legend">
        <span className="legend__item"><span className="legend__swatch legend__swatch--line" style={{ background: "var(--accent)" }} />Precyzja</span>
        <span className="legend__item"><span className="legend__swatch legend__swatch--line" style={{ background: "#0e8f8f" }} />Czułość</span>
        <span className="legend__item"><span className="legend__swatch legend__swatch--dash" style={{ borderColor: "var(--faint)" }} />F1</span>
        <span className="legend__item"><span className="legend__swatch legend__swatch--line" style={{ background: "var(--orange)" }} />Obecny próg flagowania</span>
      </div>
    </>
  );
}
