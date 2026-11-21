import { createContext, useContext } from "react";
import type { Evidence } from "../../types/incident";

interface EvidenceContextValue {
  byId: Map<string, Evidence>;
  open: (id: string) => void;
}

export const EvidenceContext = createContext<EvidenceContextValue>({ byId: new Map(), open: () => undefined });
export const useEvidence = () => useContext(EvidenceContext);
