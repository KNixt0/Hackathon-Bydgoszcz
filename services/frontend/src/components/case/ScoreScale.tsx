import { complianceScore, type Thresholds } from "../../domain/levels";
import { formatScore } from "../../domain/format";

interface Props {
  riskScore: number;
  thresholds: Thresholds;
}

const TENS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
const FIVES = Array.from({ length: 21 }, (_, i) => i * 5);
const clamp = (n: number) => Math.min(100, Math.max(0, n));

function edge(v: number): string {
  if (v <= 0) return "ds__l--s";
  if (v >= 100) return "ds__l--e";
  return "";
}

/**
 * Dual ruled scale: risk on top, Compliance Score (100 minus risk) below, one needle for this case.
 * Thresholds come from the threshold context. Everything but the caption is hidden from screen readers.
 */
export function ScoreScale({ riskScore, thresholds }: Props) {
  const risk = clamp(riskScore);
  const flag = clamp(thresholds.orange);
  const crit = clamp(thresholds.red);
  const marks = [flag, crit];
  // A ten-label too close to a threshold label would collide with it: drop it.
  const tens = TENS.filter((v) => !marks.some((m) => m !== v && Math.abs(m - v) < 6));
  const labels = [...new Set([...tens, ...marks])].sort((a, b) => a - b);
  return (
    <figure className="ds" data-testid="score-scale">
      <div className="ds__th" aria-hidden="true">
        <span style={{ left: `${flag}%` }}>oznaczenie</span>
        {crit !== flag && <span style={{ left: `${crit}%` }} className={crit > 82 ? "ds__th--e" : undefined}>krytyczne</span>}
      </div>
      <span className="ds__c ds__c1" aria-hidden="true">Ryzyko</span>
      <div className="ds__lr" aria-hidden="true">
        {labels.map((v) => (
          <span key={v} style={{ left: `${v}%` }} className={`${edge(v)}${marks.includes(v) ? " ds__l--k" : ""}${!marks.includes(v) && v % 20 !== 0 ? " ds__l--odd" : ""}`}>{v}</span>
        ))}
      </div>
      <div className="ds__ax" aria-hidden="true">
        <span className="ds__z ds__z--g" style={{ left: 0, width: `${flag}%` }} />
        <span className="ds__z ds__z--a" style={{ left: `${flag}%`, width: `${crit - flag}%` }} />
        <span className="ds__z ds__z--r" style={{ left: `${crit}%`, width: `${100 - crit}%` }} />
        {FIVES.map((v) => <span key={v} className={`ds__tk${v % 10 ? " ds__tk--mi" : ""}`} style={{ left: `${v}%` }} />)}
        {marks.map((m, i) => <span key={`${m}-${i}`} className="ds__tt" style={{ left: `${m}%` }} />)}
      </div>
      <span className="ds__c ds__c2" aria-hidden="true">Compliance Score</span>
      <div className="ds__lc" aria-hidden="true">
        {labels.map((v) => (
          <span key={v} style={{ left: `${v}%` }} className={`${edge(v)}${!marks.includes(v) && v % 20 !== 0 ? " ds__l--odd" : ""}`}>{100 - v}</span>
        ))}
      </div>
      <div className="ds__mk" aria-hidden="true"><span className="ds__nd" style={{ left: `${risk}%` }} /></div>
      <figcaption>
        Odczyt: ryzyko <b className="num">{formatScore(riskScore)}</b> z 100, wskaźnik zgodności <b className="num">{complianceScore(riskScore)}</b>.
        Progi na skali ryzyka: oznaczenie od <b className="num">{thresholds.orange}</b>, krytyczne od <b className="num">{thresholds.red}</b>.
        <span className="ds__nar"> Górna skala to ryzyko, dolna to Compliance Score (100 minus ryzyko).</span>
      </figcaption>
    </figure>
  );
}
