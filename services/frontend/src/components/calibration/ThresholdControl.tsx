interface Props {
  /** flag threshold (risk_score >= value is flagged) */
  value: number;
  onChange: (next: number) => void;
}

const clamp = (n: number) => Math.min(100, Math.max(0, Math.round(n)));

/**
 * The one control of the screen (owner decision: "a simple slider"): a native range input, 0–100, step 1.
 * Arrow keys step by 1, Page Up/Down by 10, Home/End jump to the ends; the value sits next to the label.
 */
export function ThresholdControl({ value, onChange }: Props) {
  return (
    <div className="thc">
      <p className="thc__head">
        <label className="thc__label" htmlFor="thr-flag">Próg oznaczenia</label>
        <span className="thc__value num" aria-hidden="true">: {value}</span>
      </p>
      <p className="thc__hint" id="thr-flag-hint">Od tego wyniku ryzyka sprawa trafia do kolejki. Strzałki na klawiaturze zmieniają próg o 1.</p>
      <div className="thc__row">
        <span className="thc__end" aria-hidden="true">0</span>
        <input
          id="thr-flag" className="thc__range" type="range" min={0} max={100} step={1} value={value}
          aria-describedby="thr-flag-hint"
          onChange={(e) => onChange(clamp(Number(e.target.value)))}
        />
        <span className="thc__end" aria-hidden="true">100</span>
      </div>
    </div>
  );
}
