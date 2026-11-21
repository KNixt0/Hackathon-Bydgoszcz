import { LEVELS, type LevelCounts, type Thresholds } from "../../domain/levels";
import type { RiskLevel } from "../../types/incident";
import { LevelBadge } from "../ui/LevelBadge";

interface Props {
  counts: LevelCounts;
  thresholds: Thresholds;
  active: RiskLevel | "";
  onSelect: (level: RiskLevel | "") => void;
}

function rangeText(level: RiskLevel, t: Thresholds): string {
  if (level === "red") return `ryzyko od ${t.red}`;
  if (level === "orange") return `ryzyko ${t.orange}–${Math.max(t.orange, t.red - 1)}`;
  return `ryzyko poniżej ${t.orange}`;
}

/** Counts per level at the current thresholds; each tile toggles the level filter. */
export function LevelSummary({ counts, thresholds, active, onSelect }: Props) {
  return (
    <div className="levels" role="group" aria-label="Liczba spraw według poziomu ryzyka">
      {LEVELS.map((level) => (
        <button
          key={level}
          type="button"
          className="level-tile"
          aria-pressed={active === level}
          onClick={() => onSelect(active === level ? "" : level)}
          data-testid={`count-${level}`}
        >
          <LevelBadge level={level} />
          <span className="level-tile__count num">{counts[level]}</span>
          <span className="level-tile__meta">{rangeText(level, thresholds)}</span>
        </button>
      ))}
    </div>
  );
}
