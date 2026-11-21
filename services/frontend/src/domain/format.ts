const dateFmt = new Intl.DateTimeFormat("pl-PL", { day: "2-digit", month: "2-digit", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("pl-PL", {
  day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
});
const shortDayFmt = new Intl.DateTimeFormat("pl-PL", { day: "numeric", month: "short" });
const dayMonthFmt = new Intl.DateTimeFormat("pl-PL", { day: "2-digit", month: "2-digit" });
const plnFmt = new Intl.NumberFormat("pl-PL", { style: "currency", currency: "PLN", maximumFractionDigits: 0 });
const compactFmt = new Intl.NumberFormat("pl-PL", { notation: "compact", maximumFractionDigits: 1 });

function parse(value: string | null | undefined): Date | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

export const formatDate = (v: string | null | undefined) => {
  const d = parse(v);
  return d ? dateFmt.format(d) : "brak danych";
};
export const formatDateTime = (v: string | null | undefined) => {
  const d = parse(v);
  return d ? dateTimeFmt.format(d) : "brak danych";
};
export const formatShortDay = (v: string) => {
  const d = parse(v);
  return d ? shortDayFmt.format(d) : v;
};
/** "21.11" for chart axes. */
export const formatDayMonth = (v: string) => {
  const d = parse(v);
  return d ? dayMonthFmt.format(d) : v;
};
export const formatPln = (v: number | null | undefined) => (v === null || v === undefined ? "brak danych" : plnFmt.format(v));
export const formatCompact = (v: number) => compactFmt.format(v);
export const formatPercent = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined ? "n/d" : `${(v * 100).toFixed(digits).replace(".", ",")}%`;
/** "1 zgłoszenie", "3 zgłoszenia", "5 zgłoszeń", "22 zgłoszenia". */
export function reportsLabel(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (n === 1) return "1 zgłoszenie";
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return `${n} zgłoszenia`;
  return `${n} zgłoszeń`;
}
export const formatScore = (v: number) => (Math.round(v * 10) / 10).toString().replace(".", ",");

export function relativeTime(v: string, now: Date = new Date()): string {
  const d = parse(v);
  if (!d) return "brak danych";
  const mins = Math.round((now.getTime() - d.getTime()) / 60000);
  if (mins < 1) return "przed chwilą";
  if (mins < 60) return `${mins} min temu`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} godz. temu`;
  const days = Math.round(hours / 24);
  if (days < 30) return days === 1 ? "wczoraj" : `${days} dni temu`;
  return dateFmt.format(d);
}

export function hostOf(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Only http(s) links are rendered as anchors; anything else is shown as plain text. */
export function safeHref(url: string | undefined | null): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : null;
  } catch {
    return null;
  }
}
