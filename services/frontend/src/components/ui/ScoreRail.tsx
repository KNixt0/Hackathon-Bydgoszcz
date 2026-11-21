import { deriveLevel, type Thresholds } from "../../domain/levels";
import { formatScore } from "../../domain/format";

interface Props {
  riskScore: number;
  thresholds: Thresholds;
  showValue?: boolean;
}

/** Risk number plus the ruled 56 x 12 mini-scale: baseline, fill to the score, ticks at both thresholds. */
export function ScoreRail({ riskScore, thresholds, showValue = true }: Props) {
  const level = deriveLevel(riskScore, thresholds);
  const pct = Math.min(100, Math.max(0, riskScore));
  return (
    <span className="rk">
      {showValue && <span className="rk__n num" aria-hidden="true">{formatScore(riskScore)}</span>}
      <span className="sr-only">Ryzyko {formatScore(riskScore)} na 100</span>
      <span className={`ms ms--${level}`} aria-hidden="true">
        <span className="ms__f" style={{ width: `${pct}%` }} />
        <span className="ms__t" style={{ left: `${thresholds.orange}%` }} />
        <span className="ms__t" style={{ left: `${Math.min(thresholds.red, 99.5)}%` }} />
      </span>
    </span>
  );
}
