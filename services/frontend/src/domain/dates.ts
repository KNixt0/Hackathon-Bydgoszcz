export interface DateBounds { earliest: string; latest: string; timezone: string }

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

export function apiDate(value: string): string {
  return value.length === 10 || /Z$|[+-]\d\d:\d\d$/.test(value) ? value : new Date(warsawInstant(value)).toISOString();
}

export function defaultDateBounds(now = new Date()): DateBounds {
  const day = warsawInput(now).slice(0, 10);
  let earliest = warsawInstant(`${day}T20:50`);
  if (earliest > now.getTime()) {
    const previous = new Date(Date.parse(`${day}T12:00Z`) - 86400000).toISOString().slice(0, 10);
    earliest = warsawInstant(`${previous}T20:50`);
  }
  return { earliest: new Date(earliest).toISOString(), latest: now.toISOString(), timezone: "Europe/Warsaw" };
}

export function matchesDates(value: string, from: string, to: string): boolean {
  const day = warsawInput(value).slice(0, 10);
  const moment = Date.parse(value);
  return (!from || (from.length === 10 ? day >= from : moment >= warsawInstant(from)))
    && (!to || (to.length === 10 ? day <= to : moment <= warsawInstant(to)));
}

export function processingDuration(start: string | null | undefined, end?: string | null, now = Date.now()): string {
  if (!start) return "Nie rozpoczęto";
  const minutes = Math.max(0, Math.floor(((end ? Date.parse(end) : now) - Date.parse(start)) / 60000));
  if (minutes < 1) return "poniżej minuty";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours} godz. ${minutes % 60} min` : `${Math.floor(hours / 24)} dni ${hours % 24} godz.`;
}
