import type { TrendDay } from "../types/api";
import type { ModuleId } from "../types/incident";
import { deriveLevel, type Thresholds } from "./levels";

export interface TrendRow {
  date: string;
  red: number;
  orange: number;
  green: number;
}

/** Stacks each day's incidents by the level derived from the current thresholds. */
export function trendRows(days: TrendDay[], t: Thresholds, module: ModuleId | 0 = 0): TrendRow[] {
  return [...days]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((day) => {
      const row: TrendRow = { date: day.date, red: 0, orange: 0, green: 0 };
      for (const it of day.items) {
        if (module && it.module !== module) continue;
        row[deriveLevel(it.risk_score, t)] += 1;
      }
      return row;
    });
}
