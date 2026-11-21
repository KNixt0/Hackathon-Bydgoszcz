import * as Dialog from "@radix-ui/react-dialog";
import { ChevronLeft, ChevronRight, ExternalLink, FolderSearch, X } from "lucide-react";
import { useState } from "react";
import { api, evidenceUrl } from "../../api/endpoints";
import { formatDate, formatDateTime, formatPln, safeHref } from "../../domain/format";
import { EVIDENCE_KIND_LABEL, REGISTRY_RESULT_LABEL } from "../../domain/labels";
import { useResource } from "../../hooks/useResource";
import { useRestoreFocus } from "../../hooks/useRestoreFocus";
import { hasScreenshotBox, ScreenshotEvidence } from "../evidence";
import type { Evidence, Incident } from "../../types/incident";
import { Button } from "../ui/Button";
import { ErrorState, Skeleton } from "../ui/States";
import { EVIDENCE_ICON } from "./EvidenceChips";
import { SourceText } from "./SourceText";

function ExternalUrl({ url }: { url: string }) {
  const href = safeHref(url);
  if (!href) return <span style={{ overflowWrap: "anywhere" }}>{url}</span>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" style={{ overflowWrap: "anywhere" }}>
      {url} <ExternalLink size={11} aria-hidden="true" /><span className="sr-only"> (otwiera się w nowej karcie)</span>
    </a>
  );
}

function ArchivedHtml({ storageKey }: { storageKey: string }) {
  const { resource, reload } = useResource((signal) => api.evidenceText(storageKey, signal), `evidence:${storageKey}`);
  if (resource.phase === "loading") return <Skeleton height={120} />;
  if (resource.phase === "error") return <ErrorState compact title="Nie udało się wczytać archiwum" message={resource.error} onRetry={reload} />;
  return <pre className="archive-html" tabIndex={0} aria-label="Zarchiwizowany kod HTML">{resource.data}</pre>;
}

function ArchivedImage({ storageKey, label }: { storageKey: string; label: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <p className="form-error">Nie udało się wczytać zrzutu ekranu z archiwum.</p>;
  return <img className="archive-img" src={evidenceUrl(storageKey)} alt={label} onError={() => setFailed(true)} />;
}

function Archive({ storageKey, label }: { storageKey: string; label: string }) {
  return /\.(png|jpe?g|webp)$/i.test(storageKey) ? <ArchivedImage storageKey={storageKey} label={label} /> : <ArchivedHtml storageKey={storageKey} />;
}

/** Where in the case this evidence is cited (criteria, findings, debate claims). */
function citations(incident: Incident, id: string): { kind: string; text: string }[] {
  const out: { kind: string; text: string }[] = [];
  for (const r of incident.rules) if (r.evidence_ids.includes(id)) out.push({ kind: `Kryterium ${r.id}`, text: r.name });
  for (const m of incident.module_results) for (const f of m.findings) if (f.evidence_ids.includes(id)) out.push({ kind: `Moduł ${m.module}`, text: f.text });
  for (const c of incident.debate.claims) if (c.evidence_ids.includes(id)) out.push({ kind: c.stance === "for" ? "Argument za" : "Argument przeciw", text: c.text });
  return out;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="drawer__section-title">{title}</h3>
      {children}
    </section>
  );
}

function EvidenceBody({ evidence: ev, incident }: { evidence: Evidence; incident: Incident }) {
  const cited = citations(incident, ev.id);
  const registry = ev.kind === "registry" ? incident.registry_checks.filter((c) => c.url === ev.url) : [];
  const accounts = ev.kind === "account" ? incident.forensics?.sample_accounts ?? [] : [];
  const fin = ev.kind === "krs" ? incident.financials : null;
  const isImage = (key: string) => /\.(png|jpe?g|webp)$/i.test(key);
  // a located screenshot is shown by the viewer below, with its box: no second plain copy
  const archiveKey = ev.storage_key && !(ev.bbox && isImage(ev.storage_key)) ? ev.storage_key : null;
  return (
    <>
      {hasScreenshotBox(ev) && <ScreenshotEvidence evidence={ev} incident={incident} />}

      {ev.kind === "quote" && (
        <>
          {ev.quote && (
            <Section title="Cytat">
              <blockquote className="quote">„{ev.quote}”</blockquote>
            </Section>
          )}
          <Section title="Miejsce w zarchiwizowanym tekście">
            <SourceText text={incident.source.text} span={ev.span} quote={ev.quote} />
            {ev.span && <p className="muted" style={{ fontSize: "var(--fs-14)", marginTop: 8 }}>Znaki {ev.span.start}–{ev.span.end} znormalizowanego tekstu, pobranego {formatDateTime(incident.source.fetched_at)}.</p>}
          </Section>
        </>
      )}

      {ev.legal_ref && (
        <Section title="Podstawa prawna">
          <p className="legal" data-testid="legal-ref">{ev.legal_ref}</p>
          {ev.attachment && <p className="muted" style={{ marginTop: 4 }}>Źródło wymogu: {ev.attachment}</p>}
        </Section>
      )}

      {ev.kind === "registry" && (
        <Section title="Wpis w rejestrze">
          {registry.length === 0 ? (
            <p className="muted">Brak szczegółów sprawdzenia dla tego rejestru.</p>
          ) : (
            registry.map((c, i) => (
              <dl key={i} className="kv kv--compact" style={{ marginBottom: 16 }}>
                <dt>Rejestr</dt><dd>{c.label}</dd>
                <dt>Szukano</dt><dd>{c.subject}</dd>
                <dt>Wynik</dt><dd className={`reg-result reg-result--${c.status}`}>{REGISTRY_RESULT_LABEL[c.status] ?? c.status}</dd>
                <dt>Szczegóły</dt><dd>{c.detail}</dd>
                <dt>Stan na</dt><dd>{c.snapshot_date ? formatDate(c.snapshot_date) : "brak migawki"}</dd>
              </dl>
            ))
          )}
        </Section>
      )}

      {ev.kind === "krs" && (
        <Section title="Dane z KRS">
          {fin ? (
            <dl className="kv kv--compact">
              <dt>Spółka</dt><dd>{fin.company}</dd>
              <dt>Numer KRS</dt><dd className="num">{fin.krs ?? "brak danych"}</dd>
              <dt>Data rejestracji</dt><dd>{fin.incorporated_on ? formatDate(fin.incorporated_on) : "brak danych"}</dd>
              <dt>Kapitał zakładowy</dt><dd className="num">{formatPln(fin.share_capital_pln)}</dd>
            </dl>
          ) : <p className="muted">Brak danych rejestrowych dołączonych do sprawy.</p>}
        </Section>
      )}

      {ev.kind === "account" && (
        <Section title={`Próbka podejrzanych kont (${accounts.length})`}>
          {accounts.length === 0 ? <p className="muted">Do sprawy nie dołączono próbki kont.</p> : (
            <ul>
              {accounts.map((a) => (
                <li key={a.handle} className="account">
                  <div className="account__top">
                    <span className="account__handle">{a.handle}</span>
                    <span>założone {formatDate(a.created_at)}, kraj: {a.country}</span>
                  </div>
                  <p>{a.text}</p>
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}

      {archiveKey && (
        <Section title={isImage(archiveKey) ? "Zarchiwizowany zrzut ekranu" : "Zarchiwizowany kod HTML"}>
          <Archive storageKey={archiveKey} label={ev.label} />
          <p className="muted" style={{ fontSize: "var(--fs-14)", marginTop: 8, overflowWrap: "anywhere" }}>Klucz w magazynie obiektów: {archiveKey}</p>
        </Section>
      )}

      {ev.url && (
        <Section title="Adres"><ExternalUrl url={ev.url} /></Section>
      )}

      <Section title="Materiał źródłowy">
        <dl className="kv kv--compact">
          <dt>Adres</dt><dd><ExternalUrl url={incident.source.url} /></dd>
          <dt>Pobrano</dt><dd>{formatDateTime(incident.source.fetched_at)}</dd>
        </dl>
      </Section>

      {cited.length > 0 && (
        <Section title={`Cytowane w sprawie (${cited.length})`}>
          <ul className="cited">
            {cited.map((c, i) => <li key={i}><span className="cited__kind">{c.kind}</span><span>{c.text}</span></li>)}
          </ul>
        </Section>
      )}
    </>
  );
}

interface Props {
  incident: Incident;
  /** id of the open evidence item, or null when the drawer is closed */
  evidenceId: string | null;
  onClose: () => void;
  onNavigate: (id: string) => void;
}

/** Context drawer: one piece of evidence with everything needed to verify it, without leaving the case. */
export function EvidenceDrawer({ incident, evidenceId, onClose, onNavigate }: Props) {
  const index = evidenceId ? incident.evidence.findIndex((e) => e.id === evidenceId) : -1;
  const ev = index >= 0 ? incident.evidence[index] : undefined;
  const prev = index > 0 ? incident.evidence[index - 1] : undefined;
  const next = index >= 0 ? incident.evidence[index + 1] : undefined;
  const Icon = ev ? EVIDENCE_ICON[ev.kind] ?? FolderSearch : FolderSearch;
  const focus = useRestoreFocus();

  return (
    <Dialog.Root open={evidenceId !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="drawer" aria-describedby={undefined} data-testid="evidence-drawer" onOpenAutoFocus={focus.remember} onCloseAutoFocus={focus.restore}>
          <header className="drawer__head">
            <div style={{ minWidth: 0 }}>
              <p className="drawer__kind"><Icon aria-hidden="true" />{ev ? `${EVIDENCE_KIND_LABEL[ev.kind] ?? "Dowód"}, ${index + 1} z ${incident.evidence.length}` : "Dowód"}</p>
              <Dialog.Title className="drawer__title">{ev ? ev.label : "Nie znaleziono dowodu"}</Dialog.Title>
            </div>
            <div className="drawer__nav">
              <Button variant="ghost" iconOnly aria-label="Poprzedni dowód" disabled={!prev} onClick={() => prev && onNavigate(prev.id)}><ChevronLeft aria-hidden="true" /></Button>
              <Button variant="ghost" iconOnly aria-label="Następny dowód" disabled={!next} onClick={() => next && onNavigate(next.id)}><ChevronRight aria-hidden="true" /></Button>
              <Dialog.Close asChild>
                <Button variant="ghost" iconOnly aria-label="Zamknij panel dowodu"><X aria-hidden="true" /></Button>
              </Dialog.Close>
            </div>
          </header>
          <div className="drawer__body">
            {ev ? <EvidenceBody key={ev.id} evidence={ev} incident={incident} /> : (
              <p className="muted">Dowód o identyfikatorze „{evidenceId}” nie należy do tej sprawy. Odnośnik mógł pochodzić z innej wersji analizy.</p>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
