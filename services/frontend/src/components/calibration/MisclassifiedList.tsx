import { Link } from "react-router-dom";
import type { Misclassified } from "../../domain/calibration";
import { formatScore } from "../../domain/format";
import type { CalibrationItem } from "../../types/api";
import { ModuleList } from "../ui/ModuleTag";

export function CaseTable({ items, caption, extra }: { items: CalibrationItem[]; caption: string; extra?: (it: CalibrationItem) => string }) {
  return (
    <table className="rt miss">
      <caption className="sr-only">{caption}</caption>
      <thead><tr><th scope="col" className="r">Ryzyko</th><th scope="col">Sprawa</th><th scope="col">Moduł</th><th scope="col">Etykieta</th></tr></thead>
      <tbody>
        {items.map((it) => (
          <tr key={it.id}>
            <td className="r num miss__score">{formatScore(it.risk_score)}</td>
            <td className="miss__name"><Link to={`/sprawy/${it.id}`} title={it.title}>{it.title}</Link></td>
            <td><ModuleList modules={[it.module]} /></td>
            <td className="muted nowrap">{extra ? extra(it) : it.label_source === "analyst" ? "analityk" : "próbka"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Column({ title, hint, items, empty, testId }: { title: string; hint: string; items: CalibrationItem[]; empty: string; testId: string }) {
  return (
    <div className="miss__col" data-testid={testId}>
      <h4 className="subhead">{title} <span className="num">({items.length})</span></h4>
      <p className="field__hint">{hint}</p>
      {items.length === 0 ? <p className="muted">{empty}</p> : <div className="miss__scroll"><CaseTable items={items} caption={title} /></div>}
    </div>
  );
}

/** The concrete cases that the current threshold gets wrong, as two plain tables. */
export function MisclassifiedList({ data }: { data: Misclassified<CalibrationItem> }) {
  return (
    <div className="miss__grid">
      <Column
        testId="false-positives" title="Fałszywe alarmy" hint="sprawy zgodne, a oznaczone"
        items={data.falsePositives} empty="Przy tym progu żadna zgodna sprawa nie jest oznaczona."
      />
      <Column
        testId="false-negatives" title="Przeoczone naruszenia" hint="naruszenia poniżej progu oznaczenia"
        items={data.falseNegatives} empty="Przy tym progu żadne naruszenie nie zostaje poniżej progu oznaczenia."
      />
    </div>
  );
}
