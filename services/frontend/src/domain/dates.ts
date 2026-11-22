/** Fixed launch date and clock time in Europe/Warsaw. */
export const SYSTEM_START = "2026-11-21";
export const SYSTEM_START_LOCAL = `${SYSTEM_START}T20:50`;

export function warsawInput(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const parts = new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Warsaw", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(date);
  const get = (key: string) => parts.find((p) => p.type === key)?.value ?? "00";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

/** datetime-local fields represent Warsaw time, independently of the browser's time zone. */
export function warsawInstant(input: string): number {
  if (/Z$|[+-]\d\d:\d\d$/.test(input)) return Date.parse(input);
  const raw = Date.parse(`${input.length === 10 ? `${input}T00:00` : input}:00Z`);
  if (!Number.isFinite(raw)) return NaN;
  let guess = raw;
  for (let i = 0; i < 2; i++) {
    const rendered = Date.parse(`${warsawInput(new Date(guess))}:00Z`);
    guess += raw - rendered;
  }
  return guess;
}

/** Reject malformed URL filters, impossible calendar dates and nonexistent Warsaw clock times. */
export function validDateInput(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?$/.test(value)) return false;
  const local = value.length === 10 ? `${value}T00:00` : value;
  const parsed = Date.parse(`${local}:00Z`);
  return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 16) === local
    && (value.length === 10 || warsawInput(new Date(warsawInstant(value))) === value);
}

export function apiDate(value: string): string {
  return value.length === 10 || /Z$|[+-]\d\d:\d\d$/.test(value) ? value : new Date(warsawInstant(value)).toISOString();
}

export function todayIso(now = new Date()): string {
  return warsawInput(now).slice(0, 10);
}

export function clampDate(value: string, today = todayIso()): string {
  if (!value || !validDateInput(value)) return "";
  return value < SYSTEM_START ? SYSTEM_START : value > today ? today : value;
}

export function clampDateTime(value: string, latest = warsawInput(new Date())): string {
  if (!value || !validDateInput(value)) return "";
  const local = value.length === 10 ? `${value}T00:00` : value;
  return local < SYSTEM_START_LOCAL ? SYSTEM_START_LOCAL : local > latest ? latest : local;
}

export function matchesDates(value: string, from: string, to: string): boolean {
  const day = warsawInput(value).slice(0, 10);
  const moment = Date.parse(value);
  return (!from || (from.length === 10 ? day >= from : moment >= warsawInstant(from)))
    && (!to || (to.length === 10 ? day <= to : moment <= warsawInstant(to)));
}

