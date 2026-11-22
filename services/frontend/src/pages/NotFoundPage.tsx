import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="page">
      <div className="page__head">
        <h1 className="page__title">Nie ma takiej strony</h1>
        <p className="page__sub">Adres nie prowadzi do żadnego widoku WatchIT. Sprawdź odnośnik albo wróć do kolejki spraw.</p>
      </div>
      <p><Link className="btn btn--primary" to="/">Wróć do kolejki</Link></p>
    </div>
  );
}
