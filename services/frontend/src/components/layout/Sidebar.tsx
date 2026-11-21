import { Inbox, ScanEye, SlidersHorizontal } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import type { LevelCounts, Thresholds } from "../../domain/levels";
import type { ConnectionStatus } from "../../hooks/useLive";
import { ConnectionIndicator } from "./ConnectionIndicator";

interface Props {
  thresholds: Thresholds;
  thresholdsAreDefault: boolean;
  counts: LevelCounts | null;
  connection: ConnectionStatus;
}

export function Sidebar({ thresholds, thresholdsAreDefault, counts, connection }: Props) {
  return (
    <aside className="sidebar">
      <Link to="/" className="brand" aria-label="InvestWatch, kolejka spraw">
        <span className="brand__mark" aria-hidden="true"><ScanEye /></span>
        <span>
          <span className="brand__name">InvestWatch</span>
          <span className="brand__org" style={{ display: "block" }}>UKNF · nadzór nad reklamą</span>
        </span>
      </Link>

      <nav className="nav" aria-label="Główna nawigacja">
        <NavLink to="/" end className="nav__link">
          <Inbox aria-hidden="true" />
          <span className="nav__label">Kolejka spraw</span>
          {counts && counts.red + counts.orange > 0 && (
            <span
              className={`nav__count${counts.red > 0 ? " nav__count--red" : ""}`}
              title={`Oflagowane: ${counts.red + counts.orange} (krytyczne ${counts.red}, do weryfikacji ${counts.orange})`}
              data-testid="nav-flagged"
            >
              {counts.red + counts.orange}<span className="sr-only"> oflagowanych</span>
            </span>
          )}
        </NavLink>
        <NavLink to="/kalibracja" className="nav__link">
          <SlidersHorizontal aria-hidden="true" />
          <span className="nav__label">Kalibracja</span>
        </NavLink>
      </nav>

      <div className="sidebar__section">
        <p className="sidebar__section-title">Obowiązujące progi ryzyka</p>
        <Link to="/kalibracja" className="threshold-card">
          <span className="threshold-card__row"><span>Flagowanie od</span><strong className="num">{thresholds.orange}</strong></span>
          <span className="threshold-card__row"><span>Krytyczne od</span><strong className="num">{thresholds.red}</strong></span>
          <span className="threshold-card__note" style={{ display: "block" }}>
            {thresholdsAreDefault ? "Wartości domyślne" : "Zmienione przez analityka"}
          </span>
        </Link>
      </div>

      <div className="sidebar__foot">
        <ConnectionIndicator status={connection} />
        <span className="sidebar__version">Prototyp · dane przetwarzane lokalnie</span>
      </div>
    </aside>
  );
}
