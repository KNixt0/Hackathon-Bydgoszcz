export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;

/** The auth provider registers here: any 401 outside /api/auth/* ends the session in the UI. */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  onUnauthorized = handler;
}

function notifyUnauthorized(path: string, status: number) {
  if (status === 401 && !path.startsWith("/api/auth/")) onUnauthorized?.();
}

const NETWORK_MESSAGE = "Brak połączenia z serwerem. Sprawdź, czy usługa backend działa, i spróbuj ponownie.";

function statusMessage(status: number): string {
  if (status === 401) return "Sesja wygasła. Zaloguj się ponownie.";
  if (status === 403) return "Ta czynność wymaga uprawnień kierownika.";
  if (status === 404) return "Nie znaleziono zasobu.";
  if (status === 409) return "Tej zmiany nie można wykonać na obecnym etapie sprawy. Odśwież sprawę i spróbuj ponownie.";
  if (status === 429) return "Zbyt wiele prób. Spróbuj ponownie za kilka minut.";
  if (status === 422) return "Serwer odrzucił dane jako nieprawidłowe.";
  if (status >= 500) return "Serwer zwrócił błąd. Spróbuj ponownie za chwilę.";
  return `Żądanie nie powiodło się (kod ${status}).`;
}

const KNOWN_STATUSES = new Set([401, 403, 409, 429]);

async function detailOf(res: Response): Promise<string | null> {
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) return detail;
    }
  } catch {
    // body is not JSON: fall back to the status message
  }
  return null;
}

/** Every failure becomes an ApiError with a Polish, user-presentable message. Never throws anything else. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(NETWORK_MESSAGE, 0);
  }
  if (!res.ok) {
    notifyUnauthorized(path, res.status);
    // The backend's `detail` strings are English and technical: Polish messages for the known statuses.
    const detail = KNOWN_STATUSES.has(res.status) ? null : await detailOf(res);
    throw new ApiError(detail ?? statusMessage(res.status), res.status);
  }
  if (res.status === 204) return undefined as T;
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError("Serwer zwrócił nieczytelną odpowiedź.", res.status);
  }
}

export async function requestText(path: string, init?: RequestInit): Promise<string> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(NETWORK_MESSAGE, 0);
  }
  if (!res.ok) {
    notifyUnauthorized(path, res.status);
    throw new ApiError(statusMessage(res.status), res.status);
  }
  return res.text();
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Wystąpił nieoczekiwany błąd.";
}
