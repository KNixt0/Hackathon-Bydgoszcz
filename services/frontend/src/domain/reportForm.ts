import type { ReportCategory } from "../types/api";

export const COMMENT_MAX = 500;
export const URL_MAX = 2048;

export type CategoryChoice = "unknown" | "1" | "2" | "3";
export const CATEGORY_CHOICES: { value: CategoryChoice; label: string }[] = [
  { value: "1", label: "reklama influencera lub podmiotu trzeciego" },
  { value: "2", label: "materiał firmy inwestycyjnej" },
  { value: "3", label: "doradztwo bez zezwolenia" },
  { value: "unknown", label: "nie wiem" },
];

export function categoryOf(choice: CategoryChoice): ReportCategory | null {
  return choice === "unknown" ? null : (Number(choice) as ReportCategory);
}

/** Polish message that says what to do, or null when the address is fine. */
export function validateReportUrl(raw: string): string | null {
  const value = raw.trim();
  if (!value) return "Wpisz adres strony lub posta, który chcesz zgłosić.";
  if (value.length > URL_MAX) return "Ten adres jest zbyt długi. Wklej krótszy link do strony lub posta.";
  if (!/^https?:\/\//i.test(value)) return "Adres powinien zaczynać się od http:// lub https://, na przykład https://przyklad.pl/oferta.";
  try {
    const parsed = new URL(value);
    if (!parsed.hostname.includes(".") && parsed.hostname !== "localhost") throw new Error("host");
    if (parsed.username || parsed.password) return "Usuń z adresu nazwę użytkownika i hasło, a następnie spróbuj ponownie.";
  } catch {
    return "Nie rozpoznajemy tego adresu. Skopiuj go w całości z paska przeglądarki lub z opcji „Udostępnij”.";
  }
  return null;
}
