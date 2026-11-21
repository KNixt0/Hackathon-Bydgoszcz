import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export type MarkTone = "red" | "amb" | "grn" | "muted" | "ink";

/** Icon plus words in a level colour: status is never carried by colour alone. */
export function Mark({ tone, icon: Icon, children, title }: { tone: MarkTone; icon: LucideIcon; children: ReactNode; title?: string }) {
  return (
    <span className={`mark mark--${tone}`} title={title}>
      <Icon aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}
