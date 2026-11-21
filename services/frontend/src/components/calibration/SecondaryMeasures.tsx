import type { Metrics } from "../../domain/calibration";
import { precisionFraction, recallFraction } from "../../domain/calibrationCopy";
import { formatPercent } from "../../domain/format";

/** Two secondary figures with their fractions; the English terms live only in abbr titles and in the details. */
export function SecondaryMeasures({ metrics: m }: { metrics: Metrics }) {
  const flagged = m.tp + m.fp;
  const violations = m.tp + m.fn;
  return (
    <dl className="sec">
      <div className="sec__item">
        <dt><abbr title="po angielsku: precision">Trafność alertów</abbr></dt>
        <dd className="sec__value num" data-testid="metric-precision">{m.precision === null ? "brak danych" : formatPercent(m.precision)}</dd>
        <dd className="sec__frac">{m.precision === null ? "żadna sprawa nie jest oznaczona" : precisionFraction(m.tp, flagged)}</dd>
      </div>
      <div className="sec__item">
        <dt><abbr title="po angielsku: recall">Wykrywalność naruszeń</abbr></dt>
        <dd className="sec__value num" data-testid="metric-recall">{m.recall === null ? "brak danych" : formatPercent(m.recall)}</dd>
        <dd className="sec__frac">{m.recall === null ? "w zbiorze nie ma naruszeń" : recallFraction(m.tp, violations)}</dd>
      </div>
    </dl>
  );
}
