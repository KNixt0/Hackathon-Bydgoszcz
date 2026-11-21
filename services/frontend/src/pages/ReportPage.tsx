import { CircleAlert, CircleCheck } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ApiError, errorMessage } from "../api/client";
import { api } from "../api/endpoints";
import { PublicHeader } from "../components/layout/PublicHeader";
import { Button } from "../components/ui/Button";
import { CATEGORY_CHOICES, categoryOf, COMMENT_MAX, validateReportUrl, type CategoryChoice } from "../domain/reportForm";

function failureMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 429) return "Z tego urządzenia wysłano już wiele zgłoszeń. Spróbuj ponownie za godzinę.";
    if (err.status === 422) return "Nie udało nam się sprawdzić tego adresu. Upewnij się, że to publiczny adres strony lub posta, i spróbuj ponownie.";
  }
  return errorMessage(err);
}

/** Public page: no login, no dashboard chrome, no live socket. */
export function ReportPage() {
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState<CategoryChoice>("unknown");
  const [comment, setComment] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    document.title = "Zgłoś ofertę lub reklamę · InvestWatch";
    return () => {
      document.title = "InvestWatch · UKNF";
    };
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = validateReportUrl(url);
    setUrlError(problem);
    if (problem) return;
    setBusy(true);
    setFormError(null);
    try {
      const trimmed = comment.trim();
      await api.submitReport({ url: url.trim(), category_hint: categoryOf(category), ...(trimmed ? { comment: trimmed } : {}) });
      setSent(true);
    } catch (err) {
      setFormError(failureMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const again = () => {
    setUrl("");
    setComment("");
    setCategory("unknown");
    setUrlError(null);
    setFormError(null);
    setSent(false);
  };

  return (
    <div className="shell">
      <PublicHeader />
      <main className="report" id="tresc">
        <h1 className="page__title">Zgłoś ofertę lub reklamę</h1>
        {sent ? (
          <div className="callout report__done" role="status">
            <h2 className="callout__title report__done-title"><CircleCheck aria-hidden="true" />Zgłoszenie przyjęte</h2>
            <p>Dziękujemy. Pracownicy UKNF sprawdzą wskazany materiał. Nie odpowiadamy indywidualnie na zgłoszenia i nie podajemy informacji o prowadzonych sprawach.</p>
            <div className="callout__acts"><Button onClick={again}>Wyślij kolejne zgłoszenie</Button></div>
          </div>
        ) : (
          <>
            <p className="page__sub">
              Możesz zgłosić adres strony lub posta, który wygląda na reklamę inwestycji bez wymaganych ostrzeżeń, ofertę
              „pewnego zysku”, promocję produktu finansowego przez influencera albo doradztwo inwestycyjne bez zezwolenia.
              Zgłoszenie trafi do kolejki analityków UKNF. Nie wymaga logowania ani podawania danych osobowych.
            </p>
            <form className="panel report__form" onSubmit={submit} noValidate aria-busy={busy}>
              {formError && (
                <div className="callout callout--error callout--compact" role="alert">
                  <span className="callout__lead"><CircleAlert aria-hidden="true" />{formError}</span>
                </div>
              )}
              <div className="field">
                <label className="field__label" htmlFor="report-url">Adres strony lub posta (URL)</label>
                <span className="field__hint" id="report-url-hint">Wymagane. Pełny adres, np. https://przyklad.pl/oferta</span>
                <input
                  id="report-url" className="input" type="url" name="url" inputMode="url" autoComplete="off" autoFocus value={url} maxLength={2048}
                  aria-required="true" aria-invalid={urlError ? true : undefined}
                  aria-describedby={urlError ? "report-url-hint report-url-error" : "report-url-hint"}
                  onChange={(e) => { setUrl(e.target.value); if (urlError) setUrlError(null); }}
                  onBlur={() => setUrlError(url ? validateReportUrl(url) : null)}
                />
                {urlError && <span className="form-error" id="report-url-error" role="alert"><CircleAlert aria-hidden="true" />{urlError}</span>}
              </div>

              <fieldset className="report__choices">
                <legend className="field__label">Czego dotyczy zgłoszenie</legend>
                {CATEGORY_CHOICES.map((c) => (
                  <label key={c.value} className="report__choice">
                    <input type="radio" name="category" value={c.value} checked={category === c.value} onChange={() => setCategory(c.value)} />
                    <span>{c.label}</span>
                  </label>
                ))}
              </fieldset>

              <div className="field">
                <label className="field__label" htmlFor="report-comment">Uwagi (opcjonalnie)</label>
                <textarea
                  id="report-comment" className="input textarea" name="comment" rows={4} maxLength={COMMENT_MAX} value={comment}
                  aria-describedby="report-comment-count" onChange={(e) => setComment(e.target.value)}
                />
                <span className="report__count" id="report-comment-count" aria-live="off">{comment.length} / {COMMENT_MAX} znaków</span>
              </div>

              <div>
                <Button type="submit" variant="primary" disabled={busy}>{busy ? "Wysyłanie…" : "Wyślij zgłoszenie"}</Button>
              </div>
            </form>
            <p className="report__privacy">
              Twój adres IP nie jest zapisywany. Przechowujemy wyłącznie jego skrót (hash), którego używamy tylko do ograniczania nadużyć, na przykład
              wielokrotnego wysyłania tego samego zgłoszenia.
            </p>
          </>
        )}
        <p className="report__foot"><Link to="/logowanie">Logowanie dla pracowników UKNF</Link></p>
      </main>
    </div>
  );
}
