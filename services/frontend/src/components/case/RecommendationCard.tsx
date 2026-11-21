import { ArrowUpRight, CircleCheck, Eye, MessageSquareWarning, type LucideIcon } from "lucide-react";
import { ACTION_LABEL } from "../../domain/labels";
import type { Recommendation } from "../../types/incident";

const ICON: Record<Recommendation["action"], LucideIcon> = {
  none: CircleCheck, monitor: Eye, explain: MessageSquareWarning, escalate: ArrowUpRight,
};

export function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const Icon = ICON[recommendation.action] ?? Eye;
  return (
    <div className={`reco reco--${recommendation.action}`}>
      <p className="reco__kicker"><Icon aria-hidden="true" />Rekomendacja: {ACTION_LABEL[recommendation.action] ?? recommendation.action}</p>
      <p className="reco__label">{recommendation.label}</p>
      <p className="reco__next"><strong>Następne działanie:</strong> {recommendation.next_step}</p>
    </div>
  );
}
