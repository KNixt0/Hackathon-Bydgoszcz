import { FlaskConical } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { hostOf, relativeTime } from "../../domain/format";
import { PLATFORM_LABEL, STATUS_LABEL } from "../../domain/labels";
import { deriveLevel, type Thresholds } from "../../domain/levels";
import type { IncidentSummary } from "../../types/incident";
import { Badge } from "../ui/Badge";
import { LevelBadge } from "../ui/LevelBadge";
import { ModuleTag } from "../ui/ModuleTag";
import { ScoreRail } from "../ui/ScoreRail";

interface Props {
  items: IncidentSummary[];
  thresholds: Thresholds;
  fresh: readonly string[];
  alertIds: readonly string[];
}

export function IncidentTable({ items, thresholds, fresh, alertIds }: Props) {
  const navigate = useNavigate();
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Ryzyko</th>
            <th scope="col">Poziom</th>
            <th scope="col">Sprawa</th>
            <th scope="col">Moduł</th>
            <th scope="col">Źródło</th>
            <th scope="col">Wykryto</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => {
            const level = deriveLevel(it.risk_score, thresholds);
            const isFresh = fresh.includes(it.id);
            const parties = [it.advertiser, it.firm].filter(Boolean).join(" → ");
            return (
              <tr
                key={it.id}
                className={`row row--${level}${isFresh ? " row--fresh" : ""}`}
                onClick={() => navigate(`/sprawy/${it.id}`)}
                data-testid="incident-row"
              >
                <td><ScoreRail riskScore={it.risk_score} thresholds={thresholds} /></td>
                <td><LevelBadge level={level} /></td>
                <td className="cell-main">
                  <a
                    href={`/sprawy/${it.id}`}
                    className="cell-main__title"
                    onClick={(e) => {
                      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
                      e.preventDefault();
                      e.stopPropagation();
                      navigate(`/sprawy/${it.id}`);
                    }}
                  >
                    {it.title}
                  </a>
                  <span className="cell-main__sub truncate">{parties || "Podmiot nieustalony"}</span>
                  <span className="cell-main__tags">
                    {isFresh && <Badge tone="accent">Nowe</Badge>}
                    {alertIds.includes(it.id) && <Badge tone="red">Alert</Badge>}
                    {it.synthetic && (
                      <Badge tone="neutral" title="Materiał syntetyczny, przygotowany na potrzeby demonstracji">
                        <FlaskConical aria-hidden="true" />Syntetyczne
                      </Badge>
                    )}
                    {it.failed_rules.length > 0 && <span className="muted">Naruszone kryteria: {it.failed_rules.join(", ")}</span>}
                  </span>
                </td>
                <td>
                  <span className="tags">
                    {it.modules.map((m) => <ModuleTag key={m} module={m} />)}
                  </span>
                </td>
                <td>
                  <span className="cell-source">{PLATFORM_LABEL[it.source.platform]}</span>
                  <span className="cell-main__sub truncate">{hostOf(it.source.url)}</span>
                </td>
                <td className="nowrap" title={it.created_at}>{relativeTime(it.created_at)}</td>
                <td><Badge tone={it.status === "new" ? "accent" : it.status === "escalated" ? "red" : "neutral"}>{STATUS_LABEL[it.status]}</Badge></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
