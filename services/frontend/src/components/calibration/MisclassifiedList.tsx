import { Link } from "react-router-dom";
import type { Misclassified } from "../../domain/calibration";
import { formatScore } from "../../domain/format";
import type { CalibrationItem } from "../../types/api";
import { Badge } from "../ui/Badge";
import { ModuleTag } from "../ui/ModuleTag";

function Column({ title, hint, items, empty, testId }: { title: string; hint: string; items: CalibrationItem[]; empty: string; testId: string }) {
  return (
    <div className="miss__col" data-testid={testId}>
      <div className="miss__head">
        <h3 className="miss__title">{title} <span className="num">({items.length})</span></h3>
        <span className="miss__hint">{hint}</span>
      </div>
      {items.length === 0 ? (
        <p className="miss__empty">{empty}</p>
      ) : (
        <ul className="miss__list">
          {items.map((it) => (
            <li key={it.id} className="miss__item">
              <span className="miss__score num" title="Surowy wynik ryzyka">{formatScore(it.risk_score)}</span>
              <Link to={`/sprawy/${it.id}`} className="miss__name truncate" title={it.title}>{it.title}</Link>
              {it.label_source === "analyst" && <Badge tone="accent" title="Etykieta nadana przez analityka w sprawie">analityk</Badge>}
              <ModuleTag module={it.module} compact />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The concrete cases that the current threshold gets wrong. */
export function MisclassifiedList({ data }: { data: Misclassified<CalibrationItem> }) {
  return (
    <div className="miss">
      <Column
        testId="false-positives" title="Fałszywe alarmy" hint="zgodne, a oflagowane"
        items={data.falsePositives} empty="Przy tym progu żadna zgodna sprawa nie jest oflagowana."
      />
      <Column
        testId="false-negatives" title="Przeoczone naruszenia" hint="naruszenia poniżej progu flagowania"
        items={data.falseNegatives} empty="Przy tym progu żadne naruszenie nie zostaje poniżej progu flagowania."
      />
    </div>
  );
}
