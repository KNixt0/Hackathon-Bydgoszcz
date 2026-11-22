import { MODULE_LABEL } from "../../domain/labels";
import type { ModuleId } from "../../types/incident";

/** Plain text, no pill: "1 Twórcy finansowi i podmioty trzecie" (or just the number with a full name for screen readers). */
export function ModuleTag({ module, compact = false }: { module: ModuleId; compact?: boolean }) {
  if (compact) {
    return (
      <span className="module-tag" title={`Moduł ${module}: ${MODULE_LABEL[module]}`}>
        <span aria-hidden="true">{module}</span>
        <span className="sr-only">Moduł {module}: {MODULE_LABEL[module]}</span>
      </span>
    );
  }
  return <span className="module-tag">{module} {MODULE_LABEL[module]}</span>;
}

/** "1, 2" with the names for assistive tech; the queue legend names the numbers for everyone. */
export function ModuleList({ modules }: { modules: ModuleId[] }) {
  return (
    <span className="nowrap">
      <span aria-hidden="true">{modules.join(", ")}</span>
      <span className="sr-only">{modules.map((m) => `Moduł ${m}: ${MODULE_LABEL[m]}`).join("; ")}</span>
    </span>
  );
}
