import { CircleCheck, OctagonAlert, Search, type LucideIcon } from "lucide-react";
import { LEVEL_LABEL } from "../../domain/labels";
import type { RiskLevel } from "../../types/incident";

/** Each level has an icon of its own shape: the shape and the word carry the meaning, colour only repeats it. */
export const LEVEL_ICON: Record<RiskLevel, LucideIcon> = { red: OctagonAlert, orange: Search, green: CircleCheck };

export function LevelIcon({ level }: { level: RiskLevel }) {
  const Icon = LEVEL_ICON[level];
  return <Icon aria-hidden="true" strokeWidth={2} />;
}

export function LevelBadge({ level, size = "md" }: { level: RiskLevel; size?: "md" | "lg" }) {
  return (
    <span className={`level level--${level}${size === "lg" ? " level--lg" : ""}`} data-level={level}>
      <LevelIcon level={level} />
      {LEVEL_LABEL[level]}
    </span>
  );
}
