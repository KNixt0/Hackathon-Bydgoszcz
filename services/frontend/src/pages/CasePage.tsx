import * as Tabs from "@radix-ui/react-tabs";
import { ArrowLeft, Download, ExternalLink, FileText } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, exportCsvUrl, exportPdfUrl } from "../api/endpoints";
import { DebateView } from "../components/case/DebateView";
import { EvidenceChips } from "../components/case/EvidenceChips";
import { EvidenceContext } from "../components/case/EvidenceContext";
import { EvidenceDrawer } from "../components/case/EvidenceDrawer";
import { ForensicsView } from "../components/case/ForensicsView";
import { FinancialsPanel, RegistryTable } from "../components/case/RegistryPanel";
import { RelationGraph } from "../components/case/RelationGraph";
import { RulesMatrix } from "../components/case/RulesMatrix";
import { SourceText } from "../components/case/SourceText";
import { Badge } from "../components/ui/Badge";
import { ButtonLink } from "../components/ui/Button";
import { LevelBadge } from "../components/ui/LevelBadge";
import { ModuleTag } from "../components/ui/ModuleTag";
import { Panel } from "../components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { ScoreRail } from "../components/ui/ScoreRail";
import { formatDateTime, formatScore, hostOf, safeHref } from "../domain/format";
import { ACTION_LABEL, PLATFORM_LABEL, SEVERITY_LABEL, STATUS_LABEL, STATUSES } from "../domain/labels";
import { complianceScore, deriveLevel } from "../domain/levels";
import { toSummary, useIncidents } from "../hooks/useIncidents";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import { useUi } from "../hooks/useUi";
import type { Incident, Status } from "../types/incident";

function CaseBody({ incident, onChanged }: { incident: Incident; onChanged: (i: Incident) => void }) {
  const { thresholds } = useThresholds();
  const { changeStatus } = useIncidents();
  const { notify } = useUi();
  const [openId, setOpenId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const byId = useMemo(() => new Map(incident.evidence.map((e) => [e.id, e])), [incident.evidence]);
  const ctx = useMemo(() => ({ byId, open: setOpenId }), [byId]);
  const level = deriveLevel(incident.risk_score, thresholds);
  const href = safeHref(incident.source.url);
  const { advertiser, investment_firm: firm } = incident.entities;
  const hasGraph = incident.graph.nodes.length > 0;
  const failed = incident.rules.filter((r) => r.status === "fail").length;

  const updateStatus = async (status: Status) => {
    setBusy(true);
    try {
      onChanged(await changeStatus(incident.id, status));
      notify("success", `Status zmieniony: ${STATUS_LABEL[status]}.`);
    } catch (err) {
      notify("error", err instanceof Error ? err.message : "Nie udało się zmienić statusu.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <EvidenceContext.Provider value={ctx}>
      <div className="page">
        <Link to="/" className="backlink"><ArrowLeft aria-hidden="true" size={14} />Kolejka spraw</Link>

        <header className={`casehead casehead--${level}`}>
          <div className="casehead__main">
            <div className="casehead__tags">
              {incident.modules.map((m) => <ModuleTag key={m} module={m} />)}
              <Badge tone="neutral">{PLATFORM_LABEL[incident.source.platform]}</Badge>
              {incident.synthetic && <Badge tone="neutral" title="Materiał syntetyczny, przygotowany na potrzeby demonstracji">Syntetyczne</Badge>}
            </div>
            <h1 className="page__title">{incident.title}</h1>
            <p className="casehead__summary">{incident.summary}</p>
            <dl className="kv casehead__kv">
              <dt>Reklamujący</dt><dd>{advertiser?.name ?? "nieustalony"}</dd>
              <dt>Firma inwestycyjna</dt><dd>{firm?.name ?? "nieustalona"}</dd>
              <dt>Adres</dt>
              <dd>{href ? <a href={href} target="_blank" rel="noopener noreferrer">{hostOf(incident.source.url)}<ExternalLink size={11} aria-hidden="true" style={{ marginLeft: 4 }} /></a> : incident.source.url}</dd>
              <dt>Wykryto</dt><dd>{formatDateTime(incident.created_at)}</dd>
            </dl>
          </div>
          <aside className="casehead__side" aria-label="Werdykt">
            <LevelBadge level={level} size="lg" />
            <div className="scorebox">
              <div><span className="scorebox__n num">{formatScore(incident.risk_score)}</span><span className="muted"> / 100 ryzyka</span></div>
              <div className="muted">Compliance Score: <strong className="num">{complianceScore(incident.risk_score)}</strong>/100</div>
            </div>
            <ScoreRail riskScore={incident.risk_score} thresholds={thresholds} wide showValue={false} />
            <label className="field">
              <span className="field__label">Status sprawy</span>
              <select className="select" value={incident.status} disabled={busy} onChange={(e) => void updateStatus(e.target.value as Status)}>
                {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
              </select>
            </label>
            <div className="casehead__exports">
              <ButtonLink href={exportPdfUrl(incident.id)} download><FileText aria-hidden="true" />Pakiet PDF</ButtonLink>
              <ButtonLink href={exportCsvUrl(incident.id)} download><Download aria-hidden="true" />CSV</ButtonLink>
            </div>
          </aside>
        </header>

        <section className={`reco reco--${incident.recommendation.action}`} aria-label="Rekomendacja">
          <strong>Rekomendacja: {incident.recommendation.label || ACTION_LABEL[incident.recommendation.action]}</strong>
          <span>{incident.recommendation.next_step}</span>
        </section>

        <Tabs.Root defaultValue="verdict" className="tabs">
          <Tabs.List className="tabs__list" aria-label="Sekcje sprawy">
            <Tabs.Trigger className="tabs__tab" value="verdict">Werdykt i kryteria{failed > 0 && <span className="tabs__count">{failed}</span>}</Tabs.Trigger>
            <Tabs.Trigger className="tabs__tab" value="graph">Powiązania{incident.graph.flagged_paths.length > 0 && <span className="tabs__count">{incident.graph.flagged_paths.length}</span>}</Tabs.Trigger>
            <Tabs.Trigger className="tabs__tab" value="forensics">Opinie i konta{incident.forensics && incident.forensics.anomalies.length > 0 && <span className="tabs__count">{incident.forensics.anomalies.length}</span>}</Tabs.Trigger>
            <Tabs.Trigger className="tabs__tab" value="debate">Debata za i przeciw</Tabs.Trigger>
            <Tabs.Trigger className="tabs__tab" value="source">Treść i rejestry</Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="verdict" className="tabs__panel">
            <Panel title="Wyniki modułów analitycznych" hint="Każdy moduł ocenia materiał niezależnie, agregator łączy wyniki w jeden wynik ryzyka.">
              <div className="modules">
                {incident.module_results.map((mr) => (
                  <div key={mr.plugin} className="modcard">
                    <div className="modcard__head"><ModuleTag module={mr.module} /><span className="num modcard__score">{formatScore(mr.score)}</span></div>
                    <p className="muted">Wtyczka {mr.plugin}, waga <span className="num">{mr.weight}</span></p>
                    <ul className="findings">
                      {mr.findings.map((f, i) => (
                        <li key={i}>
                          <Badge tone={f.severity === "high" ? "red" : f.severity === "medium" ? "orange" : "neutral"}>{SEVERITY_LABEL[f.severity]}</Badge>
                          <span>{f.text}</span>
                          <EvidenceChips ids={f.evidence_ids} />
                        </li>
                      ))}
                      {mr.findings.length === 0 && <li className="muted">Brak ustaleń.</li>}
                    </ul>
                  </div>
                ))}
              </div>
            </Panel>
            <Panel title="Macierz 18 kryteriów UKNF" hint="Każdy wiersz wskazuje podstawę prawną, pewność oceny i dowody.">
              <RulesMatrix rules={incident.rules} />
            </Panel>
          </Tabs.Content>

          <Tabs.Content value="graph" className="tabs__panel">
            <Panel title="Graf powiązań" hint="Zarząd, agencja PR, influencer i materiał. Czerwone krawędzie to relacje podejrzane.">
              {hasGraph ? <RelationGraph graph={incident.graph} /> : <EmptyState compact title="Brak danych o powiązaniach" text="Dla tej sprawy nie zebrano relacji między podmiotami." />}
            </Panel>
            {incident.financials && <Panel title="Dane finansowe reklamującego"><FinancialsPanel data={incident.financials} /></Panel>}
          </Tabs.Content>

          <Tabs.Content value="forensics" className="tabs__panel">
            <Panel title="Analiza wiarygodności opinii" hint="Wzorce świadczące o sztucznie pozyskanych lub zmanipulowanych opiniach.">
              {incident.forensics ? <ForensicsView data={incident.forensics} /> : <EmptyState compact title="Brak opinii do analizy" text="Materiał nie zawierał opinii ani komentarzy." />}
            </Panel>
          </Tabs.Content>

          <Tabs.Content value="debate" className="tabs__panel">
            <Panel title="Debata agentów z krytyką wzajemną" hint="Argumenty za naruszeniem i okoliczności łagodzące po krytyce, z rozstrzygnięciem arbitra.">
              <DebateView debate={incident.debate} />
            </Panel>
          </Tabs.Content>

          <Tabs.Content value="source" className="tabs__panel">
            <Panel title="Treść materiału" hint="Wyróżnione fragmenty są dosłownymi cytatami użytymi jako dowody. Kliknij, aby zobaczyć szczegóły.">
              <SourceText text={incident.source.text} evidence={incident.evidence} />
            </Panel>
            <Panel title="Sprawdzenie w rejestrach"><RegistryTable checks={incident.registry_checks} /></Panel>
            <Panel title={`Wszystkie dowody (${incident.evidence.length})`}>
              {incident.evidence.length ? <EvidenceChips ids={incident.evidence.map((e) => e.id)} /> : <p className="muted">Brak dowodów.</p>}
              <p className="muted engine">Silnik {incident.engine.version}, wtyczki: {incident.engine.plugins.join(", ") || "brak"}; {incident.engine.llm_used ? `model lokalny ${incident.engine.model ?? ""}` : "analiza regułowa bez modelu językowego"}; czas {incident.engine.duration_ms} ms.</p>
            </Panel>
          </Tabs.Content>
        </Tabs.Root>
      </div>
      <EvidenceDrawer evidence={openId ? byId.get(openId) ?? null : null} sourceText={incident.source.text} onClose={() => setOpenId(null)} />
    </EvidenceContext.Provider>
  );
}

export function CasePage() {
  const { id = "" } = useParams();
  const loader = useCallback((signal: AbortSignal) => api.getIncident(id, signal), [id]);
  const { resource, reload, setData } = useResource(loader, `incident:${id}`);
  const { items } = useIncidents();

  // keep the open case in step with live status changes made elsewhere
  const live = items.find((i) => i.id === id);
  const data = useMemo(() => {
    if (resource.phase !== "ready") return null;
    return live && live.updated_at > resource.data.updated_at ? { ...resource.data, ...pickLive(live) } : resource.data;
  }, [resource, live]);

  if (resource.phase === "loading") return <div className="page"><Skeleton height={26} width={320} /><Skeleton height={160} /><Skeleton height={320} /></div>;
  if (resource.phase === "error" || !data) {
    return (
      <div className="page">
        <Link to="/" className="backlink"><ArrowLeft aria-hidden="true" size={14} />Kolejka spraw</Link>
        <ErrorState title="Nie udało się otworzyć sprawy" message={resource.error ?? "Nieznany błąd."} onRetry={reload} />
      </div>
    );
  }
  return <CaseBody incident={data} onChanged={setData} />;
}

function pickLive(s: ReturnType<typeof toSummary>): Partial<Incident> {
  return { status: s.status, updated_at: s.updated_at, risk_score: s.risk_score, compliance_score: s.compliance_score };
}
