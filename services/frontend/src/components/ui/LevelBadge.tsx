import { LEVEL_LABEL } from "../../domain/labels";
import type { RiskLevel } from "../../types/incident";

export function LevelBadge({ level, size = "md" }: { level: RiskLevel; size?: "md" | "lg" }) {
  return (
    <span className={`level level--${level}${size === "lg" ? " level--lg" : ""}`} data-level={level}>
      <span className="level__dot" aria-hidden="true" />
      {LEVEL_LABEL[level]}
    </span>
  );
}
