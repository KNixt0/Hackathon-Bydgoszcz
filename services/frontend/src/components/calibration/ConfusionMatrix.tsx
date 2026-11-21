import type { Confusion } from "../../domain/calibration";

/** Rows: ground truth; columns: what the threshold decides. */
export function ConfusionMatrix({ confusion }: { confusion: Confusion }) {
  return (
    <div className="cm" role="table" aria-label="Macierz pomyłek">
      <div role="row" style={{ display: "contents" }}>
        <span className="cm__corner" role="columnheader"><span className="sr-only">Stan faktyczny</span></span>
        <span className="cm__col" role="columnheader">Oflagowane</span>
        <span className="cm__col" role="columnheader">Poniżej progu flagowania</span>
      </div>
      <div role="row" style={{ display: "contents" }}>
        <span className="cm__row" role="rowheader">Faktyczne naruszenie</span>
        <span className="cm__cell cm__cell--good" role="cell">
          <span className="cm__cell-n num" data-testid="cm-tp">{confusion.tp}</span>
          <span className="cm__cell-label">Trafne alarmy (TP)</span>
        </span>
        <span className="cm__cell cm__cell--bad" role="cell">
          <span className="cm__cell-n num" data-testid="cm-fn">{confusion.fn}</span>
          <span className="cm__cell-label">Przeoczone (FN)</span>
        </span>
      </div>
      <div role="row" style={{ display: "contents" }}>
        <span className="cm__row" role="rowheader">Faktycznie zgodne</span>
        <span className="cm__cell cm__cell--warn" role="cell">
          <span className="cm__cell-n num" data-testid="cm-fp">{confusion.fp}</span>
          <span className="cm__cell-label">Fałszywe alarmy (FP)</span>
        </span>
        <span className="cm__cell cm__cell--good" role="cell">
          <span className="cm__cell-n num" data-testid="cm-tn">{confusion.tn}</span>
          <span className="cm__cell-label">Słusznie pominięte (TN)</span>
        </span>
      </div>
    </div>
  );
}
