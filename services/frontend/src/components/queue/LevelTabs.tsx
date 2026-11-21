import { useRef, type KeyboardEvent } from "react";
import { LEVEL_LABEL } from "../../domain/labels";
import { LEVELS, type LevelCounts } from "../../domain/levels";
import type { RiskLevel } from "../../types/incident";
import { LevelIcon } from "../ui/LevelBadge";

interface Props {
  counts: LevelCounts;
  active: RiskLevel | "";
  onSelect: (level: RiskLevel | "") => void;
  /** id of the tab panel (the queue box below) */
  panelId: string;
}

type Key = RiskLevel | "";
const KEYS: Key[] = ["", ...LEVELS];
export const levelTabId = (k: Key) => `poziom-${k || "wszystkie"}`;

/** Level filter as tabs with live counts; the selected tab merges into the panel below. Roving tabindex, arrows select. */
export function LevelTabs({ counts, active, onSelect, panelId }: Props) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const total = counts.red + counts.orange + counts.green;
  const move = (e: KeyboardEvent, index: number) => {
    let next: number;
    if (e.key === "ArrowRight") next = (index + 1) % KEYS.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + KEYS.length) % KEYS.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = KEYS.length - 1;
    else return;
    e.preventDefault();
    onSelect(KEYS[next] ?? "");
    refs.current[next]?.focus();
  };
  return (
    <div className="ltabs" role="tablist" aria-label="Poziom ryzyka">
      {KEYS.map((k, i) => {
        const selected = active === k;
        return (
          <button
            key={k || "all"}
            ref={(el) => { refs.current[i] = el; }}
            type="button"
            role="tab"
            id={levelTabId(k)}
            className={`ltab${k ? ` ltab--${k}` : ""}`}
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            onClick={() => onSelect(k)}
            onKeyDown={(e) => move(e, i)}
            data-testid={k ? `count-${k}` : "count-all"}
          >
            {k && <LevelIcon level={k} />}
            <span>{k ? LEVEL_LABEL[k] : "Wszystkie"}</span>
            <b className="num">{k ? counts[k] : total}</b>
          </button>
        );
      })}
    </div>
  );
}
