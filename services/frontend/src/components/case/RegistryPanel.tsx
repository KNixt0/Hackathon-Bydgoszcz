import { ExternalLink } from "lucide-react";
import { formatDate, formatPln, safeHref } from "../../domain/format";
import { REGISTRY_STATUS_LABEL } from "../../domain/labels";
import type { Financials, RegistryCheck } from "../../types/incident";
import { Badge } from "../ui/Badge";

const TONE = { listed: "green", not_listed: "orange", warning_listed: "red", inactive: "orange", not_checked: "neutral" } as const;

export function RegistryTable({ checks }: { checks: RegistryCheck[] }) {
  if (checks.length === 0) return <p className="muted">Nie sprawdzono żadnych rejestrów.</p>;
  return (
    <div className="table-wrap">
      <table className="table table--static">
        <thead><tr><th scope="col">Rejestr</th><th scope="col">Szukany podmiot</th><th scope="col">Wynik</th><th scope="col">Stan na</th></tr></thead>
        <tbody>
          {checks.map((c, i) => {
            const href = safeHref(c.url);
            return (
              <tr key={`${c.registry}-${i}`}>
                <td>
                  {href ? <a href={href} target="_blank" rel="noopener noreferrer">{c.label}<ExternalLink size={11} aria-hidden="true" style={{ marginLeft: 4 }} /></a> : c.label}
                </td>
                <td>{c.subject}</td>
                <td><Badge tone={TONE[c.status]}>{REGISTRY_STATUS_LABEL[c.status]}</Badge><span className="muted registry__detail">{c.detail}</span></td>
                <td className="nowrap">{formatDate(c.snapshot_date)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function FinancialsPanel({ data }: { data: Financials }) {
  return (
    <div className="stack">
      <dl className="kv">
        <dt>Spółka</dt><dd>{data.company}</dd>
        <dt>KRS</dt><dd className="num">{data.krs ?? "brak danych"}</dd>
        <dt>Data założenia</dt><dd>{formatDate(data.incorporated_on)}{data.age_months !== null && <span className="muted"> ({data.age_months} mies.)</span>}</dd>
        <dt>Kapitał zakładowy</dt><dd className="num">{formatPln(data.share_capital_pln)}</dd>
      </dl>
      {data.flags.length > 0 && <ul className="flags">{data.flags.map((f) => <li key={f}>{f}</li>)}</ul>}
      {data.statements.length > 0 && (
        <table className="table table--static">
          <thead><tr><th scope="col">Rok</th><th scope="col">Przychody</th><th scope="col">Wynik netto</th><th scope="col">Sprawozdanie</th></tr></thead>
          <tbody>
            {data.statements.map((s) => (
              <tr key={s.year}>
                <td className="num">{s.year}</td><td className="num">{formatPln(s.revenue_pln)}</td><td className="num">{formatPln(s.net_result_pln)}</td>
                <td><Badge tone={s.filed ? "green" : "orange"}>{s.filed ? "Złożone" : "Niezłożone"}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
