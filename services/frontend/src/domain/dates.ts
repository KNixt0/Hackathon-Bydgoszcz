/** WatchIt started on this day: no detection is older and no date picker goes back further. */
export const SYSTEM_START = "2026-11-21";

/** Today as YYYY-MM-DD in local time (date pickers cannot go past it). */
export function todayIso(now: Date = new Date()): string {
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${m}-${d}`;
}

/** A picked date kept inside [SYSTEM_START, today]; "" stays "" (no filter). */
export function clampDate(value: string, today: string = todayIso()): string {
  if (!value) return "";
  if (value < SYSTEM_START) return SYSTEM_START;
  if (value > today) return today;
  return value;
}
