import { Radar, Search } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { Button } from "../ui/Button";

interface Props {
  onOpenPalette: () => void;
  onOpenScan: () => void;
  shortcutLabel: string;
  isSupervisor: boolean;
  /** Jobs and demo menus, connection state: link-style items in the quick-action group. */
  children?: ReactNode;
  /** The signed-in user and "Wyloguj". */
  trailing?: ReactNode;
}

const TABS = [
  { to: "/", label: "Kolejka spraw", match: (p: string) => p === "/" || p.startsWith("/sprawy/") },
  { to: "/kalibracja", label: "Kalibracja", match: (p: string) => p.startsWith("/kalibracja") },
  { to: "/audyt", label: "Dziennik audytu", match: (p: string) => p.startsWith("/audyt"), supervisor: true },
];

/** Two stacked rows: service name and quick actions; then the section tabs (replaces the left sidebar). */
export function Header({ onOpenPalette, onOpenScan, shortcutLabel, isSupervisor, children, trailing }: Props) {
  const { pathname } = useLocation();
  const compact = useMediaQuery("(max-width: 960px)");
  return (
    <header className="hd">
      <div className="hd__top">
        <Link to="/" className="hd__svc" aria-label="Watchit, kolejka spraw">
          <span className="hd__name">Watchit</span>
        </Link>
        <div className="hd__qa">
          <span className="hd__actions">
            {!compact && (<Button
              onClick={onOpenPalette} aria-keyshortcuts="Control+K Meta+K"
              title={`Szukaj sprawy lub polecenia (${shortcutLabel})`}
            >
              <Search aria-hidden="true" />Szukaj<kbd className="kbd hd__kbd" aria-hidden="true">{shortcutLabel}</kbd>
            </Button>)}
            <Button variant="primary" onClick={onOpenScan}>
              <Radar aria-hidden="true" />Analiza URL
            </Button>
          </span>
          {compact ? <details className="hd__compact"><summary>Menu</summary><div className="hd__compact-content"><Button
              onClick={onOpenPalette} aria-keyshortcuts="Control+K Meta+K"
              title={`Szukaj sprawy lub polecenia (${shortcutLabel})`}
            >
              <Search aria-hidden="true" />Szukaj<kbd className="kbd hd__kbd" aria-hidden="true">{shortcutLabel}</kbd>
            </Button>{children}</div></details> : children}
          {trailing}
        </div>
      </div>
      <nav className="hd__nav" aria-label="Główna nawigacja">
        {TABS.filter((t) => !t.supervisor || isSupervisor).map((t) => {
          const exact = t.to === "/" ? pathname === "/" : t.match(pathname);
          const inSection = t.match(pathname);
          return (
            <Link key={t.to} to={t.to} className={`hd__tab${inSection ? " hd__tab--on" : ""}`} aria-current={exact ? "page" : undefined}>
              {t.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
