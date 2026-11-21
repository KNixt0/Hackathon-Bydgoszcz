import { ROLE_LABEL } from "../../domain/labels";
import type { User } from "../../types/api";

/** "Analityk (demo), analityk" and the "Wyloguj" action, as plain header text. */
export function UserChip({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <span className="user-chip" data-testid="user-chip">
      <span className="user-chip__text" title={user.email}>
        <span className="user-chip__name">{user.name}</span>
        <span className="user-chip__role">, <span>{(ROLE_LABEL[user.role] ?? user.role).toLowerCase()}</span></span>
      </span>
      <button type="button" className="linkbtn" onClick={onLogout} title={`Wyloguj ${user.email}`}>Wyloguj</button>
    </span>
  );
}
