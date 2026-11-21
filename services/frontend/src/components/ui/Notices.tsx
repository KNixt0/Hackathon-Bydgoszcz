import { CircleAlert, CircleCheck, Info, X } from "lucide-react";
import type { Notice } from "../../hooks/useUi";

const ICON = { info: Info, success: CircleCheck, error: CircleAlert };

export function Notices({ notices, onDismiss }: { notices: Notice[]; onDismiss: (id: number) => void }) {
  return (
    <div className="notices" role="region" aria-label="Powiadomienia" aria-live="polite">
      {notices.map((n) => {
        const Icon = ICON[n.tone];
        return (
          <div key={n.id} className={`notice notice--${n.tone}`} role={n.tone === "error" ? "alert" : "status"}>
            <Icon aria-hidden="true" />
            <span className="notice__text">{n.text}</span>
            <button type="button" className="notice__close" onClick={() => onDismiss(n.id)} aria-label="Zamknij powiadomienie">
              <X aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
