import type { Metrics } from "../../domain/calibration";

interface Props {
  suggested: number;
  current: number;
  /** metrics at the suggested threshold */
  metrics: Metrics;
  onApply: () => void;
}

const pct = (v: number | null) => (v === null ? 0 : Math.round(v * 100));

/** One button that sets the preview to the best-F1 threshold, with the reason in one sentence. */
export function RecommendedThreshold({ suggested, current, metrics, onApply }: Props) {
  const here = suggested === current;
  return (
    <div className="reco-thr">
      <button type="button" className="btn" onClick={onApply} disabled={here} aria-describedby="reco-thr-why">Ustaw zalecany próg: {suggested}</button>
      <p className="reco-thr__why" id="reco-thr-why">
        {here
          ? "To jest zalecany próg: najlepiej godzi wykrywanie naruszeń z liczbą fałszywych alarmów."
          : `Próg ${suggested} najlepiej godzi oba cele: wykrywa ${pct(metrics.recall)}% naruszeń przy ${pct(metrics.precision)}% trafnych alertów.`}
      </p>
    </div>
  );
}
