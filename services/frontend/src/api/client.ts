export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const NETWORK_MESSAGE = "Brak połączenia z serwerem. Sprawdź, czy usługa backend działa, i spróbuj ponownie.";

function statusMessage(status: number): string {
  if (status === 404) return "Nie znaleziono zasobu.";
  if (status === 422) return "Serwer odrzucił dane jako nieprawidłowe.";
  if (status >= 500) return "Serwer zwrócił błąd. Spróbuj ponownie za chwilę.";
  return `Żądanie nie powiodło się (kod ${status}).`;
}

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
    const detail = await detailOf(res);
    throw new ApiError(detail ?? statusMessage(res.status), res.status);
  }
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
  if (!res.ok) throw new ApiError(statusMessage(res.status), res.status);
  return res.text();
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Wystąpił nieoczekiwany błąd.";
}
