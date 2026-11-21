import { CircleAlert, Inbox, RotateCw } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { Button } from "./Button";

export function Skeleton({ width = "100%", height = 14, style }: { width?: number | string; height?: number | string; style?: CSSProperties }) {
  return <span className="skeleton" aria-hidden="true" style={{ width, height, ...style }} />;
}

interface EmptyProps {
  title: string;
  text?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ title, text, icon, action, compact = false }: EmptyProps) {
  return (
    <div className={`state${compact ? " state--compact" : ""}`} data-testid="empty-state">
      <span className="state__icon" aria-hidden="true">{icon ?? <Inbox />}</span>
      <p className="state__title">{title}</p>
      {text && <p className="state__text">{text}</p>}
      {action && <div className="state__actions">{action}</div>}
    </div>
  );
}

export function ErrorState({ title = "Nie udało się wczytać danych", message, onRetry, compact = false }: { title?: string; message: string; onRetry?: () => void; compact?: boolean }) {
  return (
    <div className={`state state--error${compact ? " state--compact" : ""}`} role="alert">
      <span className="state__icon" aria-hidden="true"><CircleAlert /></span>
      <p className="state__title">{title}</p>
      <p className="state__text">{message}</p>
      {onRetry && (
        <div className="state__actions">
          <Button onClick={onRetry}><RotateCw aria-hidden="true" />Spróbuj ponownie</Button>
        </div>
      )}
    </div>
  );
}
