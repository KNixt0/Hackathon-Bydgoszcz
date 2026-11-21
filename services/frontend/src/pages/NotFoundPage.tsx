import { Compass } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/States";

export function NotFoundPage() {
  return (
    <div className="page">
      <div className="panel">
        <EmptyState
          icon={<Compass />}
          title="Nie ma takiej strony"
          text="Adres nie prowadzi do żadnego widoku InvestWatch. Sprawdź odnośnik albo wróć do kolejki spraw."
          action={<Link className="btn btn--primary" to="/">Wróć do kolejki</Link>}
        />
      </div>
    </div>
  );
}
