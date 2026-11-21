import { CircleCheck, CircleHelp, CircleMinus, CircleX, type LucideIcon } from "lucide-react";
import { formatPercent } from "../../domain/format";
import { RULE_METHOD_LABEL, RULE_STATUS_LABEL } from "../../domain/labels";
import type { RuleResult, RuleStatus } from "../../types/incident";
import { Mark, type MarkTone } from "../ui/Mark";
import { EmptyState } from "../ui/States";
import { EvidenceChips } from "./EvidenceChips";

const TONE: Record<RuleStatus, MarkTone> = { pass: "grn", fail: "red", na: "muted", unknown: "amb" };
const ICON: Record<RuleStatus, LucideIcon> = { pass: CircleCheck, fail: CircleX, na: CircleMinus, unknown: CircleHelp };
const ORDER: RuleStatus[] = ["fail", "unknown", "pass", "na"];

export function RuleStatusBadge({ status }: { status: RuleStatus }) {
  return <Mark tone={TONE[status] ?? "muted"} icon={ICON[status] ?? CircleHelp}>{RULE_STATUS_LABEL[status] ?? status}</Mark>;
}

/** The UKNF criteria (18 criteria, 12 split into 12a/12b: 19 rows), one ruled row each, with method and legal basis. */
export function ComplianceMatrix({ rules }: { rules: RuleResult[] }) {
  if (rules.length === 0) {
    return <EmptyState title="Brak oceny kryteriów" text="Silnik nie zwrócił macierzy kryteriów dla tego materiału." />;
  }
  const counts = rules.reduce<Record<string, number>>((acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }), {});
  return (
    <div className="matrix-wrap">
      <p className="matrix-summary">
        <span className="muted">{rules.length} pozycji (18 kryteriów, kryterium 12 w dwóch częściach):</span>
        {ORDER.filter((s) => counts[s]).map((s) => (
          <span key={s} className="matrix-summary__item"><RuleStatusBadge status={s} /> <b className="num">{counts[s]}</b></span>
        ))}
      </p>
      <div className="table-wrap">
        <table className="rt matrix">
          <caption className="sr-only">Macierz zgodności z kryteriami UKNF</caption>
          <thead>
            <tr>
              <th scope="col" className="r">Nr</th><th scope="col">Kryterium i podstawa prawna</th><th scope="col">Ocena</th>
              <th scope="col">Metoda</th><th scope="col" className="r">Pewność</th><th scope="col">Uzasadnienie i dowody</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id} id={`kryterium-${r.id}`} className={`matrix__row matrix__row--${r.status}`} data-testid="rule-row">
                <td className="matrix__id r num">{r.id}</td>
                <td className="matrix__crit">
                  <span className="matrix__name">{r.name}</span>
                  <span className="rt__sub">{r.legal_basis}</span>
                </td>
                <td><RuleStatusBadge status={r.status} /></td>
                <td className="matrix__method">{r.method ? RULE_METHOD_LABEL[r.method] : <span className="muted">nie podano</span>}</td>
                <td className="r num" title="Pewność oceny silnika">{formatPercent(r.confidence)}</td>
                <td className="matrix__why">
                  {r.explanation}
                  <EvidenceChips ids={r.evidence_ids} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
