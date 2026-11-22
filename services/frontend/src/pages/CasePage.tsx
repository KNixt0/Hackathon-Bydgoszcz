import { Download, FlaskConical, OctagonAlert, Scale } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { api, exportCsvUrl, exportPdfUrl } from "../api/endpoints";
import { DebateBlock } from "../components/case/DebateBlock";
import { DecisionHistory } from "../components/case/DecisionHistory";
import { EvidenceDrawer } from "../components/case/EvidenceDrawer";
import { EvidenceProvider } from "../components/case/EvidenceContext";
import { SourcesBlock } from "../components/case/SourcesBlock";
import { VerdictBlock } from "../components/case/VerdictBlock";
import { VISUAL_TABS, VisualsBlock, type VisualTab } from "../components/case/VisualsBlock";
import { WorkflowPanel } from "../components/case/WorkflowPanel";
import { ObservationPanel } from "../components/case/ObservationPanel";
import { PartiesCard } from "../components/case/PartiesCard";
import { RegistryChecks } from "../components/case/RegistryChecks";
import { caseRef } from "../components/queue/QueueTable";
import { Badge } from "../components/ui/Badge";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { formatDateTime, hostOf, safeHref } from "../domain/format";
import { MODULE_LABEL, PLATFORM_LABEL, SCOPE_CATEGORY_LABEL } from "../domain/labels";
import { deriveLevel } from "../domain/levels";
import { useUser } from "../hooks/useAuth";
import { useIncidents } from "../hooks/useIncidents";
import { useLiveEvent } from "../hooks/useLive";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import type { TransitionRequest } from "../types/api";
import type { CaseLabel, Incident } from "../types/incident";

function defaultTab(incident: Incident): VisualTab {
  if (incident.graph.flagged_paths.length > 0) return "powiazania";
  return "zgodnosc";
}

function CaseSkeleton() {
  return (
    <div className="page" aria-busy="true" aria-label="Wczytywanie sprawy">
      <Skeleton width={180} height={12} />
      <Skeleton width="55%" height={32} />
      <div className="case-grid">
        <div className="case-col" style={{ display: "grid", gap: 12 }}>
          <Skeleton height={180} /><Skeleton width="70%" height={20} /><Skeleton height={60} /><Skeleton height={24} />
        </div>
        <div className="case-col" style={{ display: "grid", gap: 12 }}><Skeleton height={140} /><Skeleton height={100} /></div>
      </div>
    </div>
  );
}

export function CasePage() {
  const { id = "" } = useParams();
  const { thresholds } = useThresholds();
  const { transition, assign, setLabel } = useIncidents();
  const user = useUser();
  const [params, setParams] = useSearchParams();
  const [statusBusy, setStatusBusy] = useState(false);
  const history = useResource((signal) => api.history(id, signal), `history:${id}`);
  const { refresh: refreshHistory } = history;
  const versions = useResource((signal) => api.versions(id, signal), `versions:${id}`);
  const { refresh: refreshVersions } = versions;
  const [notFound, setNotFound] = useState(false);

  const { resource, reload, refresh, setData } = useResource(
    async (signal) => {
      try {
        const incident = await api.getIncident(id, signal);
        setNotFound(false);
        return incident;
      } catch (err) {
        setNotFound(err instanceof ApiError && err.status === 404);
        throw err;
      }
    },
    `incident:${id}`,
  );

  // Another analyst (or a re-analysis) changed this case: refresh without dropping the screen.
  useLiveEvent("incident:updated", (summary) => {
    if (summary.id === id) {
      refresh();
      refreshHistory();
      refreshVersions();
    }
  });

  const incident = resource.phase === "ready" ? resource.data : null;
  const title = incident?.title;
  useEffect(() => {
    document.title = title ? `${title} · WatchIt` : "WatchIt · UKNF";
    return () => {
      document.title = "WatchIt · UKNF";
    };
  }, [title]);

  // Deep links with a section anchor: the target only exists once the case has loaded.
  const loadedId = incident?.id;
  useEffect(() => {
    if (!loadedId || !window.location.hash) return;
    const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    if (target && typeof target.scrollIntoView === "function") target.scrollIntoView();
  }, [loadedId]);

  const evidenceId = params.get("dowod");
  const openEvidence = useCallback(
    (evId: string) => setParams((prev) => { const p = new URLSearchParams(prev); p.set("dowod", evId); return p; }, { replace: Boolean(evidenceId) }),
    [setParams, evidenceId],
  );
  const closeEvidence = useCallback(
    () => setParams((prev) => { const p = new URLSearchParams(prev); p.delete("dowod"); return p; }, { replace: true }),
    [setParams],
  );
  const setTab = useCallback(
    (tab: VisualTab) => setParams((prev) => { const p = new URLSearchParams(prev); p.set("widok", tab); return p; }, { replace: true }),
    [setParams],
  );

  /** One workflow call: busy flag, fresh case + history on success, a Polish message on failure (shown by the panel). */
  const act = useCallback(
    async (call: () => Promise<Incident>, failurePrefix: string): Promise<string | null> => {
      setStatusBusy(true);
      try {
        setData(await call());
        refreshHistory();
        return null;
      } catch (err) {
        return `${failurePrefix} ${err instanceof Error ? err.message : ""}`.trim();
      } finally {
        setStatusBusy(false);
      }
    },
    [setData, refreshHistory],
  );
  const onTransition = useCallback((body: TransitionRequest) => act(() => transition(id, body), "Nie zmieniono etapu sprawy."), [act, transition, id]);
  const onAssign = useCallback(() => act(() => assign(id), "Nie przejęto sprawy."), [act, assign, id]);
  const onRescan = useCallback(async (): Promise<string | null> => {
    try {
      await api.rescan(id);
      return null;
    } catch (err) {
      return `Nie zlecono sprawdzenia. ${err instanceof Error ? err.message : ""}`.trim();
    }
  }, [id]);
  const onLabel = useCallback((label: CaseLabel) => act(() => setLabel(id, label), "Nie zapisano oceny."), [act, setLabel, id]);

  if (resource.phase === "loading") return <CaseSkeleton />;
  if (resource.phase === "error") {
    return (
      <div className="page">
        <div className="panel panel--flush">
          {notFound ? (
            <EmptyState title="Nie ma takiej sprawy" text="Sprawa o tym identyfikatorze nie istnieje albo została usunięta." action={<Link className="btn btn--primary" to="/">Wróć do kolejki</Link>} />
          ) : (
            <ErrorState title="Nie udało się wczytać sprawy" message={resource.error} onRetry={reload} />
          )}
        </div>
      </div>
    );
  }

  const inc = resource.data;
  const widok = params.get("widok");
  const tab: VisualTab = VISUAL_TABS.includes(widok as VisualTab) ? (widok as VisualTab) : defaultTab(inc);

  const level = deriveLevel(inc.risk_score, thresholds);
  const href = safeHref(inc.source.url);
  const parties = [inc.entities.investment_firm, inc.entities.advertiser].filter((p, k, all) => p && all.findIndex((q) => q?.name === p.name) === k);

  return (
    <EvidenceProvider evidence={inc.evidence} onOpen={openEvidence}>
      <div className="page case">
        <header className="case-head">
          <nav className="crumbs" aria-label="Okruszki">
            <Link to="/">Kolejka spraw</Link><span aria-hidden="true">›</span><span aria-current="page">Sprawa {caseRef(inc.id)}</span>
          </nav>
          <div className="case-head__badges">
            {level === "red" && <Badge tone="red"><OctagonAlert aria-hidden="true" />Krytyczne</Badge>}
            {inc.status === "new" && <Badge tone="accent">Nowa</Badge>}
            {inc.synthetic && (
              <Badge tone="plain" title="Materiał przygotowany na potrzeby demonstracji, nie pochodzi z rzeczywistego źródła">
                <FlaskConical aria-hidden="true" />Dane syntetyczne
              </Badge>
            )}
          </div>
          <h1 className="case-head__title">{inc.title}</h1>
          <nav className="case-nav" aria-label="Sekcje sprawy">
            <span className="muted">Na tej stronie:</span>
            <a href="#werdykt">Werdykt AI</a>
            <a href="#workflow-h">Postępowanie</a>
            <a href="#obserwacja">Weryfikacja</a>
            <a href="#wizualizacje">Analiza</a>
            <a href="#rekomendacja">Rekomendacja AI</a>
            <a href="#zrodla">Źródła dowodowe</a>
            <a href="#historia">Historia decyzji</a>
          </nav>
        </header>

        <div className="case-grid">
          <div className="case-col">
            <dl className="kv case-meta" aria-label="Dane sprawy">
              <dt>Sygnatura</dt><dd><span className="num">{caseRef(inc.id)}</span> <span className="muted">({inc.id})</span></dd>
              <dt>Pierwsze wykrycie</dt><dd>{formatDateTime(inc.created_at)}</dd>
              <dt>Podmiot</dt>
              <dd>{parties.length ? parties.map((p) => p && `${p.name}${p.krs ? `, KRS ${p.krs}` : ""}`).join("; ") : <span className="muted">nieustalony</span>}</dd>
              <dt>Źródło</dt>
              <dd>
                {PLATFORM_LABEL[inc.source.platform] ?? inc.source.platform},{" "}
                {href ? <a href={href} target="_blank" rel="noopener noreferrer">{hostOf(inc.source.url)}<span className="sr-only"> (otwiera się w nowej karcie)</span></a> : hostOf(inc.source.url)}
              </dd>
              <dt>Moduły</dt>
              <dd>{inc.scope?.in_scope === false ? <span className="muted">żaden: materiał poza właściwością UKNF</span> : inc.modules.map((m) => `${m} ${MODULE_LABEL[m]}`).join("; ")}</dd>
              <dt>Aktualizacja</dt><dd>{formatDateTime(inc.updated_at)}</dd>
              <dt>Silnik</dt>
              <dd>{inc.engine.version}{inc.engine.llm_used && inc.engine.model ? `, model ${inc.engine.model}` : ", bez modelu językowego"}, {(inc.engine.duration_ms / 1000).toFixed(1).replace(".", ",")} s</dd>
            </dl>
            {inc.scope && !inc.scope.in_scope && (
              <div className="callout callout--compact" data-testid="out-of-scope" role="note">
                <p className="callout__lead"><Scale aria-hidden="true" />Poza właściwością UKNF</p>
                <p>
                  {SCOPE_CATEGORY_LABEL[inc.scope.category]}. {inc.scope.reason}
                  {inc.scope.authority_hint ? ` Wskazówka: ${inc.scope.authority_hint}` : ""}
                </p>
              </div>
            )}
            <VerdictBlock incident={inc} thresholds={thresholds} />
            <WorkflowPanel incident={inc} user={user} busy={statusBusy} onTransition={onTransition} onAssign={onAssign} onLabel={onLabel} />
            <ObservationPanel
              incident={inc}
              versions={versions.resource.phase === "ready" ? versions.resource.data.items ?? [] : null}
              error={versions.resource.phase === "error" ? versions.resource.error : null}
              onRetry={versions.reload}
              onRescan={onRescan}
            />
          </div>
          <div className="case-col">
            <section className="csec csec--first" aria-labelledby="rejestry-h">
              <h2 className="section-title" id="rejestry-h">Rejestry</h2>
              <RegistryChecks checks={inc.registry_checks} />
            </section>
            <section className="csec" aria-labelledby="podmioty-h">
              <h2 className="section-title" id="podmioty-h">Podmioty</h2>
              <PartiesCard entities={inc.entities} registryChecks={inc.registry_checks} inScope={inc.scope?.in_scope !== false} />
            </section>
            <section className="csec" aria-labelledby="pliki-h">
              <h2 className="section-title" id="pliki-h">Pliki do pobrania</h2>
              <ul className="files">
                <li>
                  <a href={exportPdfUrl(inc.id)} download={`raport-z-wykrycia-${inc.id}.pdf`}><Download aria-hidden="true" />Pobierz raport z wykrycia</a>
                  <span>Dokument do druku: wykrycie, dowody, rejestry, stan materiału i historia decyzji</span>
                </li>
                <li>
                  <a href={exportCsvUrl(inc.id)} download={`sprawa-${inc.id}.csv`}><Download aria-hidden="true" />Pobierz dane sprawy</a>
                  <span>Arkusz kalkulacyjny: kryteria i ustalenia</span>
                </li>
              </ul>
            </section>
            <DecisionHistory
              items={history.resource.phase === "ready" ? history.resource.data.items ?? [] : null}
              error={history.resource.phase === "error" ? history.resource.error : null}
              onRetry={history.reload}
            />
          </div>
        </div>

        <VisualsBlock incident={inc} tab={tab} onTabChange={setTab} />
        <DebateBlock debate={inc.debate} recommendation={inc.recommendation} />
        <SourcesBlock evidence={inc.evidence} source={inc.source} onOpen={openEvidence} />
      </div>
      <EvidenceDrawer incident={inc} evidenceId={evidenceId} onClose={closeEvidence} onNavigate={openEvidence} />
    </EvidenceProvider>
  );
}
