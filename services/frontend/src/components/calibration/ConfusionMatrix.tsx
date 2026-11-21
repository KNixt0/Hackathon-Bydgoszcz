import type { Confusion } from "../../domain/calibration";

function Cell({ n, label, testId }: { n: number; label: string; testId: string }) {
  return (
    <td>
      <b className="num" data-testid={testId}>{n}</b>
      <small>{label}</small>
    </td>
  );
}

/** Ruled table with totals; rows are the analysts' verdict, columns what the threshold decides. No cell fills. */
export function ConfusionMatrix({ confusion: c, threshold }: { confusion: Confusion; threshold: number }) {
  const flagged = c.tp + c.fp;
  const unflagged = c.fn + c.tn;
  return (
    <div className="table-wrap">
      <table className="cm">
        <caption>Macierz pomyłek przy progu {threshold}</caption>
        <thead>
          <tr><td /><th scope="col">Oznaczone</th><th scope="col">Nieoznaczone</th><th scope="col">Razem</th></tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Naruszenie</th>
            <Cell n={c.tp} label="trafne alarmy (TP)" testId="cm-tp" />
            <Cell n={c.fn} label="przeoczone (FN)" testId="cm-fn" />
            <td className="num">{c.tp + c.fn}</td>
          </tr>
          <tr>
            <th scope="row">Zgodne</th>
            <Cell n={c.fp} label="fałszywe alarmy (FP)" testId="cm-fp" />
            <Cell n={c.tn} label="trafnie pominięte (TN)" testId="cm-tn" />
            <td className="num">{c.fp + c.tn}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr><th scope="row">Razem</th><td className="num">{flagged}</td><td className="num">{unflagged}</td><td className="num">{flagged + unflagged}</td></tr>
        </tfoot>
      </table>
    </div>
  );
}
