import { useCallback, useRef } from "react";

/**
 * Radix dialogs return focus to their own Trigger; ours are opened from elsewhere (header buttons, Ctrl+K,
 * workflow actions, evidence links). Remember what had focus when the dialog opened and return there on close.
 */
export function useRestoreFocus(fallbackId?: string) {
  const last = useRef<HTMLElement | null>(null);
  const remember = useCallback(() => {
    const active = document.activeElement;
    if (active instanceof HTMLElement && active !== document.body) last.current = active;
  }, []);
  const restore = useCallback((event: Event) => {
    const el = last.current;
    last.current = null;
    // The trigger can disappear (a workflow step changes the available actions): fall back to a stable landmark.
    const target = el && el.isConnected ? el : fallbackId ? document.getElementById(fallbackId) : null;
    if (target) {
      event.preventDefault();
      target.focus();
    }
  }, [fallbackId]);
  return { remember, restore };
}
