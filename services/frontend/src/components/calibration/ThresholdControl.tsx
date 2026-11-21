import * as Slider from "@radix-ui/react-slider";
import { RotateCcw, Target } from "lucide-react";
import type { CSSProperties } from "react";
import type { Thresholds } from "../../domain/levels";
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

/** Two handles on the raw risk score: orange ("do weryfikacji") and red ("krytyczne"). */
export function ThresholdControl({ thresholds, onChange, onReset, isDefault, suggested }: Props) {
  const style = { "--t-orange": `${thresholds.orange}%`, "--t-red": `${thresholds.red}%` } as CSSProperties;
  return (
    <>
      <div className="thr__slider-wrap">
        <Slider.Root
          className="thr__slider"
          min={0} max={100} step={1} minStepsBetweenThumbs={0}
          value={[thresholds.orange, thresholds.red]}
          onValueChange={([orange, red]) => {
            if (orange === undefined || red === undefined) return;
            onChange({ orange, red });
          }}
        >
          <Slider.Track className="thr__track" style={style} />
          <Slider.Thumb className="thr__thumb" aria-label="Próg „do weryfikacji”" data-value={thresholds.orange} />
          <Slider.Thumb className="thr__thumb" aria-label="Próg krytyczny" data-value={thresholds.red} />
        </Slider.Root>
        <div className="thr__scale" aria-hidden="true"><span>0 · brak ryzyka</span><span>50</span><span>100 · ryzyko maksymalne</span></div>
      </div>
      <div className="thr__inputs">
        <NumberField id="thr-orange" label="Do weryfikacji od" value={thresholds.orange} onCommit={(orange) => onChange({ orange })} />
        <NumberField id="thr-red" label="Krytyczne od" value={thresholds.red} onCommit={(red) => onChange({ red })} />
        {suggested !== null && (
          <Button onClick={() => onChange({ red: suggested })} disabled={suggested === thresholds.red} title="Ustawia próg krytyczny na wartość o najwyższym F1 w zbiorze oznaczonym">
            <Target aria-hidden="true" />Najlepszy F1: {suggested}
          </Button>
        )}
        <Button variant="ghost" onClick={onReset} disabled={isDefault}><RotateCcw aria-hidden="true" />Przywróć 35 / 70</Button>
      </div>
    </>
  );
}
