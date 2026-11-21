import { CircleAlert } from "lucide-react";
import { formatDate } from "../../domain/format";
import type { Thresholds } from "../../domain/levels";
import type { ThresholdSettings } from "../../types/api";

interface Props {
  thresholds: Thresholds;
  globalThresholds: Thresholds;
  global: ThresholdSettings | null;
  isGlobal: boolean;
  supervisor: boolean;
  saving: boolean;
  saveError: string | null;
  onSave: () => void;
  onReset: () => void;
}

/**
 * The global-thresholds line, replaced in place by the "Podgląd, niezapisane" callout when the preview differs.
 * The slot reserves its height so nothing below it moves.
 */
export function PreviewNote({ thresholds: t, globalThresholds: g, global, isGlobal, supervisor, saving, saveError, onSave, onReset }: Props) {
  const who = global?.updated_by ? `Ustawił ${global.updated_by}, ${formatDate(global.updated_at)}.` : "Wartości domyślne, jeszcze nie zmieniane.";
  return (
    <div className="pnote" data-testid="global-thresholds">
      {isGlobal ? (
        <p className="pnote__line">
          Obowiązują progi globalne: oznaczenie od <b className="num">{g.orange}</b>, krytyczne od <b className="num">{g.red}</b>. {who}
        </p>
      ) : (
        <div className="callout callout--compact pnote__callout">
          <p>
            <b>Podgląd, niezapisane.</b> Progi globalne to <span className="num">{g.orange}</span> i <span className="num">{g.red}</span>, a w tym podglądzie{" "}
            <b className="num">{t.orange}</b> i <b className="num">{t.red}</b>. Zmiana działa tylko w tej przeglądarce{supervisor ? ", dopóki jej nie zapiszesz" : ""}.
          </p>
          <div className="callout__acts">
            {supervisor && (
              <button type="button" className="btn btn--primary" onClick={onSave} disabled={saving}>{saving ? "Zapisywanie…" : "Zapisz jako progi globalne"}</button>
            )}
            <button type="button" className="btn" onClick={onReset}>Przywróć globalne ({g.orange} / {g.red})</button>
            {!supervisor && <span className="muted">Progi globalne zapisuje kierownik.</span>}
          </div>
        </div>
      )}
      {saveError && (
        <div className="callout callout--error callout--compact" role="alert">
          <p className="callout__lead"><CircleAlert aria-hidden="true" />Nie zapisano progów. {saveError.replace(/\.$/, "")}. Spróbuj ponownie.</p>
        </div>
      )}
    </div>
  );
}
