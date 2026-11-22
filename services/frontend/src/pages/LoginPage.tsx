import { CircleAlert, Info } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { PublicHeader } from "../components/layout/PublicHeader";
import { Button } from "../components/ui/Button";
import { useAuth } from "../hooks/useAuth";
import type { Role } from "../types/incident";

function target(state: unknown): string {
  const from = state && typeof state === "object" && "from" in state ? (state as { from: unknown }).from : null;
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("/logowanie") ? from : "/";
}

export function LoginPage() {
  const { state, login, demoLogin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"form" | Role | null>(null);

  useEffect(() => {
    document.title = "Logowanie · WatchIT";
    return () => {
      document.title = "WatchIT · UKNF";
    };
  }, []);

  if (state.phase === "authenticated") return <Navigate to={target(location.state)} replace />;

  const finish = (failure: string | null) => {
    setBusy(null);
    if (failure) setError(failure);
    else navigate(target(location.state), { replace: true });
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Wpisz adres e-mail i hasło.");
      return;
    }
    setBusy("form");
    setError(null);
    finish(await login(email.trim(), password));
  };

  const demo = async (role: Role) => {
    setBusy(role);
    setError(null);
    finish(await demoLogin(role));
  };

  const notice = state.phase === "anonymous" ? state.notice : null;

  return (
    <div className="shell">
      <PublicHeader linkTo="/logowanie" />
      <main className="login" id="tresc">
        <h1 className="page__title">Logowanie</h1>
        <p className="page__sub">Zaloguj się, aby pracować w kolejce spraw.</p>
        {notice && (
          <p className="callout callout--compact login__notice" role="status">
            <span className="callout__lead"><Info aria-hidden="true" />{notice}</span>
          </p>
        )}
        <form className="panel login__form" onSubmit={submit} noValidate aria-busy={busy !== null}>
          {error && (
            <div className="callout callout--error callout--compact" id="login-error" role="alert">
              <span className="callout__lead"><CircleAlert aria-hidden="true" />{error}</span>
            </div>
          )}
          <label className="field">
            <span className="field__label">Adres e-mail</span>
            <input
              className="input" type="email" name="email" autoComplete="username" autoFocus value={email}
              aria-invalid={error ? true : undefined} aria-describedby={error ? "login-error" : undefined}
              onChange={(e) => { setEmail(e.target.value); if (error) setError(null); }}
            />
          </label>
          <label className="field">
            <span className="field__label">Hasło</span>
            <input
              className="input" type="password" name="password" autoComplete="current-password" value={password}
              aria-invalid={error ? true : undefined} aria-describedby={error ? "login-error" : undefined}
              onChange={(e) => { setPassword(e.target.value); if (error) setError(null); }}
            />
          </label>
          <div>
            <Button type="submit" variant="primary" disabled={busy !== null}>{busy === "form" ? "Logowanie…" : "Zaloguj się"}</Button>
          </div>
        </form>
        {state.demoLogin && (
          <section className="login__demo" aria-labelledby="login-demo-h">
            <h2 className="subhead" id="login-demo-h">Konta demonstracyjne</h2>
            <p className="field__hint">Dostęp bez hasła, tylko w trybie demonstracyjnym.</p>
            <div className="login__demo-acts">
              <Button onClick={() => void demo("ANALYST")} disabled={busy !== null}>Zaloguj jako analityk (konto demonstracyjne)</Button>
              <Button onClick={() => void demo("SUPERVISOR")} disabled={busy !== null}>Zaloguj jako kierownik (konto demonstracyjne)</Button>
            </div>
          </section>
        )}
        <p className="login__foot">Narzędzie analityczne UKNF, dane przetwarzane lokalnie. Logowania i decyzje w sprawach są zapisywane w dzienniku audytu.</p>
      </main>
    </div>
  );
}
