import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { DEFAULT_THRESHOLDS, normalizeThresholds, type Thresholds } from "../domain/levels";

// v2: the default orange (flag) threshold moved from 35 to 20 with incident contract v2; v1 values are ignored.
const STORAGE_KEY = "investwatch.thresholds.v2";
const LEGACY_KEYS = ["investwatch.thresholds.v1"];

export function readStoredThresholds(): Thresholds {
  try {
    for (const key of LEGACY_KEYS) window.localStorage.removeItem(key);
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_THRESHOLDS;
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object") return normalizeThresholds(parsed as Partial<Thresholds>);
  } catch {
    // storage blocked or corrupted: fall back to defaults
  }
  return DEFAULT_THRESHOLDS;
}

function store(t: Thresholds) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
  } catch {
    // storage unavailable: the threshold still applies for this session
  }
}

interface ThresholdsContextValue {
  thresholds: Thresholds;
  setThresholds: (next: Partial<Thresholds>) => void;
  reset: () => void;
  isDefault: boolean;
}

const ThresholdsContext = createContext<ThresholdsContextValue | null>(null);

export function ThresholdsProvider({ children, initial }: { children: ReactNode; initial?: Thresholds }) {
  const [thresholds, setState] = useState<Thresholds>(() => initial ?? readStoredThresholds());

  const setThresholds = useCallback((next: Partial<Thresholds>) => {
    setState((prev) => {
      let merged = { ...prev, ...next };
      // The flag threshold is primary: the critical threshold never drops below it, and raising
      // the flag threshold past the critical one pushes the critical one along.
      if (next.red !== undefined && next.orange === undefined && merged.red < merged.orange) merged = { ...merged, red: merged.orange };
      if (next.orange !== undefined && next.red === undefined && merged.orange > merged.red) merged = { ...merged, red: merged.orange };
      const normalized = normalizeThresholds(merged);
      store(normalized);
      return normalized;
    });
  }, []);

  const reset = useCallback(() => setThresholds(DEFAULT_THRESHOLDS), [setThresholds]);

  const value = useMemo(
    () => ({
      thresholds,
      setThresholds,
      reset,
      isDefault: thresholds.red === DEFAULT_THRESHOLDS.red && thresholds.orange === DEFAULT_THRESHOLDS.orange,
    }),
    [thresholds, setThresholds, reset],
  );
  return <ThresholdsContext.Provider value={value}>{children}</ThresholdsContext.Provider>;
}

export function useThresholds(): ThresholdsContextValue {
  const ctx = useContext(ThresholdsContext);
  if (!ctx) throw new Error("useThresholds must be used inside ThresholdsProvider");
  return ctx;
}
