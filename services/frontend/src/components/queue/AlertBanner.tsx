import { OctagonAlert, Users, X } from "lucide-react";
import { Link } from "react-router-dom";
import { formatScore, reportsLabel } from "../../domain/format";
import type { IncidentSummary } from "../../types/incident";
import { Button } from "../ui/Button";

interface Props {
  alerts: IncidentSummary[];
  onDismiss: (id: string) => void;
  /** alert:viral: a critical case that reached 5 user reports */
  viral?: IncidentSummary[];
  onDismissViral?: (id: string) => void;
}

/** Persistent until dismissed: square bordered alert, icon and a lead word, the case as a link. No red fill. */
export function AlertBanner({ alerts, onDismiss, viral = [], onDismissViral }: Props) {
  if (alerts.length === 0 && viral.length === 0) return null;
  return (
    <>
      {alerts.length > 0 && (
        <div className="alerts" role="region" aria-label="Alerty wysokiego ryzyka">
          {alerts.map((a) => (
            <div key={a.id} className="alert" role="alert">
              <OctagonAlert aria-hidden="true" className="alert__icon" />
              <div className="alert__body">
                <p className="alert__title">Nowy incydent wysokiego ryzyka <span className="alert__meta">ryzyko {formatScore(a.risk_score)} na 100</span></p>
                <p className="alert__case truncate">{a.title}</p>
              </div>
              <div className="alert__actions">
                <Link className="btn btn--sm" to={`/sprawy/${a.id}`}>Otwórz sprawę</Link>
                <Button variant="ghost" size="sm" iconOnly aria-label={`Zamknij alert: ${a.title}`} onClick={() => onDismiss(a.id)}>
                  <X aria-hidden="true" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
      {viral.length > 0 && (
        <div className="alerts" role="region" aria-label="Alerty zgłoszeń użytkowników">
          {viral.map((a) => (
            <div key={a.id} className="alert alert--viral" role="alert">
              <Users aria-hidden="true" className="alert__icon" />
              <div className="alert__body">
                <p className="alert__title">
                  Krytyczna sprawa zgłaszana przez wielu użytkowników{" "}
                  <span className="alert__meta">{reportsLabel(a.user_reports_count)}, ryzyko {formatScore(a.risk_score)} na 100</span>
                </p>
                <p className="alert__case truncate">{a.title}</p>
              </div>
              <div className="alert__actions">
                <Link className="btn btn--sm" to={`/sprawy/${a.id}`}>Otwórz sprawę</Link>
                <Button variant="ghost" size="sm" iconOnly aria-label={`Zamknij alert zgłoszeń: ${a.title}`} onClick={() => onDismissViral?.(a.id)}>
                  <X aria-hidden="true" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
