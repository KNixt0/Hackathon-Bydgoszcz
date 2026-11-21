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

export function Panel({ title, hint, actions, children, flush = false, id, headingLevel = 2 }: Props) {
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <section className="panel" id={id} aria-label={title}>
      <header className="panel__head">
        <div>
          <Heading className="panel__title">{title}</Heading>
          {hint && <p className="panel__hint">{hint}</p>}
        </div>
        {actions}
      </header>
      <div className={`panel__body${flush ? " panel__body--flush" : ""}`}>{children}</div>
    </section>
  );
}
