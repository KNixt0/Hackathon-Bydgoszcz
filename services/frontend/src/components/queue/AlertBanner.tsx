import { Siren, X } from "lucide-react";
import { Link } from "react-router-dom";
import { formatScore } from "../../domain/format";
import type { IncidentSummary } from "../../types/incident";
import { Button } from "../ui/Button";

interface Props {
  alerts: IncidentSummary[];
  onDismiss: (id: string) => void;
}

/** Persistent until dismissed: a high-risk incident that arrived over the live channel. */
export function AlertBanner({ alerts, onDismiss }: Props) {
  if (alerts.length === 0) return null;
  return (
    <div className="alerts" role="region" aria-label="Alerty wysokiego ryzyka">
      {alerts.map((a) => (
        <div key={a.id} className="alert" role="alert">
          <Siren aria-hidden="true" />
          <div className="alert__body">
            <p className="alert__title">Nowy incydent wysokiego ryzyka · ryzyko {formatScore(a.risk_score)}/100</p>
            <p className="alert__case truncate">{a.title}</p>
          </div>
          <div className="alert__actions">
            <Link className="btn btn--primary btn--sm" to={`/sprawy/${a.id}`}>Otwórz sprawę</Link>
            <Button variant="ghost" size="sm" iconOnly aria-label={`Zamknij alert: ${a.title}`} onClick={() => onDismiss(a.id)}>
              <X aria-hidden="true" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
