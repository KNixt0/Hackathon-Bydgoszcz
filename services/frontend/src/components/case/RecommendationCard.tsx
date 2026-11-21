import { ACTION_LABEL } from "../../domain/labels";
import type { Recommendation } from "../../types/incident";

/** The one left-rule callout on the case page. Same tint for every recommendation; the level is not repeated here. */
export function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  return (
    <section className="callout" aria-labelledby="reco-h" data-testid="recommendation">
      <h2 className="callout__title" id="reco-h">Rekomendacja: {(ACTION_LABEL[recommendation.action] ?? recommendation.action).toLowerCase()}</h2>
      <p className="reco__label">{recommendation.label}</p>
      <p><span className="reco__next">Następne działanie:</span> {recommendation.next_step}</p>
    </section>
  );
}
