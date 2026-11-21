import * as Dialog from "@radix-ui/react-dialog";
import { ExternalLink, X } from "lucide-react";
import { evidenceUrl } from "../../api/endpoints";
import { EVIDENCE_KIND_LABEL } from "../../domain/labels";
import { safeHref } from "../../domain/format";
import type { Evidence } from "../../types/incident";
import { ButtonLink, Button } from "../ui/Button";

interface Props {
  evidence: Evidence | null;
  sourceText: string;
  onClose: () => void;
}

/** A few words of surrounding text so the quote can be judged in context. */
function contextAround(text: string, ev: Evidence): { before: string; quote: string; after: string } | null {
  if (!ev.quote) return null;
  let start = ev.span && text.slice(ev.span.start, ev.span.end) === ev.quote ? ev.span.start : text.indexOf(ev.quote);
  if (start < 0) return { before: "", quote: ev.quote, after: "" };
  const end = start + ev.quote.length;
  start = Math.max(0, start);
  const b = Math.max(0, start - 160);
  const a = Math.min(text.length, end + 160);
  return {
    before: (b > 0 ? "… " : "") + text.slice(b, start),
    quote: text.slice(start, end),
    after: text.slice(end, a) + (a < text.length ? " …" : ""),
  };
}

export function EvidenceDrawer({ evidence, sourceText, onClose }: Props) {
  const ctx = evidence ? contextAround(sourceText, evidence) : null;
  const link = safeHref(evidence?.url);
  const key = evidence?.storage_key ?? null;
  return (
    <Dialog.Root open={evidence !== null} onOpenChange={(o) => { if (!o) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="drawer" aria-describedby={undefined}>
          <div className="drawer__head">
            <div>
              <p className="drawer__kind">{evidence ? EVIDENCE_KIND_LABEL[evidence.kind] : ""}</p>
              <Dialog.Title className="drawer__title">{evidence?.label ?? "Dowód"}</Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" iconOnly aria-label="Zamknij szufladę dowodów"><X aria-hidden="true" /></Button>
            </Dialog.Close>
          </div>
          {evidence && (
            <div className="drawer__body">
              {ctx && (
                <figure className="quote">
                  <blockquote>
                    <span className="muted">{ctx.before}</span><mark className="hl">{ctx.quote}</mark><span className="muted">{ctx.after}</span>
                  </blockquote>
                  <figcaption>Dokładny fragment materiału źródłowego, wyróżniony w kontekście.</figcaption>
                </figure>
              )}
              <dl className="kv">
                {evidence.legal_ref && (<><dt>Podstawa prawna</dt><dd>{evidence.legal_ref}</dd></>)}
                {evidence.attachment && (<><dt>Załącznik organizatora</dt><dd>{evidence.attachment}</dd></>)}
                {evidence.span && (<><dt>Pozycja w tekście</dt><dd className="num">znaki {evidence.span.start}–{evidence.span.end}</dd></>)}
                {evidence.url && (<><dt>Adres</dt><dd>{link ? <a href={link} target="_blank" rel="noopener noreferrer">{evidence.url}</a> : evidence.url}</dd></>)}
                <dt>Identyfikator</dt><dd className="num">{evidence.id}</dd>
              </dl>
              {key && /\.(png|jpe?g)$/i.test(key) && (
                <img className="drawer__shot" src={evidenceUrl(key)} alt={`Zrzut ekranu: ${evidence.label}`} loading="lazy" />
              )}
              {key && !/\.(png|jpe?g)$/i.test(key) && (
                <ButtonLink href={evidenceUrl(key)} target="_blank" rel="noopener noreferrer">
                  <ExternalLink aria-hidden="true" />Otwórz zarchiwizowaną treść
                </ButtonLink>
              )}
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
