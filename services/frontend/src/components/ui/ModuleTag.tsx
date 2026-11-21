import { MODULE_LABEL, MODULE_SHORT } from "../../domain/labels";
import type { ModuleId } from "../../types/incident";

export function ModuleTag({ module, compact = false }: { module: ModuleId; compact?: boolean }) {
  return (
    <span className={`module-tag${compact ? " module-tag--compact" : ""}`} title={`Moduł ${module}: ${MODULE_LABEL[module]}`}>
      <span className="module-tag__n" aria-hidden="true">{module}</span>
      {compact ? <span className="sr-only">Moduł {module}: {MODULE_SHORT[module]}</span> : MODULE_SHORT[module]}
    </span>
  );
}
