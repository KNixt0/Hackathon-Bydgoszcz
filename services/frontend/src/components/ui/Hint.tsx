import { useId, useState, type KeyboardEvent, type ReactNode } from "react";

/**
 * A small tooltip shown on hover and on keyboard focus (no extra dependency). The trigger is focusable
 * and points at the bubble with aria-describedby, so screen readers read the definition too.
 * Escape hides it without moving focus (WCAG 1.4.13, as in the criterion tooltip from #33).
 */
export function Hint({ children, text }: { children: ReactNode; text: string }) {
  const id = useId();
  const [dismissed, setDismissed] = useState(false);
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape" && !dismissed) {
      event.stopPropagation();
      setDismissed(true);
    }
  };
  return (
    <span className={`hint${dismissed ? " hint--dismissed" : ""}`} onMouseLeave={() => setDismissed(false)}>
      <span className="hint__trigger" tabIndex={0} aria-describedby={id} onKeyDown={onKeyDown} onBlur={() => setDismissed(false)}>
        {children}
      </span>
      <span className="hint__bubble" role="tooltip" id={id}>{text}</span>
    </span>
  );
}
