import { useEffect, useRef } from "react";

interface Props {
  text: string;
  span?: { start: number; end: number };
  quote?: string;
}

/** Resolves the highlight: contract offsets first, exact-substring search as a fallback. */
export function resolveSpan(text: string, span?: { start: number; end: number }, quote?: string): { start: number; end: number } | null {
  if (span && Number.isInteger(span.start) && Number.isInteger(span.end) && span.start >= 0 && span.end > span.start && span.end <= text.length) {
    if (!quote || text.slice(span.start, span.end) === quote) return span;
  }
  if (quote) {
    const start = text.indexOf(quote);
    if (start >= 0) return { start, end: start + quote.length };
  }
  return null;
}

/** The archived source text with the exact quoted passage highlighted and scrolled into view. */
export function SourceText({ text, span, quote }: Props) {
  const markRef = useRef<HTMLElement>(null);
  const resolved = resolveSpan(text, span, quote);

  useEffect(() => {
    const el = markRef.current;
    if (el && typeof el.scrollIntoView === "function") el.scrollIntoView({ block: "center" });
  }, [resolved?.start, resolved?.end]);

  if (!text) return <p className="muted">Tekst źródłowy nie został zapisany.</p>;
  if (!resolved) {
    return (
      <>
        {quote && <p className="form-error" style={{ marginBottom: 6 }}>Nie udało się odnaleźć cytatu w zarchiwizowanym tekście. Zweryfikuj dowód ręcznie.</p>}
        <div className="source-text" tabIndex={0} role="region" aria-label="Zarchiwizowany tekst źródłowy">{text}</div>
      </>
    );
  }
  return (
    <div className="source-text" tabIndex={0} role="region" aria-label="Zarchiwizowany tekst źródłowy z wyróżnionym cytatem">
      {text.slice(0, resolved.start)}
      <mark ref={markRef} data-testid="quote-highlight">{text.slice(resolved.start, resolved.end)}</mark>
      {text.slice(resolved.end)}
    </div>
  );
}
