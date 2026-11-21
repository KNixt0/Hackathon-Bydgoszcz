import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CurvePoint } from "../../domain/calibration";
import { ChartTip } from "../ui/ChartTip";

const LABELS = { precision: "Precyzja (trafność alertów)", recall: "Czułość (wykrywalność naruszeń)" };

/** Precision (solid accent) and recall (dashed ink) for every possible threshold; the vertical line is the current one. */
export function PrCurve({ curve, threshold }: { curve: CurvePoint[]; threshold: number }) {
  return (
    <>
      <div className="chart" data-testid="pr-curve" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 600, height: 220 }}>
          <LineChart data={curve} margin={{ top: 18, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="threshold" type="number" domain={[0, 100]} ticks={[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]} tickLine={false} axisLine={{ stroke: "var(--ink-2)" }} />
            <YAxis domain={[0, 1]} ticks={[0, 0.5, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} width={40} tickLine={false} axisLine={false} />
            <Tooltip
              isAnimationActive={false}
              content={({ active, payload, label }) => <ChartTip active={active} payload={payload} label={`Próg ${label ?? ""}`} labels={LABELS} />}
            />
            <Line dataKey="precision" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} type="stepAfter" />
            <Line dataKey="recall" stroke="var(--ink)" strokeWidth={2} strokeDasharray="4 3" dot={false} isAnimationActive={false} type="stepAfter" />
            <ReferenceLine x={threshold} stroke="var(--ink)" strokeWidth={2} label={{ value: `${threshold}`, position: "top", fill: "var(--ink)", fontSize: 12, fontWeight: 700 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="legend">
        <span className="legend__item"><span className="legend__swatch legend__swatch--line" style={{ background: "var(--accent)" }} />Precyzja, linia ciągła</span>
        <span className="legend__item"><span className="legend__swatch legend__swatch--dash" />Czułość, linia przerywana</span>
        <span className="legend__item">Pionowa linia: obecny próg oznaczenia ({threshold})</span>
      </div>
    </>
  );
}
