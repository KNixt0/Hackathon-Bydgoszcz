import type { ReactNode } from "react";

export type Tone = "red" | "orange" | "green" | "neutral" | "accent" | "plain";

export function Badge({ tone = "plain", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span className={`badge${tone === "plain" ? "" : ` badge--${tone}`}`} title={title}>
      {children}
    </span>
  );
}
