import { formatDateTime, reportsLabel } from "../../domain/format";
import { REPORT_CATEGORY_LABEL, TIER_HINT } from "../../domain/labels";
import type { PriorityTier } from "../../domain/priority";
import type { CaseReport } from "../../types/api";
import { PriorityTierTag } from "../ui/PriorityTierTag";
import { EmptyState, ErrorState, Skeleton } from "../ui/States";

interface Props {
  count: number;
  tier: PriorityTier;
  /** null = loading */
  items: CaseReport[] | null;
  error: string | null;
  onRetry: () => void;
}

/** Public reports linked to the case: the count, the tier and what people wrote (plain text, escaped by React). */
export function UserReports({ count, tier, items, error, onRetry }: Props) {
  return (
    <section className="csec" id="zgloszenia" aria-labelledby="zgloszenia-h">
      <div className="csec__head">
        <h2 className="section-title" id="zgloszenia-h">Zgłoszenia użytkowników</h2>
        <PriorityTierTag tier={tier} />
      </div>
      <p className="csec__lead" data-testid="case-report-count">{count === 0 ? "Nikt nie zgłosił tej sprawy." : reportsLabel(count)}</p>
      {tier === "crowd_anomaly" && <p className="reports__note">{TIER_HINT.crowd_anomaly}</p>}
      {count === 0 ? null : error ? (
        <ErrorState compact title="Nie udało się wczytać zgłoszeń" message={error} onRetry={onRetry} />
      ) : items === null ? (
        <div aria-busy="true"><Skeleton height={14} width="60%" /></div>
      ) : items.length === 0 ? (
        <EmptyState compact title="Brak szczegółów zgłoszeń" text="Zgłoszenia zostały policzone, ale nie mają treści do pokazania." />
      ) : (
        <ul className="reports" data-testid="case-reports">
          {items.map((r, i) => (
            <li key={`${r.created_at}-${i}`} className="reports__item">
              <span className="reports__meta">
                {formatDateTime(r.created_at)}
                <span className="reports__cat">{r.category_hint ? REPORT_CATEGORY_LABEL[r.category_hint] : "Kategoria: nie wiem"}</span>
              </span>
              <span className="reports__comment">{r.comment ? r.comment : <span className="muted">Bez uwag.</span>}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
