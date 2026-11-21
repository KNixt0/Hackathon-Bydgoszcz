import { Check, CircleHelp, ListChecks, Minus, X, type LucideIcon } from "lucide-react";
import { formatPercent } from "../../domain/format";
import { RULE_STATUS_LABEL } from "../../domain/labels";
import type { RuleResult, RuleStatus } from "../../types/incident";
import { Badge, type Tone } from "../ui/Badge";
import { EmptyState } from "../ui/States";
import { EvidenceChips } from "./EvidenceChips";

const TONE: Record<RuleStatus, Tone> = { pass: "green", fail: "red", na: "neutral", unknown: "orange" };
const ICON: Record<RuleStatus, LucideIcon> = { pass: Check, fail: X, na: Minus, unknown: CircleHelp };
const ORDER: RuleStatus[] = ["fail", "unknown", "pass", "na"];

export function RuleStatusBadge({ status }: { status: RuleStatus }) {
  const Icon = ICON[status] ?? CircleHelp;
  return <Badge tone={TONE[status] ?? "neutral"}><Icon aria-hidden="true" />{RULE_STATUS_LABEL[status] ?? status}</Badge>;
}

/** Block 2d: the UKNF criteria (ids 1–18, 12 split into 12a/12b), one row per criterion. */
export function ComplianceMatrix({ rules }: { rules: RuleResult[] }) {
  if (rules.length === 0) {
    return <EmptyState icon={<ListChecks />} title="Brak oceny kryteriów" text="Silnik nie zwrócił macierzy kryteriów dla tego materiału." />;
  }
  const counts = rules.reduce<Record<string, number>>((acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }), {});
  return (
    <>
      <div className="matrix-top">
        <div className="matrix-strip" aria-label="Przegląd kryteriów">
          {rules.map((r) => (
            <a key={r.id} href={`#kryterium-${r.id}`} className={`matrix-cell matrix-cell--${r.status}`} title={`${r.id}. ${r.name}: ${RULE_STATUS_LABEL[r.status] ?? r.status}`}>
              {r.id}<span className="sr-only">: {RULE_STATUS_LABEL[r.status] ?? r.status}</span>
            </a>
          ))}
        </div>
        <div className="matrix-summary">
          {ORDER.filter((s) => counts[s]).map((s) => (
            <span key={s} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <RuleStatusBadge status={s} /><strong className="num">{counts[s]}</strong>
            </span>
          ))}
        </div>
      </div>
      <div className="table-wrap">
        <table className="matrix">
          <caption className="sr-only">Macierz zgodności z kryteriami UKNF</caption>
          <thead>
            <tr>
              <th scope="col">Nr</th><th scope="col">Kryterium i podstawa prawna</th><th scope="col">Ocena</th>
              <th scope="col">Pewność</th><th scope="col">Uzasadnienie i dowody</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id} id={`kryterium-${r.id}`} className={`matrix__row matrix__row--${r.status}`} data-testid="rule-row">
                <td className="matrix__id num">{r.id}</td>
                <td style={{ maxWidth: 320 }}>
                  <span className="matrix__name" style={{ display: "block" }}>{r.name}</span>
                  <span className="matrix__legal">{r.legal_basis}</span>
                </td>
                <td><RuleStatusBadge status={r.status} /></td>
                <td>
                  <span className="conf" title="Pewność oceny silnika">
                    <span className="conf__bar" aria-hidden="true"><i style={{ width: `${Math.round(r.confidence * 100)}%` }} /></span>
                    <span className="num">{formatPercent(r.confidence)}</span>
                  </span>
                </td>
                <td>
                  {r.explanation}
                  <EvidenceChips ids={r.evidence_ids} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
