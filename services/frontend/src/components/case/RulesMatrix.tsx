import { CircleCheck, CircleHelp, CircleMinus, CircleX } from "lucide-react";
import { useState } from "react";
import { formatPercent } from "../../domain/format";
import { RULE_STATUS_LABEL } from "../../domain/labels";
import type { RuleResult, RuleStatus } from "../../types/incident";
import { EvidenceChips } from "./EvidenceChips";

const ICON: Record<RuleStatus, typeof CircleX> = { pass: CircleCheck, fail: CircleX, na: CircleMinus, unknown: CircleHelp };

export function RulesMatrix({ rules }: { rules: RuleResult[] }) {
  const [onlyIssues, setOnlyIssues] = useState(false);
  const shown = onlyIssues ? rules.filter((r) => r.status === "fail" || r.status === "unknown") : rules;
  const tally = (s: RuleStatus) => rules.filter((r) => r.status === s).length;
  return (
    <>
      <div className="matrix__bar">
        <p className="matrix__tally">
          <span className="rs rs--fail">{tally("fail")} naruszeń</span>
          <span className="rs rs--pass">{tally("pass")} spełnionych</span>
          <span className="rs rs--unknown">{tally("unknown")} do oceny ręcznej</span>
          <span className="rs rs--na">{tally("na")} nie dotyczy</span>
        </p>
        <label className="checkbox">
          <input type="checkbox" checked={onlyIssues} onChange={(e) => setOnlyIssues(e.target.checked)} />
          Tylko naruszenia i do oceny
        </label>
      </div>
      <div className="table-wrap">
        <table className="table table--static matrix">
          <thead>
            <tr><th scope="col">Nr</th><th scope="col">Kryterium UKNF</th><th scope="col">Ocena</th><th scope="col">Pewność</th><th scope="col">Uzasadnienie i dowody</th></tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const Icon = ICON[r.status];
              return (
                <tr key={r.id} className={`matrix__row matrix__row--${r.status}`}>
                  <td className="num"><strong>{r.id}</strong></td>
                  <td>
                    <span className="matrix__name">{r.name}</span>
                    <span className="muted matrix__basis">{r.legal_basis}</span>
                  </td>
                  <td><span className={`rs rs--${r.status}`}><Icon aria-hidden="true" />{RULE_STATUS_LABEL[r.status]}</span></td>
                  <td className="num">{r.status === "na" ? "–" : formatPercent(r.confidence)}</td>
                  <td>
                    <span className="matrix__why">{r.explanation}</span>
                    <EvidenceChips ids={r.evidence_ids} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
