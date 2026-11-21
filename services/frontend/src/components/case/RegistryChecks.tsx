import { BadgeCheck, CircleAlert, CircleHelp, CircleSlash, ExternalLink, Stamp, type LucideIcon } from "lucide-react";
import { formatDate, safeHref } from "../../domain/format";
import { REGISTRY_STATUS_LABEL } from "../../domain/labels";
import type { RegistryCheck, RegistryStatus } from "../../types/incident";
import { Badge, type Tone } from "../ui/Badge";
import { EmptyState } from "../ui/States";

const TONE: Record<RegistryStatus, Tone> = { listed: "green", not_listed: "neutral", warning_listed: "red", inactive: "orange", not_checked: "neutral" };
const ICON: Record<RegistryStatus, LucideIcon> = { listed: BadgeCheck, not_listed: CircleSlash, warning_listed: CircleAlert, inactive: CircleAlert, not_checked: CircleHelp };

/** Register and licence checks (KNF registers, KIRP, KIDP…) as status cards. */
export function RegistryChecks({ checks }: { checks: RegistryCheck[] }) {
  if (checks.length === 0) {
    return <EmptyState compact icon={<Stamp />} title="Brak sprawdzeń w rejestrach" text="Dla tego materiału nie wykonano weryfikacji w rejestrach KNF, KIRP ani KIDP." />;
  }
  return (
    <ul className="registry">
      {checks.map((c, i) => {
        const Icon = ICON[c.status] ?? CircleHelp;
        const href = safeHref(c.url);
        return (
          <li key={`${c.registry}-${i}`} className={`reg${c.status === "warning_listed" ? " reg--bad" : ""}`} data-testid="registry-check">
            <div className="reg__top">
              <span className="reg__label">{c.label}</span>
              <Badge tone={TONE[c.status] ?? "neutral"}><Icon aria-hidden="true" />{REGISTRY_STATUS_LABEL[c.status] ?? c.status}</Badge>
            </div>
            <span className="reg__subject">{c.subject}</span>
            <span className="reg__detail">{c.detail}</span>
            <div className="reg__foot">
              <span>{c.snapshot_date ? `Stan rejestru: ${formatDate(c.snapshot_date)}` : "Bez migawki rejestru"}</span>
              {href && <a href={href} target="_blank" rel="noopener noreferrer">Rejestr <ExternalLink size={11} aria-hidden="true" /><span className="sr-only"> (otwiera się w nowej karcie)</span></a>}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
