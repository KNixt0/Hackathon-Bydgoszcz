import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { formatScore } from "../../domain/format";
import { MODULE_LABEL, SEVERITY_LABEL } from "../../domain/labels";
import { complianceScore, deriveLevel, type Thresholds } from "../../domain/levels";
import { listPl } from "../../domain/plural";
import type { Incident, RiskLevel } from "../../types/incident";
import { LevelBadge } from "../ui/LevelBadge";
import { EvidenceChips } from "./EvidenceChips";
import { ScoreScale } from "./ScoreScale";

const LEAD: Record<RiskLevel, string> = { red: "Naruszenie.", orange: "Wymaga weryfikacji.", green: "Brak naruszeń." };

interface Props {
  incident: Incident;
  thresholds: Thresholds;
}

/**
 * WatchIT "Werdykt AI": optional, folded behind a button. Inside: the sentence first (finding word + the
 * engine's summary + violated criteria), then the numbers and the findings.
 */
export function VerdictBlock({ incident, thresholds }: Props) {
  const [open, setOpen] = useState(false);
  const level = deriveLevel(incident.risk_score, thresholds);
  const failed = incident.rules.filter((r) => r.status === "fail").map((r) => r.id);
  const findings = incident.module_results.flatMap((m) => m.findings.map((f) => ({ ...f, module: m.module })));
  return (
    <section className="csec csec--first" id="werdykt" aria-labelledby="werdykt-h">
      <h2 className="section-title" id="werdykt-h">Werdykt AI</h2>
      <button
        type="button" className="btn verdict__toggle" aria-expanded={open} aria-controls="werdykt-tresc" onClick={() => setOpen((v) => !v)}
      >
        {open ? "Ukryj werdykt AI" : "Pokaż werdykt AI"}<ChevronDown aria-hidden="true" className={open ? "chev chev--up" : "chev"} />
      </button>
      <div id="werdykt-tresc" hidden={!open}>
      <p className="verd" data-testid="verdict-sentence">
        <b className={`verd__lead verd__lead--${level}`}>{LEAD[level]}</b> {incident.summary}
        {failed.length > 0 && !/naruszone kryteria/i.test(incident.summary) && <> Naruszone kryteria: {listPl(failed)}.</>}
      </p>
      <div className="score-row">
        <LevelBadge level={level} size="lg" />
        <span className="score-row__item">
          <span className="score-row__label">Wskaźnik zgodności</span>
          <span className="score-row__value num" data-testid="compliance-score">{complianceScore(incident.risk_score)}</span>
          <span className="score-row__label">z 100</span>
        </span>
        <span className="score-row__item">
          <span className="score-row__label">Ryzyko</span>
          <span className="score-row__value score-row__value--sm num">{formatScore(incident.risk_score)}</span>
          <span className="score-row__label">z 100</span>
        </span>
      </div>
      <ScoreScale riskScore={incident.risk_score} thresholds={thresholds} />
      {findings.length > 0 && (
        <div className="findings">
          <h3 className="subhead">Ustalenia</h3>
          <ol className="findings__list">
            {findings.map((f, i) => (
              <li key={`${f.module}-${f.code}-${i}`} className="finding">
                <span className="finding__n num" aria-hidden="true">{i + 1}.</span>
                <span className="finding__body">
                  <span>{f.text}</span>{" "}
                  <small className="finding__meta">
                    Moduł {f.module}, {MODULE_LABEL[f.module].toLowerCase()}; waga {(SEVERITY_LABEL[f.severity] ?? f.severity).toLowerCase()}
                  </small>
                  <EvidenceChips ids={f.evidence_ids} />
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
      </div>
    </section>
  );
}
