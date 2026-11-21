import { Archive, Building2, Link2, Quote, Scale, Stamp, Users, type LucideIcon } from "lucide-react";
import { EVIDENCE_KIND_LABEL } from "../../domain/labels";
import type { EvidenceKind } from "../../types/incident";
import { useEvidence } from "./EvidenceContext";

export const EVIDENCE_ICON: Record<EvidenceKind, LucideIcon> = {
  quote: Quote, legal: Scale, registry: Stamp, archive: Archive, account: Users, url: Link2, krs: Building2,
};

/** Citations: each chip opens the evidence drawer on that item. Unknown ids are shown, not hidden. */
export function EvidenceChips({ ids }: { ids: string[] }) {
  const { byId, open } = useEvidence();
  if (ids.length === 0) return null;
  return (
    <span className="chips">
      {ids.map((id) => {
        const ev = byId.get(id);
        if (!ev) {
          return <span key={id} className="chip chip--missing" title="Dowód o tym identyfikatorze nie został dołączony do sprawy">{id}</span>;
        }
        const Icon = EVIDENCE_ICON[ev.kind] ?? Link2;
        return (
          <button
            key={id} type="button" className="chip" onClick={() => open(id)}
            title={ev.label} aria-label={`${EVIDENCE_KIND_LABEL[ev.kind] ?? "Dowód"}: ${ev.label}`}
          >
            <Icon aria-hidden="true" />
            <span className="chip__label">{ev.kind === "legal" && ev.legal_ref ? ev.legal_ref : ev.label}</span>
          </button>
        );
      })}
    </span>
  );
}
