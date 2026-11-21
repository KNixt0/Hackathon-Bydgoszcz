import { Radar, Search } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "../ui/Button";

interface Props {
  onOpenPalette: () => void;
  onOpenScan: () => void;
  shortcutLabel: string;
  children?: ReactNode;
  /** After the primary action (the signed-in user). */
  trailing?: ReactNode;
}

export function TopBar({ onOpenPalette, onOpenScan, shortcutLabel, children, trailing }: Props) {
  return (
    <header className="topbar">
      <button type="button" className="topbar__search" onClick={onOpenPalette} aria-label="Otwórz paletę poleceń">
        <Search aria-hidden="true" />
        <span>Szukaj sprawy lub polecenia</span>
        <kbd className="kbd">{shortcutLabel}</kbd>
      </button>
      <span className="topbar__spacer" />
      {children}
      <Button variant="primary" onClick={onOpenScan}>
        <Radar aria-hidden="true" />
        Skanuj URL
      </Button>
      {trailing}
    </header>
  );
}
