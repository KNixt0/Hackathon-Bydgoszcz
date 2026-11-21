import type { CSSProperties } from "react";
import { deriveLevel, type Thresholds } from "../../domain/levels";
import { formatScore } from "../../domain/format";

interface Props {
  riskScore: number;
  thresholds: Thresholds;
  wide?: boolean;
  showValue?: boolean;
}

/** Raw risk score (0–100, higher = worse) on a track that shows both thresholds. */
export function ScoreRail({ riskScore, thresholds, wide = false, showValue = true }: Props) {
  const level = deriveLevel(riskScore, thresholds);
  const pct = Math.min(100, Math.max(0, riskScore));
  const style = { "--t-orange": `${thresholds.orange}%`, "--t-red": `${thresholds.red}%` } as CSSProperties;
  return (
    <span className={`rail rail--${level}${wide ? " rail--wide" : ""}`}>
      {showValue && <span className="rail__value num">{formatScore(riskScore)}</span>}
      <span
        className="rail__track"
        style={style}
        role="img"
        aria-label={`Ryzyko ${formatScore(riskScore)} na 100; próg do weryfikacji ${thresholds.orange}, próg krytyczny ${thresholds.red}`}
      >
        <span className="rail__fill" style={{ width: `${pct}%` }} />
        <span className="rail__tick" style={{ left: `${thresholds.orange}%` }} />
        <span className="rail__tick" style={{ left: `${thresholds.red}%` }} />
      </span>
    </span>
  );
}
