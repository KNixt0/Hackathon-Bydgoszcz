import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { errorMessage } from "../api/client";
import { api } from "../api/endpoints";
import { DEFAULT_THRESHOLDS, normalizeThresholds, type Thresholds } from "../domain/levels";
import type { ThresholdSettings } from "../types/api";

// The local preview (this browser only). v2: the default flag threshold moved from 35 to 20; v1 values are ignored.
const STORAGE_KEY = "investwatch.thresholds.v2"; // key kept from before the WatchIt rename
const LEGACY_KEYS = ["investwatch.thresholds.v1"];

export function readStoredThresholds(): Thresholds | null {
  try {
    for (const key of LEGACY_KEYS) window.localStorage.removeItem(key);
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object") return normalizeThresholds(parsed as Partial<Thresholds>);
  } catch {
    // storage blocked or corrupted: no preview
  }
  return null;
}

function store(t: Thresholds | null) {
  try {
    if (t) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // storage unavailable: the preview still applies for this session
  }
}

export const fromSettings = (s: Pick<ThresholdSettings, "flag" | "critical">): Thresholds =>
  normalizeThresholds({ orange: s.flag, red: s.critical });

interface ThresholdsContextValue {
  /** What the whole UI uses: the local preview if there is one, otherwise the global thresholds. */
  thresholds: Thresholds;
  setThresholds: (next: Partial<Thresholds>) => void;
  /** Drops the local preview: back to the global thresholds. */
  reset: () => void;
  /** The shared thresholds from the server (null until loaded or when the server could not be reached). */
  global: ThresholdSettings | null;
  globalThresholds: Thresholds;
  /** The preview equals the global thresholds. */
  isGlobal: boolean;
  /** Supervisor only: stores the current thresholds as the global ones. Resolves to null or an error message. */
  saveGlobal: () => Promise<string | null>;
  /** Bumps after every recorded change, so the calibration history can refresh. */
  historyRevision: number;
}

const ThresholdsContext = createContext<ThresholdsContextValue | null>(null);

export function ThresholdsProvider({ children, initial }: { children: ReactNode; initial?: Thresholds }) {
  const [preview, setPreview] = useState<Thresholds | null>(() => initial ?? readStoredThresholds());
  const [global, setGlobal] = useState<ThresholdSettings | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    api
      .thresholds(controller.signal)
      .then((s) => {
        if (!controller.signal.aborted) setGlobal(s);
      })
      .catch(() => {
        // offline or not allowed: the defaults stay in force locally
      });
    return () => controller.abort();
  }, []);

  const globalThresholds = useMemo(() => (global ? fromSettings(global) : DEFAULT_THRESHOLDS), [global]);
  const thresholds = preview ?? globalThresholds;

  // WatchIt: a user's own thresholds are recorded in the calibration history (who changed what), once the
  // slider has settled. Silent: no notification, a failed write never disturbs the screen.
  const [historyRevision, setHistoryRevision] = useState(0);
  const lastRecorded = useRef<string | null>(null);
  useEffect(() => {
    if (!preview) return;
    const key = `${preview.orange}/${preview.red}`;
    if (key === lastRecorded.current) return;
    const timer = window.setTimeout(() => {
      lastRecorded.current = key;
      api.recordPreview(preview.orange, preview.red)
        .then(() => setHistoryRevision((r) => r + 1))
        .catch(() => {
          // offline or session ended: the preview still applies locally
        });
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [preview]);

  const setThresholds = useCallback(
    (next: Partial<Thresholds>) => {
      setPreview((prev) => {
        const base = prev ?? globalThresholds;
        let merged = { ...base, ...next };
        // The flag threshold is primary: the critical threshold never drops below it, and raising
        // the flag threshold past the critical one pushes the critical one along.
        if (next.red !== undefined && next.orange === undefined && merged.red < merged.orange) merged = { ...merged, red: merged.orange };
        if (next.orange !== undefined && next.red === undefined && merged.orange > merged.red) merged = { ...merged, red: merged.orange };
        const normalized = normalizeThresholds(merged);
        store(normalized);
        return normalized;
      });
    },
    [globalThresholds],
  );

  const reset = useCallback(() => {
    store(null);
    setPreview(null);
  }, []);

  const saveGlobal = useCallback(async () => {
    try {
      const saved = await api.saveThresholds(thresholds.orange, thresholds.red);
      setGlobal(saved);
      store(null);
      setPreview(null);
      setHistoryRevision((r) => r + 1);
      return null;
    } catch (err) {
      return errorMessage(err);
    }
  }, [thresholds]);

  const value = useMemo(
    () => ({
      thresholds,
      setThresholds,
      reset,
      global,
      globalThresholds,
      isGlobal: thresholds.red === globalThresholds.red && thresholds.orange === globalThresholds.orange,
      saveGlobal,
      historyRevision,
    }),
    [thresholds, setThresholds, reset, global, globalThresholds, saveGlobal, historyRevision],
  );
  return <ThresholdsContext.Provider value={value}>{children}</ThresholdsContext.Provider>;
}

export function useThresholds(): ThresholdsContextValue {
  const ctx = useContext(ThresholdsContext);
  if (!ctx) throw new Error("useThresholds must be used inside ThresholdsProvider");
  return ctx;
}
