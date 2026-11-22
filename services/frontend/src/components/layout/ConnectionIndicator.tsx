import { LoaderCircle, Wifi, WifiOff } from "lucide-react";
import type { ConnectionStatus } from "../../hooks/useLive";

const LABEL: Record<ConnectionStatus, string> = {
  online: "Połączono",
  connecting: "Łączenie…",
  offline: "Brak połączenia",
};
const ICON = { online: Wifi, connecting: LoaderCircle, offline: WifiOff };

/** Icon plus word; the word carries the meaning. Polite live region so a dropped connection is announced. */
export function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const Icon = ICON[status];
  return (
    <span
      className={`conn conn--${status}`} role="status"
      title={status === "offline" ? "Nowe sprawy nie pojawią się automatycznie. Trwa ponawianie połączenia." : "Połączenie na żywo z serwerem"}
    >
      <Icon aria-hidden="true" />
      <span className="conn__label">{LABEL[status]}</span>
    </span>
  );
}
