import { CircleAlert, LogIn, ScanEye, ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
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
    document.title = "Logowanie · InvestWatch";
    return () => {
      document.title = "InvestWatch · UKNF";
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
    <main className="login" id="tresc">
      <div className="login__card panel">
        <div className="login__brand">
          <span className="brand__mark" aria-hidden="true"><ScanEye /></span>
          <span>
            <span className="brand__name" style={{ display: "block" }}>InvestWatch</span>
            <span className="brand__org" style={{ display: "block" }}>UKNF · nadzór nad reklamą</span>
          </span>
        </div>
        <h1 className="login__title">Logowanie</h1>
        {notice && <p className="login__notice" role="status">{notice}</p>}
        <form className="login__form" onSubmit={submit} noValidate aria-busy={busy !== null}>
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
          {error && <p className="form-error" id="login-error" role="alert"><CircleAlert aria-hidden="true" />{error}</p>}
          <Button type="submit" variant="primary" disabled={busy !== null}>
            <LogIn aria-hidden="true" />{busy === "form" ? "Logowanie…" : "Zaloguj się"}
          </Button>
        </form>
        {state.demoLogin && (
          <section className="login__demo" aria-labelledby="login-demo-h">
            <p className="login__demo-title" id="login-demo-h">Konta demonstracyjne</p>
            <Button onClick={() => void demo("ANALYST")} disabled={busy !== null}>
              <UserRound aria-hidden="true" />Zaloguj jako analityk (demo)
            </Button>
            <Button onClick={() => void demo("SUPERVISOR")} disabled={busy !== null}>
              <ShieldCheck aria-hidden="true" />Zaloguj jako kierownik (demo)
            </Button>
          </section>
        )}
        <p className="login__foot"><Link to="/zglos">Zgłoś ofertę lub reklamę</Link></p>
        <p className="login__foot">Dostęp tylko dla pracowników UKNF. Logowania i decyzje w sprawach są zapisywane w dzienniku audytu.</p>
      </div>
    </main>
  );
}
