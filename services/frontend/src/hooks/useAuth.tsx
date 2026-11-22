import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, errorMessage, setUnauthorizedHandler } from "../api/client";
import { api } from "../api/endpoints";
import type { User } from "../types/api";
import type { Role } from "../types/incident";

export type AuthState =
  | { phase: "loading"; user: null; demoLogin: boolean; notice: null }
  | { phase: "anonymous"; user: null; demoLogin: boolean; notice: string | null }
  | { phase: "authenticated"; user: User; demoLogin: boolean; notice: null };

interface AuthContextValue {
  state: AuthState;
  /** Resolve to null on success or a Polish message for the form. */
  login: (email: string, password: string) => Promise<string | null>;
  demoLogin: (role: Role) => Promise<string | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const SESSION_EXPIRED = "Sesja wygasła albo została zakończona. Zaloguj się ponownie, aby kontynuować.";

function loginError(err: unknown): string {
  if (err instanceof ApiError && err.status === 401) {
    return "Ten adres e-mail i hasło nie pasują do żadnego konta. Sprawdź oba pola i spróbuj ponownie.";
  }
  if (err instanceof ApiError && err.status === 404) return "Logowanie na konta demonstracyjne jest wyłączone na tym serwerze.";
  return errorMessage(err);
}

/** Owns the session: who is logged in, and the switch back to the login page on any 401. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ phase: "loading", user: null, demoLogin: false, notice: null });

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      let demoLogin = false;
      try {
        const config = await api.authConfig(controller.signal);
        demoLogin = Boolean(config.demo_login);
        // No session cookie: skip /me, whose 401 would only add noise to the browser console.
        if (config.authenticated === false) {
          setState({ phase: "anonymous", user: null, demoLogin, notice: null });
          return;
        }
        const { user } = await api.me(controller.signal);
        setState({ phase: "authenticated", user, demoLogin, notice: null });
      } catch (err) {
        if (controller.signal.aborted) return;
        const notice = err instanceof ApiError && err.status === 401 ? null : errorMessage(err);
        setState({ phase: "anonymous", user: null, demoLogin, notice });
      }
    })();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() =>
      setState((prev) => (prev.phase === "authenticated" ? { phase: "anonymous", user: null, demoLogin: prev.demoLogin, notice: SESSION_EXPIRED } : prev)),
    );
    return () => setUnauthorizedHandler(null);
  }, []);

  const start = useCallback(async (call: () => Promise<{ user: User }>) => {
    try {
      const { user } = await call();
      setState((prev) => ({ phase: "authenticated", user, demoLogin: prev.demoLogin, notice: null }));
      return null;
    } catch (err) {
      return loginError(err);
    }
  }, []);

  const login = useCallback((email: string, password: string) => start(() => api.login(email, password)), [start]);
  const demoLogin = useCallback((role: Role) => start(() => api.demoLogin(role)), [start]);
  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // the cookie may already be gone; the UI logs out either way
    }
    setState((prev) => ({ phase: "anonymous", user: null, demoLogin: prev.demoLogin, notice: null }));
  }, []);

  const value = useMemo(() => ({ state, login, demoLogin, logout }), [state, login, demoLogin, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** The logged-in user; only valid inside the guarded part of the app. */
export function useUser(): User {
  const { state } = useAuth();
  if (state.phase !== "authenticated") throw new Error("useUser must be used behind the route guard");
  return state.user;
}
