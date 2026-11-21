import { CircleAlert, RotateCw } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { Button } from "./Button";

export function Skeleton({ width = "100%", height = 14, style }: { width?: number | string; height?: number | string; style?: CSSProperties }) {
  return <span className="skeleton" aria-hidden="true" style={{ width, height, ...style }} />;
}

interface EmptyProps {
  title: string;
  text?: ReactNode;
  /** Kept for call sites; the language has no icon discs in empty states, so it is not drawn. */
  icon?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

/** One title, one sentence, one action. Left aligned, no illustration. */
export function EmptyState({ title, text, action, compact = false }: EmptyProps) {
  return (
    <div className={`state${compact ? " state--compact" : ""}`} data-testid="empty-state">
      <p className="state__title">{title}</p>
      {text && <p className="state__text">{text}</p>}
      {action && <div className="state__actions">{action}</div>}
    </div>
  );
}

export function ErrorState({ title = "Nie udało się wczytać danych", message, onRetry, compact = false }: { title?: string; message: string; onRetry?: () => void; compact?: boolean }) {
  return (
    <div className={`state state--error${compact ? " state--compact" : ""}`} role="alert">
      <p className="state__title"><CircleAlert aria-hidden="true" />{title}</p>
      <p className="state__text">{message}</p>
      {onRetry && (
        <div className="state__actions">
          <Button onClick={onRetry}><RotateCw aria-hidden="true" />Spróbuj ponownie</Button>
        </div>
      )}
    </div>
  );
}
