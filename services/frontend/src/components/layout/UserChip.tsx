import { LogOut } from "lucide-react";
import { ROLE_LABEL } from "../../domain/labels";
import type { User } from "../../types/api";
import { Button } from "../ui/Button";

export function UserChip({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <span className="user-chip" data-testid="user-chip">
      <span className="user-chip__text">
        <span className="user-chip__name truncate" title={user.email}>{user.name}</span>
        <span className="user-chip__role">{ROLE_LABEL[user.role] ?? user.role}</span>
      </span>
      <Button variant="ghost" onClick={onLogout} title={`Wyloguj ${user.email}`}>
        <LogOut aria-hidden="true" />Wyloguj
      </Button>
    </span>
  );
}
