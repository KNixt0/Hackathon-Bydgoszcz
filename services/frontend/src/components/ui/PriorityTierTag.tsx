import { Siren, TriangleAlert, Users } from "lucide-react";
import { TIER_HINT, TIER_LABEL } from "../../domain/labels";
import type { PriorityTier } from "../../domain/priority";

const ICON = { critical_viral: Siren, high_risk_early: TriangleAlert, crowd_anomaly: Users } as const;

/** Icon + words (never colour alone). Nothing for low_watch. */
export function PriorityTierTag({ tier }: { tier: PriorityTier }) {
  if (tier === "low_watch") return null;
  const Icon = ICON[tier];
  return (
    <span className={`tier tier--${tier}`} data-tier={tier} title={TIER_HINT[tier]}>
      <Icon aria-hidden="true" />
      {TIER_LABEL[tier]}
    </span>
  );
}
