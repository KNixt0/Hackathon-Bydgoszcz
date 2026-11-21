import { Archive, BookOpenText, Link2, Quote, Scale, Users, Building2, Landmark } from "lucide-react";
import type { ReactElement } from "react";
import type { EvidenceKind } from "../../types/incident";
import { useEvidence } from "./EvidenceContext";

export const EVIDENCE_ICON: Record<EvidenceKind, ReactElement> = {
  quote: <Quote />, legal: <Scale />, registry: <Landmark />, archive: <Archive />, account: <Users />, url: <Link2 />, krs: <Building2 />,
};

/** Chips that open the evidence drawer. An id with no matching evidence is shown as inert text, never hidden. */
export function EvidenceChips({ ids }: { ids: string[] }) {
  const { byId, open } = useEvidence();
  if (ids.length === 0) return null;
  return (
    <span className="chips">
      {ids.map((id) => {
        const ev = byId.get(id);
        if (!ev) return <span key={id} className="chip chip--missing" title="Brak materiału dowodowego">{id}</span>;
        return (
          <button key={id} type="button" className="chip" onClick={() => open(id)} title={ev.label}>
            {EVIDENCE_ICON[ev.kind] ?? <BookOpenText />}
            <span className="chip__label">{ev.label}</span>
          </button>
        );
      })}
    </span>
  );
}
