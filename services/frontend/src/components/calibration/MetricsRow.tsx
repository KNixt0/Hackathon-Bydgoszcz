import type { Metrics } from "../../domain/calibration";
import { formatPercent } from "../../domain/format";

export function MetricsRow({ metrics }: { metrics: Metrics }) {
  const items = [
    { key: "precision", label: "Precyzja", value: metrics.precision, hint: `${metrics.tp} z ${metrics.tp + metrics.fp} alarmów to naruszenia` },
    { key: "recall", label: "Czułość", value: metrics.recall, hint: `wykryto ${metrics.tp} z ${metrics.tp + metrics.fn} naruszeń` },
    { key: "f1", label: "F1", value: metrics.f1, hint: "średnia harmoniczna obu miar" },
  ];
  return (
    <dl className="metrics">
      {items.map((m) => (
        <div key={m.key} className="metric">
          <dt className="metric__label">{m.label}</dt>
          <dd className="metric__value num" data-testid={`metric-${m.key}`}>{formatPercent(m.value)}</dd>
          <dd className="metric__hint">{m.hint}</dd>
        </div>
      ))}
    </dl>
  );
}
