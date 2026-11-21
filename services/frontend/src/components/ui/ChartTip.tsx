import { formatShortDay } from "../../domain/format";

interface TipProps {
  active?: boolean;
  label?: string | number;
  payload?: readonly { dataKey?: unknown; value?: unknown; color?: string }[];
  labels: Record<string, string>;
}

/** Recharts tooltip in the register style: white, 1px ink-2 frame, no shadow. */
export function ChartTip({ active, label, payload, labels }: TipProps) {
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
