import { Crosshair } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { evidenceUrl } from "../../api/endpoints";
import type { BBox, Evidence, Incident, RuleMethod, Viewport } from "../../types/incident";
import { Button } from "../ui/Button";
import "./evidence.css";

const DESKTOP = { id: "desktop" as Viewport, label: "Komputer", size: "1920×1080" };
export const VIEWPORTS: { id: Viewport; label: string; size: string }[] = [
  DESKTOP,
  { id: "tablet", label: "Tablet", size: "768×1024" },
  { id: "mobile", label: "Telefon", size: "390×844" },
];

export const METHOD_LABEL: Record<RuleMethod, string> = {
  rendered: "pomiar w przeglądarce",
  static: "analiza kodu HTML",
  text: "analiza tekstu",
  llm: "model językowy",
};

/** True when the evidence item points at a region of an archived screenshot (contract v3). */
export function hasScreenshotBox(ev: Evidence): ev is Evidence & { bbox: BBox } {
  return !!ev.bbox && ev.bbox.w > 0 && ev.bbox.h > 0;
}

/** Screenshot keys per viewport: the archive's set, plus the one this evidence points at. */
export function screenshotKeys(incident: Incident, ev: Evidence): Partial<Record<Viewport, string>> {
  const keys: Partial<Record<Viewport, string>> = { ...(incident.source.archive.screenshots ?? {}) };
  if (!keys.desktop && incident.source.archive.screenshot_key) keys.desktop = incident.source.archive.screenshot_key;
  if (ev.bbox && ev.storage_key && /\.(png|jpe?g|webp)$/i.test(ev.storage_key)) keys[ev.bbox.viewport] = ev.storage_key;
  return keys;
}

/** Box position as percentages of the image, so it stays aligned at any displayed size. */
export function boxStyle(bbox: BBox, natural: { w: number; h: number }): React.CSSProperties | null {
  if (natural.w <= 0 || natural.h <= 0 || bbox.y >= natural.h || bbox.x >= natural.w) return null;
  const w = Math.min(bbox.w, natural.w - bbox.x);
  const h = Math.min(bbox.h, natural.h - bbox.y);
  const pct = (v: number, total: number) => `${(v / total) * 100}%`;
  return { left: pct(bbox.x, natural.w), top: pct(bbox.y, natural.h), width: pct(w, natural.w), height: pct(h, natural.h) };
}

interface Props {
  evidence: Evidence;
  incident: Incident;
}

/** Archived screenshot with the violation box drawn over it, a viewport switcher and the measured explanation. */
export function ScreenshotEvidence({ evidence: ev, incident }: Props) {
  const keys = screenshotKeys(incident, ev);
  const available = VIEWPORTS.filter((v) => keys[v.id]);
  const home = ev.bbox?.viewport ?? available[0]?.id ?? "desktop";
  const [viewport, setViewport] = useState<Viewport>(home);
  const [natural, setNatural] = useState<{ key: string; w: number; h: number } | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const key = keys[viewport];
  const meta = VIEWPORTS.find((v) => v.id === viewport) ?? DESKTOP;
  const showBox = ev.bbox && ev.bbox.viewport === viewport;
  const size = natural && natural.key === key ? natural : null;
  const style = showBox && ev.bbox && size ? boxStyle(ev.bbox, size) : null;
  const rules = incident.rules.filter((r) => r.evidence_ids.includes(ev.id));

  useEffect(() => {
    if (style) boxRef.current?.scrollIntoView({ block: "center", inline: "nearest" });
  }, [style?.top, style?.left]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!available.length && !rules.length) return null;
  const homeMeta = VIEWPORTS.find((v) => v.id === ev.bbox?.viewport);

  return (
    <section className="ev-shot" aria-label="Dowód na zrzucie ekranu" data-testid="screenshot-evidence">
      <div className="ev-shot__head">
        <h3 className="drawer__section-title">Zrzut ekranu z zaznaczeniem</h3>
        {available.length > 1 && (
          <div className="ev-shot__switch" role="group" aria-label="Rozmiar ekranu">
            {available.map((v) => (
              <button
                key={v.id}
                type="button"
                className="ev-shot__tab"
                aria-pressed={viewport === v.id}
                onClick={() => setViewport(v.id)}
              >
                {v.label}
                {ev.bbox?.viewport === v.id && <span className="sr-only"> (zaznaczenie)</span>}
              </button>
            ))}
          </div>
        )}
      </div>

      {key ? (
        failed === key ? (
          <p className="form-error">Nie udało się wczytać zrzutu ekranu z archiwum.</p>
        ) : (
          <div className="ev-shot__frame" tabIndex={0} role="group" aria-label={`Zrzut ekranu: ${meta.label.toLowerCase()} ${meta.size}, przewijany`}>
            <div className="ev-shot__canvas">
              <img
                key={key}
                className="ev-shot__img"
                src={evidenceUrl(key)}
                alt={
                  showBox
                    ? `Zrzut strony (${meta.label.toLowerCase()} ${meta.size}) z ramką wokół: ${ev.label}${ev.quote ? ` – „${ev.quote.slice(0, 120)}”` : ""}`
                    : `Zrzut strony (${meta.label.toLowerCase()} ${meta.size})`
                }
                onLoad={(e) => setNatural({ key, w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
                onError={() => setFailed(key)}
              />
              {style && <div ref={boxRef} className="ev-shot__box" style={style} aria-hidden="true" data-testid="violation-box" />}
            </div>
          </div>
        )
      ) : (
        <p className="muted">Brak zarchiwizowanego zrzutu ekranu dla tego widoku.</p>
      )}

      <div className="ev-shot__foot">
        {showBox && style && (
          <Button variant="ghost" size="sm" onClick={() => boxRef.current?.scrollIntoView({ block: "center", inline: "nearest" })}>
            <Crosshair size={14} aria-hidden="true" /> Pokaż zaznaczenie
          </Button>
        )}
        {showBox && size && !style && <p className="muted">Zaznaczony fragment leży poza zapisaną częścią zrzutu (zrzut jest przycięty).</p>}
        {!showBox && homeMeta && (
          <p className="muted">
            Zaznaczenie dotyczy widoku: {homeMeta.label.toLowerCase()} {homeMeta.size}.{" "}
            <button type="button" className="ev-shot__link" onClick={() => setViewport(homeMeta.id)}>Przełącz</button>
          </p>
        )}
        {ev.bbox && showBox && (
          <p className="muted ev-shot__coords">
            Ramka: x {Math.round(ev.bbox.x)}, y {Math.round(ev.bbox.y)}, {Math.round(ev.bbox.w)}×{Math.round(ev.bbox.h)} px (piksele CSS zrzutu)
          </p>
        )}
      </div>

      {rules.length > 0 && (
        <ul className="ev-shot__rules" aria-label="Wynik pomiaru">
          {rules.map((r) => (
            <li key={r.id}>
              <span className="ev-shot__rule">
                Kryterium {r.id}: {r.name}
                {r.method && <span className="ev-shot__method">{METHOD_LABEL[r.method]}</span>}
              </span>
              <span>{r.explanation}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
