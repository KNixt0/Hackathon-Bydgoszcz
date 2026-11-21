import { ChevronRight, FileQuestion } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import { DebateBlock } from "../components/case/DebateBlock";
import { EvidenceDrawer } from "../components/case/EvidenceDrawer";
import { EvidenceProvider } from "../components/case/EvidenceContext";
import { SourcesBlock } from "../components/case/SourcesBlock";
import { VerdictBlock } from "../components/case/VerdictBlock";
import { VISUAL_TABS, VisualsBlock, type VisualTab } from "../components/case/VisualsBlock";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { formatDateTime, hostOf } from "../domain/format";
import { PLATFORM_LABEL } from "../domain/labels";
import { useIncidents } from "../hooks/useIncidents";
import { useLiveEvent } from "../hooks/useLive";
import { useResource } from "../hooks/useResource";
import { useThresholds } from "../hooks/useThresholds";
import { useUi } from "../hooks/useUi";
import type { Incident, Status } from "../types/incident";

function defaultTab(incident: Incident): VisualTab {
  if (incident.graph.flagged_paths.length > 0) return "powiazania";
  return "zgodnosc";
}

function CaseSkeleton() {
  return (
    <div className="page" aria-busy="true" aria-label="Wczytywanie sprawy">
      <Skeleton width={180} height={12} />
      <Skeleton width="55%" height={26} />
      <Skeleton width="80%" />
      <div className="panel" style={{ padding: 16, display: "grid", gridTemplateColumns: "1fr 1.3fr 1fr", gap: 24 }}>
        <div style={{ display: "grid", gap: 12 }}><Skeleton width={140} height={20} /><Skeleton width={120} height={52} /><Skeleton height={10} /></div>
        <div style={{ display: "grid", gap: 12 }}><Skeleton height={96} /><Skeleton height={28} /></div>
        <div style={{ display: "grid", gap: 12 }}><Skeleton height={40} /><Skeleton height={40} /><Skeleton height={40} /></div>
      </div>
      <div className="panel" style={{ padding: 16 }}><Skeleton height={260} /></div>
    </div>
  );
}

export function CasePage() {
  const { id = "" } = useParams();
  const { thresholds } = useThresholds();
  const { changeStatus } = useIncidents();
  const { notify } = useUi();
  const [params, setParams] = useSearchParams();
  const [statusBusy, setStatusBusy] = useState(false);
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
    if (summary.id === id) refresh();
  });

  const incident = resource.phase === "ready" ? resource.data : null;
  const title = incident?.title;
  useEffect(() => {
    document.title = title ? `${title} · InvestWatch` : "InvestWatch · UKNF";
    return () => {
      document.title = "InvestWatch · UKNF";
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

  const onStatusChange = useCallback(
    (next: Status) => {
      setStatusBusy(true);
      changeStatus(id, next)
        .then((updated) => setData(updated))
        .catch((err: unknown) => notify("error", `Nie zmieniono statusu. ${err instanceof Error ? err.message : ""}`.trim()))
        .finally(() => setStatusBusy(false));
    },
    [changeStatus, id, notify, setData],
  );

  if (resource.phase === "loading") return <CaseSkeleton />;
  if (resource.phase === "error") {
    return (
      <div className="page">
        <div className="panel">
          {notFound ? (
            <EmptyState icon={<FileQuestion />} title="Nie ma takiej sprawy" text="Sprawa o tym identyfikatorze nie istnieje albo została usunięta." action={<Link className="btn btn--primary" to="/">Wróć do kolejki</Link>} />
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

  return (
    <EvidenceProvider evidence={inc.evidence} onOpen={openEvidence}>
      <div className="page">
        <header>
          <nav className="crumbs" aria-label="Okruszki">
            <Link to="/">Kolejka spraw</Link><ChevronRight aria-hidden="true" /><span aria-current="page">Sprawa {inc.id.slice(0, 8)}</span>
          </nav>
          <h1 className="case-head__title" style={{ marginTop: 6 }}>{inc.title}</h1>
          <p className="case-head__summary">{inc.summary}</p>
          <p className="case-head__meta">
            <span>{PLATFORM_LABEL[inc.source.platform] ?? inc.source.platform}, {hostOf(inc.source.url)}</span>
            <span>Wykryto {formatDateTime(inc.created_at)}</span>
            <span>Aktualizacja {formatDateTime(inc.updated_at)}</span>
            <span>Silnik {inc.engine.version}{inc.engine.llm_used && inc.engine.model ? `, model ${inc.engine.model}` : ", bez modelu językowego"}, {(inc.engine.duration_ms / 1000).toFixed(1).replace(".", ",")} s</span>
          </p>
        </header>

        <nav className="case-nav" aria-label="Sekcje sprawy">
          <a href="#werdykt">Werdykt</a>
          <a href="#wizualizacje">Wykresy i wizualizacje</a>
          <a href="#argumenty">Argumenty</a>
          <a href="#zrodla">Źródła dowodowe</a>
        </nav>

        <VerdictBlock incident={inc} thresholds={thresholds} onStatusChange={onStatusChange} statusBusy={statusBusy} />
        <VisualsBlock incident={inc} tab={tab} onTabChange={setTab} />
        <DebateBlock debate={inc.debate} />
        <SourcesBlock evidence={inc.evidence} source={inc.source} onOpen={openEvidence} />
      </div>
      <EvidenceDrawer incident={inc} evidenceId={evidenceId} onClose={closeEvidence} onNavigate={openEvidence} />
    </EvidenceProvider>
  );
}
