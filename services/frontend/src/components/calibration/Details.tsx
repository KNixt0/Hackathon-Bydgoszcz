import { ChevronRight } from "lucide-react";
import { useState, type ReactNode } from "react";

/** Closed-by-default disclosure. Its content (charts measure 0 width while hidden) mounts on the first open and stays. */
export function Details({ summary, hint, children }: { summary: string; hint: string; children: () => ReactNode }) {
  const [opened, setOpened] = useState(false);
  return (
    <details className="disc" onToggle={(e) => { if (e.currentTarget.open) setOpened(true); }} data-testid="analyst-details">
      <summary className="disc__sum">
        <ChevronRight aria-hidden="true" className="disc__chev" />
        <span className="disc__title">{summary}</span>
        <span className="disc__hint">{hint}</span>
      </summary>
      <div className="disc__body">{opened ? children() : null}</div>
    </details>
  );
}
