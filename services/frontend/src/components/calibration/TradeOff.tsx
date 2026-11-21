import type { Confusion } from "../../domain/calibration";
import { ofCompliant, ofViolations } from "../../domain/calibrationCopy";

function Quantity({ title, gloss, count, population, of, missing, testId }: {
  title: string; gloss: string; count: number; population: number; of: string; missing: string; testId: string;
}) {
  const pct = population > 0 ? (count / population) * 100 : 0;
  return (
    <div className="trade__q" data-testid={testId}>
      <h3 className="trade__title">{title}</h3>
      <p className="trade__gloss">{gloss}</p>
      {population === 0 ? (
        <p className="trade__count"><b>—</b> <span>{missing}</span></p>
      ) : (
        <p className="trade__count"><b className="num" data-testid={`${testId}-count`}>{count}</b> <span>{of}</span></p>
      )}
      <span className="trade__bar" aria-hidden="true">
        <i style={{ width: count > 0 ? `max(2px, ${pct}%)` : 0 }} />
      </span>
    </div>
  );
}

/** The two opposing errors: lowering the threshold trades missed violations for false alarms. */
export function TradeOff({ confusion: c }: { confusion: Confusion }) {
  const compliant = c.fp + c.tn;
  const violations = c.tp + c.fn;
  return (
    <div className="trade">
      <Quantity
        testId="false-alarms" title="Fałszywe alarmy" gloss="zgodne sprawy oznaczone przez pomyłkę"
        count={c.fp} population={compliant} of={ofCompliant(compliant)} missing="brak spraw zgodnych w zbiorze"
      />
      <Quantity
        testId="missed" title="Przeoczone naruszenia" gloss="naruszenia, których system nie oznaczył"
        count={c.fn} population={violations} of={ofViolations(violations)} missing="brak naruszeń w zbiorze"
      />
      <p className="trade__cap">Niższy próg: mniej przeoczonych naruszeń, ale więcej fałszywych alarmów. Wyższy próg: odwrotnie.</p>
    </div>
  );
}
