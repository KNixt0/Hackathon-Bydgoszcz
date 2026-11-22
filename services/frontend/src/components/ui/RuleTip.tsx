import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { RULE_DEFINITIONS } from "../../domain/rules";
import type { RuleId } from "../../types/incident";

type Definition = { name: string; legal_basis: string; explanation?: string };
export function RuleTip({ id, definition }: { id: RuleId; definition?: Definition }) {
  const tipId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const tooltip = useRef<HTMLSpanElement>(null);
  const hideTimer = useRef<number | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ left: 8, top: 8 });
  const rule: Definition = definition ?? RULE_DEFINITIONS[id];
  const cancelHide = () => window.clearTimeout(hideTimer.current);
  const show = () => { cancelHide(); setOpen(true); };
  const leave = () => {
    cancelHide();
    hideTimer.current = window.setTimeout(() => {
      if (document.activeElement !== trigger.current) setOpen(false);
    }, 120);
  };
  const reposition = useCallback(() => {
    if (!trigger.current || !tooltip.current) return;
    const box = trigger.current.getBoundingClientRect();
    const popup = tooltip.current.getBoundingClientRect();
    const below = box.bottom + 8;
    const top = below + popup.height <= window.innerHeight - 8 ? below : Math.max(8, box.top - popup.height - 8);
    const left = Math.max(8, Math.min(box.left, window.innerWidth - popup.width - 8));
    setPosition((previous) => previous.top === top && previous.left === left ? previous : { top, left });
  }, []);
  useLayoutEffect(() => { if (open) reposition(); }, [open, reposition]);
  useEffect(() => {
    if (!open) return;
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !trigger.current?.contains(event.target) && !tooltip.current?.contains(event.target)) setOpen(false);
    };
    window.addEventListener("keydown", escape);
    window.addEventListener("pointerdown", outside);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    return () => {
      window.removeEventListener("keydown", escape);
      window.removeEventListener("pointerdown", outside);
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
    };
  }, [open, reposition]);
  useEffect(() => () => window.clearTimeout(hideTimer.current), []);
  return <span className="rule-tip" onMouseLeave={leave}>
    <button ref={trigger} type="button" className="rule-tip__number" aria-describedby={open ? tipId : undefined} aria-label={`Kryterium ${id}: ${rule.name}`}
      onMouseEnter={show} onFocus={show} onBlur={() => { cancelHide(); setOpen(false); }} onClick={show}>{id}</button>
    {open && createPortal(<span ref={tooltip} role="tooltip" id={tipId} className="rule-tip__body rule-tip__body--open" style={{ position: "fixed", ...position }} onMouseEnter={cancelHide} onMouseLeave={leave}>
      <b>Kryterium {id}: {rule.name}</b><span>{rule.legal_basis}</span>{rule.explanation && <span>{rule.explanation}</span>}
    </span>, document.body)}
  </span>;
}
