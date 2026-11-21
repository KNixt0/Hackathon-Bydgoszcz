import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export interface Notice {
  id: number;
  tone: "info" | "success" | "error";
  text: string;
}

interface UiContextValue {
  paletteOpen: boolean;
  setPaletteOpen: (open: boolean) => void;
  scanOpen: boolean;
  setScanOpen: (open: boolean) => void;
  notices: Notice[];
  notify: (tone: Notice["tone"], text: string) => void;
  dismissNotice: (id: number) => void;
}

const UiContext = createContext<UiContextValue | null>(null);
let nextNoticeId = 1;

export function UiProvider({ children }: { children: ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [scanOpen, setScanOpen] = useState(false);
  const [notices, setNotices] = useState<Notice[]>([]);

  const dismissNotice = useCallback((id: number) => setNotices((prev) => prev.filter((n) => n.id !== id)), []);
  const notify = useCallback(
    (tone: Notice["tone"], text: string) => {
      const id = nextNoticeId++;
      setNotices((prev) => [...prev.slice(-3), { id, tone, text }]);
      if (tone !== "error") window.setTimeout(() => dismissNotice(id), 6000);
    },
    [dismissNotice],
  );

  const value = useMemo(
    () => ({ paletteOpen, setPaletteOpen, scanOpen, setScanOpen, notices, notify, dismissNotice }),
    [paletteOpen, scanOpen, notices, notify, dismissNotice],
  );
  return <UiContext.Provider value={value}>{children}</UiContext.Provider>;
}

export function useUi(): UiContextValue {
  const ctx = useContext(UiContext);
  if (!ctx) throw new Error("useUi must be used inside UiProvider");
  return ctx;
}
