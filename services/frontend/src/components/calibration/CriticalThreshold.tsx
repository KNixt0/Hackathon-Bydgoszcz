import { LEVEL_LABEL } from "../../domain/labels";
import { LEVELS, type LevelCounts, type Thresholds } from "../../domain/levels";
import { LevelIcon } from "../ui/LevelBadge";

interface Props {
  thresholds: Thresholds;
  onChange: (red: number) => void;
  counts: LevelCounts;
}

/** The critical threshold as a plain number field, and what both thresholds do to the live queue. */
export function CriticalThreshold({ thresholds, onChange, counts }: Props) {
  const clamped = thresholds.red === thresholds.orange;
  return (
    <div className="crit">
      <div className="crit__row">
        <div className="field crit__field">
          <label className="crit__label" htmlFor="thr-crit">Próg krytyczny</label>
          <input
            id="thr-crit" className="input input--num num" type="number" inputMode="numeric" min={0} max={100} step={1} value={thresholds.red}
            aria-describedby="thr-crit-hint thr-crit-clamp"
            onChange={(e) => {
              const n = Number(e.target.value);
              if (e.target.value !== "" && Number.isFinite(n)) onChange(n);
            }}
          />
        </div>
        <p className="crit__hint" id="thr-crit-hint">Od tego wyniku sprawa jest krytyczna i wywołuje alert. Nie wpływa na fałszywe alarmy ani przeoczone naruszenia.</p>
      </div>
      <p className="crit__clamp" id="thr-crit-clamp" role="status">
        {clamped ? `Próg krytyczny nie może być niższy niż próg oznaczenia (${thresholds.orange}).` : ""}
      </p>
      <p className="effect">
        <span>W kolejce przy tych progach: oznaczone <b className="num" data-testid="queue-flagged">{counts.red + counts.orange}</b>, w tym</span>
        {LEVELS.map((level) => (
          <span key={level} className={`effect__item level--${level}`}>
            <LevelIcon level={level} />
            <span className="effect__word">{LEVEL_LABEL[level]}</span>
            <b className="num" data-testid={`queue-${level}`}>{counts[level]}</b>
          </span>
        ))}
      </p>
    </div>
  );
}
