import { useId, useState } from "react";
import { createPortal } from "react-dom";
import { RULE_DEFINITIONS } from "../../domain/rules";
import type { RuleId } from "../../types/incident";

export function RuleTip({ id, definition }: { id: RuleId; definition?: { name: string; legal_basis: string; explanation?: string } }) {
  const tipId = useId();
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);
  const rule: { name: string; legal_basis: string; explanation?: string } = definition ?? RULE_DEFINITIONS[id];
  const show = (element: HTMLElement) => {
    const box = element.getBoundingClientRect();
    setPosition({ left: Math.max(8, Math.min(box.left, window.innerWidth - 320)), top: Math.max(8, Math.min(box.bottom + 4, window.innerHeight - 250)) });
  };
  return <span className="rule-tip" onMouseLeave={() => setPosition(null)}>
    <button type="button" className="rule-tip__number" aria-describedby={position ? tipId : undefined} aria-label={`Kryterium ${id}: ${rule.name}`}
      onMouseEnter={(e) => show(e.currentTarget)} onFocus={(e) => show(e.currentTarget)} onBlur={() => setPosition(null)} onClick={(e) => position ? setPosition(null) : show(e.currentTarget)} onKeyDown={(e) => { if (e.key === "Escape") setPosition(null); }}>{id}</button>
    {position && createPortal(<span role="tooltip" id={tipId} className="rule-tip__body rule-tip__body--open" style={{ position: "fixed", ...position }}><b>Kryterium {id}: {rule.name}</b><span>{rule.legal_basis}</span>{rule.explanation && <span>{rule.explanation}</span>}</span>, document.body)}
  </span>;
}
