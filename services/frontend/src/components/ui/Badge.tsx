import type { ReactNode } from "react";

/** Only two badges have a fill: "Krytyczne" (red) and "Nowa" (accent). "plain" is icon + text without a fill. */
export type Tone = "red" | "accent" | "plain";

export function Badge({ tone = "plain", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span className={`badge badge--${tone}`} title={title}>
      {children}
    </span>
  );
}
