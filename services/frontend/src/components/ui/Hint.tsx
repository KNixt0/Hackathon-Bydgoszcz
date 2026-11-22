import { useId, type ReactNode } from "react";

/**
 * A small tooltip shown on hover and on keyboard focus (no extra dependency). The trigger is focusable
 * and points at the bubble with aria-describedby, so screen readers read the definition too.
 */
export function Hint({ children, text }: { children: ReactNode; text: string }) {
  const id = useId();
  return (
    <span className="hint">
      <span className="hint__trigger" tabIndex={0} aria-describedby={id}>{children}</span>
      <span className="hint__bubble" role="tooltip" id={id}>{text}</span>
    </span>
  );
}
