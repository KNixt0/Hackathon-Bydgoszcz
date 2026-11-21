import { useMemo } from "react";
import type { Evidence } from "../../types/incident";
import { useEvidence } from "./EvidenceContext";

interface Seg { start: number; end: number; evidenceId: string }

/** Locates each quote evidence in the text: trusts `span` only if it matches the quote, else searches for it. */
export function locateQuotes(text: string, evidence: Evidence[]): Seg[] {
  const found: Seg[] = [];
  for (const ev of evidence) {
    if (ev.kind !== "quote" || !ev.quote) continue;
    const start = ev.span && text.slice(ev.span.start, ev.span.end) === ev.quote ? ev.span.start : text.indexOf(ev.quote);
    if (start < 0) continue;
    found.push({ start, end: start + ev.quote.length, evidenceId: ev.id });
  }
  found.sort((a, b) => a.start - b.start);
  const out: Seg[] = [];
  for (const s of found) {
    const last = out[out.length - 1];
    if (!last || s.start >= last.end) out.push(s);
  }
  return out;
}

export function SourceText({ text, evidence }: { text: string; evidence: Evidence[] }) {
  const { open } = useEvidence();
  const parts = useMemo(() => {
    const segs = locateQuotes(text, evidence);
    const nodes: Array<{ key: number; text: string; evidenceId?: string }> = [];
    let cursor = 0;
    segs.forEach((s, i) => {
      if (s.start > cursor) nodes.push({ key: i * 2, text: text.slice(cursor, s.start) });
      nodes.push({ key: i * 2 + 1, text: text.slice(s.start, s.end), evidenceId: s.evidenceId });
      cursor = s.end;
    });
    if (cursor < text.length) nodes.push({ key: 9999, text: text.slice(cursor) });
    return nodes;
  }, [text, evidence]);

  if (!text) return <p className="muted">Brak zarchiwizowanego tekstu.</p>;
  return (
    <div className="source" tabIndex={0} aria-label="Treść materiału z wyróżnionymi fragmentami naruszeń">
      {parts.map((p) =>
        p.evidenceId ? (
          <mark key={p.key} className="hl hl--btn" role="button" tabIndex={0}
            onClick={() => open(p.evidenceId as string)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(p.evidenceId as string); } }}>
            {p.text}
          </mark>
        ) : (
          <span key={p.key}>{p.text}</span>
        ),
      )}
    </div>
  );
}
