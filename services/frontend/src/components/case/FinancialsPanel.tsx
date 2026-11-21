import { CircleCheck, CircleMinus, TriangleAlert } from "lucide-react";
import { formatDate, formatPln } from "../../domain/format";
import type { Financials } from "../../types/incident";
import { Mark } from "../ui/Mark";
import { EmptyState } from "../ui/States";

function ageText(months: number | null): string {
  if (months === null) return "brak danych";
  if (months < 12) return `${months} mies.`;
  const years = Math.floor(months / 12);
  const rest = months % 12;
  return rest ? `${years} l. ${rest} mies.` : `${years} l.`;
}

/** Block 2c: KRS facts and filed statements of the company behind the material. */
export function FinancialsPanel({ financials }: { financials: Financials | null }) {
  if (!financials) {
    return (
      <EmptyState
        title="Brak danych finansowych"
        text="Dla tego materiału nie pobrano danych spółki z KRS (data rejestracji, kapitał, sprawozdania)."
      />
    );
  }
  const max = Math.max(1, ...financials.statements.map((s) => Math.abs(s.revenue_pln ?? 0)));
  return (
    <div className="vbody">
      <div className="vgrid">
        <div className="vsub">
          <h3 className="subhead">{financials.company}</h3>
          <dl className="kv kv--compact">
            <dt>Numer KRS</dt><dd className="num">{financials.krs ?? "brak danych"}</dd>
            <dt>Data rejestracji</dt><dd>{financials.incorporated_on ? formatDate(financials.incorporated_on) : "brak danych"}</dd>
            <dt>Wiek spółki</dt><dd>{ageText(financials.age_months)}</dd>
            <dt>Kapitał zakładowy</dt><dd className="num">{formatPln(financials.share_capital_pln)}</dd>
          </dl>
        </div>
        <div className="vsub">
          <h3 className="subhead">Sygnały ostrzegawcze</h3>
          {financials.flags.length === 0 ? <p className="muted">Brak sygnałów ostrzegawczych w danych rejestrowych.</p> : (
            <ul style={{ display: "grid", gap: 6 }}>
              {financials.flags.map((f) => (
                <li key={f}><Mark tone="amb" icon={TriangleAlert}>{f}</Mark></li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="vsub">
        <h3 className="subhead">Sprawozdania finansowe</h3>
        {financials.statements.length === 0 ? (
          <p className="muted">Spółka nie złożyła jeszcze żadnego sprawozdania finansowego.</p>
        ) : (
          <table className="rt">
            <thead>
              <tr>
                <th scope="col">Rok</th><th scope="col" className="r">Przychód</th><th scope="col" style={{ width: "30%" }}><span className="sr-only">Przychód na wykresie</span></th>
                <th scope="col" className="r">Wynik netto</th><th scope="col">Sprawozdanie</th>
              </tr>
            </thead>
            <tbody>
              {financials.statements.map((s) => (
                <tr key={s.year}>
                  <td className="num">{s.year}</td>
                  <td className="r num">{formatPln(s.revenue_pln)}</td>
                  <td>
                    {s.revenue_pln !== null && (
                      <span className="hbar" aria-hidden="true">
                        <i style={{ width: `${(Math.abs(s.revenue_pln) / max) * 100}%` }} />
                      </span>
                    )}
                  </td>
                  <td className="r num" style={s.net_result_pln !== null && s.net_result_pln < 0 ? { color: "var(--c-red)" } : undefined}>{formatPln(s.net_result_pln)}</td>
                  <td>{s.filed ? <Mark tone="grn" icon={CircleCheck}>złożone</Mark> : <Mark tone="amb" icon={CircleMinus}>nie złożono</Mark>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
