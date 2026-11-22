import { CircleCheck, CircleMinus, TriangleAlert, type LucideIcon } from "lucide-react";
import { formatDate, safeHref } from "../../domain/format";
import { REGISTRY_RESULT_LABEL } from "../../domain/labels";
import type { RegistryCheck, RegistryStatus } from "../../types/incident";
import { Mark, type MarkTone } from "../ui/Mark";
import { EmptyState } from "../ui/States";

/** "Brak wpisu" is amber with icon + words: absence from a list is a reason to verify, not a verdict. */
const TONE: Record<RegistryStatus, MarkTone> = { listed: "grn", warning_listed: "red", inactive: "amb", not_listed: "amb", not_checked: "muted" };
const ICON: Record<RegistryStatus, LucideIcon> = { listed: CircleCheck, warning_listed: TriangleAlert, inactive: TriangleAlert, not_listed: CircleMinus, not_checked: CircleMinus };

/** Register and licence checks as a ruled table: register, result in words, "stan na" date. */
export function RegistryChecks({ checks }: { checks: RegistryCheck[] }) {
  checks = checks.filter((check) => !(check.status === "not_checked" && ["knf_foreign_branches", "knf_foreign_cross_border"].includes(check.registry)));
  if (checks.length === 0) {
    return <EmptyState compact title="Brak sprawdzeń w rejestrach" text="Dla tego materiału nie wykonano weryfikacji w rejestrach KNF, KIRP ani KIDP." />;
  }
  return (
    <div className="table-wrap">
      <table className="rt registry">
        <caption className="sr-only">Sprawdzenia w rejestrach</caption>
        <thead>
          <tr><th scope="col">Rejestr</th><th scope="col">Wynik</th><th scope="col">Stan na</th></tr>
        </thead>
        <tbody>
          {checks.map((c, i) => {
            const href = safeHref(c.url);
            return (
              <tr key={`${c.registry}-${i}`} data-testid="registry-check" data-status={c.status}>
                <td>
                  <span className="registry__name">{c.label}</span>
                  <span className="rt__sub">{c.subject}{c.detail ? `. ${c.detail}` : ""}</span>
                  {href && (
                    <a className="rt__sub registry__link" href={href} target="_blank" rel="noopener noreferrer">
                      otwórz rejestr<span className="sr-only"> {c.label} (otwiera się w nowej karcie)</span>
                    </a>
                  )}
                </td>
                <td><Mark tone={TONE[c.status] ?? "muted"} icon={ICON[c.status] ?? CircleMinus}>{REGISTRY_RESULT_LABEL[c.status] ?? c.status}</Mark></td>
                <td className="nowrap">{c.snapshot_date ? formatDate(c.snapshot_date) : <span className="muted">brak migawki</span>}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
