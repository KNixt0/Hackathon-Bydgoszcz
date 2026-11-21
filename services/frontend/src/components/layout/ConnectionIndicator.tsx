import type { ConnectionStatus } from "../../hooks/useLive";

const LABEL: Record<ConnectionStatus, string> = {
  online: "Połączono na żywo",
  connecting: "Łączenie…",
  offline: "Brak połączenia na żywo",
};

export function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  return (
    <span className={`conn conn--${status}`} role="status" title={status === "offline" ? "Nowe incydenty nie pojawią się automatycznie. Trwa ponawianie połączenia." : undefined}>
      <span className="conn__dot" aria-hidden="true" />
      {LABEL[status]}
    </span>
  );
}
