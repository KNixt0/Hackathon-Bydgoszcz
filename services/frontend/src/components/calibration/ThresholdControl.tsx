import * as Slider from "@radix-ui/react-slider";
import { RotateCcw, Target } from "lucide-react";
import type { CSSProperties } from "react";
import { DEFAULT_THRESHOLDS, type Thresholds } from "../../domain/levels";
import { Button } from "../ui/Button";

interface Props {
  thresholds: Thresholds;
  onChange: (next: Partial<Thresholds>) => void;
  onReset: () => void;
  isDefault: boolean;
  /** Threshold with the best F1 on the labelled set, if computable. */
  suggested: number | null;
}

function NumberField({ label, value, onCommit, id }: { label: string; value: number; onCommit: (n: number) => void; id: string }) {
  return (
    <label className="field" htmlFor={id}>
      <span className="field__label">{label}</span>
      <input
        id={id} className="input num" type="number" min={0} max={100} step={1} value={value}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (e.target.value !== "" && Number.isFinite(n)) onCommit(n);
        }}
      />
    </label>
  );
}

/**
 * Primary slider: the flag threshold (T_orange), on which the whole calibration panel works
 * (flagged = risk_score >= T_orange). Secondary slider: the critical threshold (T_red >= T_orange).
 */
export function ThresholdControl({ thresholds, onChange, onReset, isDefault, suggested }: Props) {
  const style = { "--t-orange": `${thresholds.orange}%`, "--t-red": `${thresholds.red}%` } as CSSProperties;
  return (
    <>
      <div className="thr__slider-wrap">
        <Slider.Root
          className="thr__slider"
          min={0} max={100} step={1}
          value={[thresholds.orange]}
          onValueChange={([orange]) => {
            if (orange !== undefined) onChange({ orange });
          }}
        >
          <Slider.Track className="thr__track" style={style} />
          <Slider.Thumb className="thr__thumb" aria-label="Próg flagowania" data-value={thresholds.orange} />
        </Slider.Root>
        <div className="thr__scale" aria-hidden="true"><span>0 · brak ryzyka</span><span>50</span><span>100 · ryzyko maksymalne</span></div>
        <div className="thr__secondary">
          <span className="thr__secondary-label">Próg krytyczny (od niego sprawa jest „krytyczna”, nie tylko „do weryfikacji”)</span>
          <Slider.Root
            className="thr__slider thr__slider--secondary"
            min={0} max={100} step={1}
            value={[thresholds.red]}
            onValueChange={([red]) => {
              if (red !== undefined) onChange({ red });
            }}
          >
            <Slider.Track className="thr__track thr__track--secondary" />
            <Slider.Thumb className="thr__thumb thr__thumb--secondary" aria-label="Próg krytyczny" data-value={thresholds.red} />
          </Slider.Root>
        </div>
      </div>
      <div className="thr__inputs">
        <NumberField id="thr-orange" label="Flagowanie od" value={thresholds.orange} onCommit={(orange) => onChange({ orange })} />
        <NumberField id="thr-red" label="Krytyczne od" value={thresholds.red} onCommit={(red) => onChange({ red })} />
        {suggested !== null && (
          <Button onClick={() => onChange({ orange: suggested })} disabled={suggested === thresholds.orange} title="Ustawia próg flagowania na wartość o najwyższym F1 w zbiorze oznaczonym">
            <Target aria-hidden="true" />Najlepszy F1: {suggested}
          </Button>
        )}
        <Button variant="ghost" onClick={onReset} disabled={isDefault}><RotateCcw aria-hidden="true" />Przywróć {DEFAULT_THRESHOLDS.orange} / {DEFAULT_THRESHOLDS.red}</Button>
      </div>
    </>
  );
}
