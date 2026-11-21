import type { ReactNode } from "react";

interface Props {
  title: string;
  hint?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  flush?: boolean;
  id?: string;
  headingLevel?: 2 | 3;
}

/** 1px ruled block with an h2/h3 title; no header bar, no radius, no shadow. */
export function Panel({ title, hint, actions, children, flush = false, id, headingLevel = 2 }: Props) {
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <section className={`panel${flush ? " panel--flush" : ""}`} id={id} aria-label={title}>
      <header className="panel__head" style={flush ? { padding: "16px 16px 0" } : undefined}>
        <div>
          <Heading className="panel__title">{title}</Heading>
          {hint && <p className="panel__hint">{hint}</p>}
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}
