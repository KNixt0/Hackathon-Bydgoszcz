import { useEffect, useState } from "react";
import { segText, type Seg } from "../../domain/calibrationCopy";

/**
 * The plain-language sentence. It updates on every change; the screen-reader live region gets the text
 * only after 400 ms without change, so dragging the slider is not read out step by step.
 */
export function LiveSentence({ segments }: { segments: Seg[] }) {
  const text = segText(segments);
  const [announced, setAnnounced] = useState(text);
  useEffect(() => {
    const id = window.setTimeout(() => setAnnounced(text), 400);
    return () => window.clearTimeout(id);
  }, [text]);
  return (
    <>
      <p className="live" data-testid="live-sentence" aria-hidden="true">
        {segments.map((s, i) => (s.b ? <b key={i} className="num">{s.t}</b> : <span key={i}>{s.t}</span>))}
      </p>
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true" data-testid="live-announcement">{announced}</p>
    </>
  );
}
