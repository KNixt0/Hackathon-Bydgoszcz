import { ChevronRight, FolderSearch } from "lucide-react";
import { formatDateTime, safeHref } from "../../domain/format";
import { EVIDENCE_KIND_LABEL, PLATFORM_LABEL } from "../../domain/labels";
import type { Evidence, EvidenceKind, Source } from "../../types/incident";
import { EmptyState } from "../ui/States";
import { EVIDENCE_ICON } from "./EvidenceChips";

const KIND_ORDER: EvidenceKind[] = ["quote", "legal", "registry", "krs", "account", "archive", "url"];

function subline(ev: Evidence): string | null {
  if (ev.kind === "quote" && ev.quote) return `„${ev.quote}”`;
  if (ev.kind === "legal" && ev.legal_ref) return ev.legal_ref;
  if (ev.url) return ev.url;
  if (ev.storage_key) return ev.storage_key;
  return null;
}

interface Props {
  evidence: Evidence[];
  source: Source;
  onOpen: (id: string) => void;
}

/** Block 4: every piece of evidence in the case; each row opens the evidence drawer. */
export function SourcesBlock({ evidence, source, onOpen }: Props) {
  const sorted = [...evidence].sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind));
  const href = safeHref(source.url);
  return (
    <section className="csec" id="zrodla" aria-labelledby="zrodla-h">
      <div className="csec__head">
        <h2 className="section-title" id="zrodla-h">Źródła dowodowe</h2>
        <span className="muted num">{evidence.length} pozycji</span>
      </div>
      <p className="csec__lead">Każdy dowód otwiera się w panelu bocznym, bez opuszczania sprawy.</p>
      <div className="sources">
        <div className="sources__list">
          {sorted.length === 0 ? (
            <EmptyState compact title="Brak dowodów" text="Silnik nie dołączył cytatów, wpisów rejestrowych ani archiwum do tej sprawy." />
          ) : (
            sorted.map((ev) => {
              const Icon = EVIDENCE_ICON[ev.kind] ?? FolderSearch;
              const sub = subline(ev);
              return (
                <button key={ev.id} type="button" className="ev-row" onClick={() => onOpen(ev.id)} data-testid="evidence-row">
                  <span className="ev-row__kind"><Icon aria-hidden="true" />{EVIDENCE_KIND_LABEL[ev.kind] ?? "Dowód"}</span>
                  <span className="ev-row__label">
                    <span className="ev-row__title truncate">{ev.label}</span>
                    {sub && <span className="ev-row__sub truncate">{sub}</span>}
                  </span>
                  <ChevronRight aria-hidden="true" />
                </button>
              );
            })
          )}
        </div>
        <div className="sources__meta">
          <h3 className="subhead">Materiał źródłowy</h3>
          <dl className="kv kv--compact">
            <dt>Platforma</dt><dd>{PLATFORM_LABEL[source.platform] ?? source.platform}</dd>
            <dt>Adres URL</dt>
            <dd>{href ? <a href={href} target="_blank" rel="noopener noreferrer">{source.url}<span className="sr-only"> (otwiera się w nowej karcie)</span></a> : source.url}</dd>
            <dt>Pobrano</dt><dd>{formatDateTime(source.fetched_at)}</dd>
            <dt>Język</dt><dd>{source.language}</dd>
            <dt>Skrót treści</dt><dd className="num" title={`SHA-256 znormalizowanego tekstu: ${source.content_hash}`}>{source.content_hash.slice(0, 12)}<span className="muted"> (pierwsze 12 znaków)</span></dd>
            <dt>Archiwum</dt>
            <dd>
              {[source.archive.html_key && "kod strony", source.archive.screenshot_key && "zrzut ekranu"].filter(Boolean).join(", ") || "nie zarchiwizowano"}
            </dd>
          </dl>
        </div>
      </div>
    </section>
  );
}
