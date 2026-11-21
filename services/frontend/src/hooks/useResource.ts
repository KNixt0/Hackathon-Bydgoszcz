import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "../api/client";

export type Resource<T> =
  | { phase: "loading"; data: null; error: null }
  | { phase: "error"; data: null; error: string }
  | { phase: "ready"; data: T; error: null };

export interface UseResource<T> {
  resource: Resource<T>;
  reload: () => void;
  /** Re-fetch without dropping the data already on screen (used after live events). */
  refresh: () => void;
  setData: (data: T) => void;
}

/**
 * Loads one resource; failures are captured into state (never thrown, never logged).
 * `key` identifies the resource: when it changes the previous data is dropped.
 */
export function useResource<T>(loader: (signal: AbortSignal) => Promise<T>, key: string): UseResource<T> {
  const [state, setState] = useState<{ key: string; resource: Resource<T> }>({
    key,
    resource: { phase: "loading", data: null, error: null },
  });
  const [tick, setTick] = useState({ n: 0, silent: false });

  useEffect(() => {
    const controller = new AbortController();
    if (!tick.silent) setState({ key, resource: { phase: "loading", data: null, error: null } });
    loader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ key, resource: { phase: "ready", data, error: null } });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        // A failed background refresh keeps the last good data on screen.
        setState((prev) =>
          tick.silent && prev.key === key && prev.resource.phase === "ready"
            ? prev
            : { key, resource: { phase: "error", data: null, error: errorMessage(err) } },
        );
      });
    return () => controller.abort();
    // `loader` is intentionally identified by `key`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tick]);

  const reload = useCallback(() => setTick((t) => ({ n: t.n + 1, silent: false })), []);
  const refresh = useCallback(() => setTick((t) => ({ n: t.n + 1, silent: true })), []);
  const setData = useCallback((data: T) => setState({ key, resource: { phase: "ready", data, error: null } }), [key]);

  const resource: Resource<T> = state.key === key ? state.resource : { phase: "loading", data: null, error: null };
  return { resource, reload, refresh, setData };
}
