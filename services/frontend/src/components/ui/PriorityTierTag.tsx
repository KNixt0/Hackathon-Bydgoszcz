import { Siren, TriangleAlert, Users } from "lucide-react";
import { TIER_HINT, TIER_LABEL } from "../../domain/labels";
import type { PriorityTier } from "../../domain/priority";

const ICON = { critical_viral: Siren, high_risk_early: TriangleAlert, crowd_anomaly: Users } as const;
const TONE = { critical_viral: "red", high_risk_early: "amb", crowd_anomaly: "ink" } as const;

/** Icon + words (never colour alone), no pill. Nothing for low_watch. */
export function PriorityTierTag({ tier }: { tier: PriorityTier }) {
  if (tier === "low_watch") return null;
  const Icon = ICON[tier];
  return (
    <span className={`mark mark--${TONE[tier]} tier`} data-tier={tier} title={TIER_HINT[tier]}>
      <Icon aria-hidden="true" />
      <span>{TIER_LABEL[tier]}</span>
    </span>
  );
}
