import { Download, FileText, FlaskConical } from "lucide-react";
import { exportCsvUrl, exportPdfUrl } from "../../api/endpoints";
import { formatScore } from "../../domain/format";
import { SEVERITY_LABEL } from "../../domain/labels";
import { complianceScore, deriveLevel, type Thresholds } from "../../domain/levels";
import type { ReactNode } from "react";
import type { Incident } from "../../types/incident";
import { Badge } from "../ui/Badge";
import { ButtonLink } from "../ui/Button";
import { LevelBadge } from "../ui/LevelBadge";
import { ModuleTag } from "../ui/ModuleTag";
import { ScoreRail } from "../ui/ScoreRail";
import { EvidenceChips } from "./EvidenceChips";
import { PartiesCard } from "./PartiesCard";
import { RecommendationCard } from "./RecommendationCard";

interface Props {
  incident: Incident;
  thresholds: Thresholds;
  /** The case workflow (stepper, assignee, actions). */
  workflow: ReactNode;
}

/** Block 1: the verdict, readable in three seconds, plus what to do next. */
export function VerdictBlock({ incident, thresholds, workflow }: Props) {
  const level = deriveLevel(incident.risk_score, thresholds);
  const modules = incident.module_results.filter((m) => m.findings.length > 0);
  return (
    <section className="panel block" id="werdykt" aria-labelledby="werdykt-h">
      <header className="panel__head">
        <h2 className="panel__title" id="werdykt-h"><span className="block__n">1</span>Werdykt</h2>
        <div className="exports">
          <ButtonLink size="sm" href={exportPdfUrl(incident.id)} download={`pakiet-dowodowy-${incident.id}.pdf`}>
            <FileText aria-hidden="true" />Pakiet dowodowy PDF
          </ButtonLink>
          <ButtonLink size="sm" href={exportCsvUrl(incident.id)} download={`sprawa-${incident.id}.csv`}>
            <Download aria-hidden="true" />CSV
          </ButtonLink>
        </div>
      </header>
      <div className="verdict">
        <div className="verdict__col">
          <LevelBadge level={level} size="lg" />
          <div>
            <p className="verdict__label">Compliance Score</p>
            <p className={`score score--${level}`}>
              <span className="score__value num" data-testid="compliance-score">{complianceScore(incident.risk_score)}</span>
              <span className="score__of">/ 100</span>
            </p>
          </div>
          <div className="verdict__raw">
            <div className="verdict__raw-row">
              <span>Surowy wynik ryzyka: <strong className="num" style={{ color: "var(--ink)" }}>{formatScore(incident.risk_score)}</strong></span>
              <span>progi {thresholds.orange} / {thresholds.red}</span>
            </div>
            <ScoreRail riskScore={incident.risk_score} thresholds={thresholds} wide showValue={false} />
          </div>
          <div className="verdict__tags">
            {incident.modules.map((m) => <ModuleTag key={m} module={m} />)}
            {incident.synthetic && (
              <Badge tone="accent" title="Materiał przygotowany na potrzeby demonstracji, nie pochodzi z rzeczywistego źródła">
                <FlaskConical aria-hidden="true" />Dane syntetyczne
              </Badge>
            )}
          </div>
        </div>
        <div className="verdict__col">
          <RecommendationCard recommendation={incident.recommendation} />
          <div>
            <p className="verdict__label" style={{ marginBottom: 6 }}>Etap sprawy</p>
            {workflow}
          </div>
        </div>
        <div className="verdict__col">
          <p className="verdict__label">Podmioty</p>
          <PartiesCard entities={incident.entities} registryChecks={incident.registry_checks} />
        </div>
      </div>
      {modules.length > 0 && (
        <div className="findings">
          <h3 className="findings__head">Kluczowe ustalenia</h3>
          <div className="findings__grid">
            {modules.map((m) => (
              <div key={`${m.module}-${m.plugin}`} className="findings__module">
                <div className="findings__module-head">
                  <ModuleTag module={m.module} />
                  <span className="muted" style={{ fontSize: "var(--fs-sm)" }}>ryzyko modułu {formatScore(m.score)} · waga {formatScore(m.weight * 100)}%</span>
                </div>
                <ul>
                  {m.findings.map((f, i) => (
                    <li key={`${f.code}-${i}`} className={`finding finding--${f.severity}`}>
                      <span className="finding__sev" title={`Waga ustalenia: ${SEVERITY_LABEL[f.severity] ?? f.severity}`} />
                      <span>
                        {f.text} <span className="finding__code">{SEVERITY_LABEL[f.severity] ?? f.severity} · {f.code}</span>
                      </span>
                      <EvidenceChips ids={f.evidence_ids} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
