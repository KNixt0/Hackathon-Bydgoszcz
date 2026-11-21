/**
 * Polish plural form for a count: 1 → one; last digit 2–4 except 12–14 → few; everything else (0, 5–21, 25…) → many.
 * Negative and fractional counts use the absolute integer part.
 */
export function pl(n: number, one: string, few: string, many: string): string {
  const k = Math.abs(Math.trunc(n));
  if (k === 1) return one;
  const mod10 = k % 10;
  const mod100 = k % 100;
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return few;
  return many;
}

/** "3 sprawy", "5 spraw": the count followed by its form. */
export const plN = (n: number, one: string, few: string, many: string) => `${n} ${pl(n, one, few, many)}`;

/** "3, 7, 12 i 14": a Polish list with "i" before the last item. */
export function listPl(items: readonly string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} i ${items[items.length - 1]}`;
}
