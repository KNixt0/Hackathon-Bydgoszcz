import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { errorMessage } from "../api/client";
import { api } from "../api/endpoints";
import { incidentsReducer, INITIAL_INCIDENTS, type IncidentsState } from "../domain/liveState";
import type { TransitionRequest } from "../types/api";
import type { CaseLabel, Incident, IncidentSummary } from "../types/incident";
import { useLiveEvent } from "./useLive";

const FRESH_MS = 12000;

interface IncidentsContextValue extends IncidentsState {
  reload: () => void;
  dismissAlert: (id: string) => void;
  dismissViralAlert: (id: string) => void;
  /** Workflow calls; each resolves with the full incident or throws an Error with a Polish message. */
  transition: (id: string, body: TransitionRequest) => Promise<Incident>;
  assign: (id: string) => Promise<Incident>;
  setLabel: (id: string, label: CaseLabel) => Promise<Incident>;
  /** Bumps whenever the set of incidents changed (trend chart refetches on it). */
  revision: number;
}

const IncidentsContext = createContext<IncidentsContextValue | null>(null);

export function toSummary(inc: Incident): IncidentSummary {
  return {
    id: inc.id, title: inc.title, summary: inc.summary, modules: inc.modules, primary_module: inc.primary_module,
    risk_score: inc.risk_score, compliance_score: inc.compliance_score, risk_level: inc.risk_level, status: inc.status,
    created_at: inc.created_at, updated_at: inc.updated_at, synthetic: inc.synthetic, ground_truth: inc.ground_truth,
    demo_case: inc.demo_case, source: { platform: inc.source.platform, url: inc.source.url },
    advertiser: inc.entities.advertiser?.name ?? null, firm: inc.entities.investment_firm?.name ?? null,
    failed_rules: inc.rules.filter((r) => r.status === "fail").map((r) => r.id),
    workflow: { assigned_to: inc.workflow.assigned_to, label: inc.workflow.label },
    user_reports_count: inc.user_reports_count ?? 0, priority_score: inc.priority_score ?? inc.risk_score,
  };
}

export function IncidentsProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(incidentsReducer, INITIAL_INCIDENTS);
  const [revision, bump] = useReducer((n: number) => n + 1, 0);
  const timers = useRef(new Map<string, number>());

  const load = useCallback((signal?: AbortSignal) => {
    dispatch({ type: "load:start" });
    api
      .listIncidents(signal)
      .then((res) => {
        if (!signal?.aborted) dispatch({ type: "load:ok", items: Array.isArray(res.items) ? res.items : [] });
      })
      .catch((err: unknown) => {
        if (!signal?.aborted) dispatch({ type: "load:error", message: errorMessage(err) });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach((t) => window.clearTimeout(t));
      pending.clear();
    };
  }, []);

  const markFresh = useCallback((id: string) => {
    const existing = timers.current.get(id);
    if (existing) window.clearTimeout(existing);
    timers.current.set(
      id,
      window.setTimeout(() => {
        timers.current.delete(id);
        dispatch({ type: "fresh:clear", id });
      }, FRESH_MS),
    );
  }, []);

  useLiveEvent("incident:new", (incident) => {
    dispatch({ type: "incident:new", incident });
    markFresh(incident.id);
    bump();
  });
  useLiveEvent("incident:updated", (incident) => {
    dispatch({ type: "incident:updated", incident });
    bump();
  });
  useLiveEvent("alert:high", (incident) => {
    dispatch({ type: "alert:high", incident });
    markFresh(incident.id);
  });

  useLiveEvent("alert:viral", (incident) => dispatch({ type: "alert:viral", incident }));

  const run = useCallback(async (call: () => Promise<Incident>) => {
    try {
      const updated = await call();
      dispatch({ type: "incident:updated", incident: toSummary(updated) });
      return updated;
    } catch (err) {
      throw new Error(errorMessage(err), { cause: err });
    }
  }, []);
  const transition = useCallback((id: string, body: TransitionRequest) => run(() => api.transition(id, body)), [run]);
  const assign = useCallback((id: string) => run(() => api.assign(id)), [run]);
  const setLabel = useCallback((id: string, label: CaseLabel) => run(() => api.label(id, label)), [run]);

  const reload = useCallback(() => load(), [load]);
  const dismissAlert = useCallback((id: string) => dispatch({ type: "alert:dismiss", id }), []);

  const dismissViralAlert = useCallback((id: string) => dispatch({ type: "alert:viral:dismiss", id }), []);

  const value = useMemo(
    () => ({ ...state, reload, dismissAlert, dismissViralAlert, transition, assign, setLabel, revision }),
    [state, reload, dismissAlert, dismissViralAlert, transition, assign, setLabel, revision],
  );
  return <IncidentsContext.Provider value={value}>{children}</IncidentsContext.Provider>;
}

export function useIncidents(): IncidentsContextValue {
  const ctx = useContext(IncidentsContext);
  if (!ctx) throw new Error("useIncidents must be used inside IncidentsProvider");
  return ctx;
}
