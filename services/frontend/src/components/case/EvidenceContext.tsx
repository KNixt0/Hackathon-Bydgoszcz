import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { Evidence } from "../../types/incident";

interface EvidenceContextValue {
  byId: Map<string, Evidence>;
  open: (id: string) => void;
}

const EvidenceContext = createContext<EvidenceContextValue>({ byId: new Map(), open: () => undefined });

/** Lets any citation inside a case open the evidence drawer without threading props through every panel. */
export function EvidenceProvider({ evidence, onOpen, children }: { evidence: Evidence[]; onOpen: (id: string) => void; children: ReactNode }) {
  const value = useMemo(() => ({ byId: new Map(evidence.map((e) => [e.id, e])), open: onOpen }), [evidence, onOpen]);
  return <EvidenceContext.Provider value={value}>{children}</EvidenceContext.Provider>;
}

export function useEvidence(): EvidenceContextValue {
  return useContext(EvidenceContext);
}
