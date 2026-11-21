import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { errorMessage } from "../api/client";
import { api } from "../api/endpoints";
import { upsertJob } from "../domain/liveState";
import type { ScanJob, ScanRequest } from "../types/api";
import { useLiveEvent } from "./useLive";

interface ScanJobsContextValue {
  jobs: ScanJob[];
  activeCount: number;
  /** Each action resolves to null on success or a Polish error message. */
  startScan: (req: ScanRequest) => Promise<string | null>;
  triggerDemo: () => Promise<string | null>;
  importSamples: () => Promise<string | null>;
  clearFinished: () => void;
}

const ScanJobsContext = createContext<ScanJobsContextValue | null>(null);

const placeholder = (id: string, url: string): ScanJob => ({
  id, url, state: "queued", incident_id: null, error: null, created_at: new Date().toISOString(), finished_at: null,
});

export function ScanJobsProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<ScanJob[]>([]);

  // Jobs that were already running when the page opened (best effort: the panel simply starts empty on failure).
  useEffect(() => {
    const controller = new AbortController();
    api
      .listScans(controller.signal)
      .then((res) => {
        if (controller.signal.aborted || !Array.isArray(res.items)) return;
        const running = res.items.filter((j) => j.state !== "done" && j.state !== "failed");
        setJobs((prev) => running.reduce((acc, j) => (acc.some((p) => p.id === j.id) ? acc : [...acc, j]), prev));
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  useLiveEvent("scan:progress", (job) => {
    // A progress event may arrive before the POST resolves: keep whichever is further along.
    setJobs((prev) => upsertJob(prev, job));
  });

  const track = useCallback((id: string, url: string) => {
    setJobs((prev) => (prev.some((j) => j.id === id) ? prev : upsertJob(prev, placeholder(id, url))));
  }, []);

  const startScan = useCallback(async (req: ScanRequest) => {
    try {
      const res = await api.startScan(req);
      track(res.job_id, req.url);
      return null;
    } catch (err) {
      return errorMessage(err);
    }
  }, [track]);

  const triggerDemo = useCallback(async () => {
    try {
      const res = await api.triggerDemo();
      track(res.job_id, "Próbka demonstracyjna");
      return null;
    } catch (err) {
      return errorMessage(err);
    }
  }, [track]);

  const importSamples = useCallback(async () => {
    try {
      const res = await api.importSamples();
      (res.job_ids ?? []).forEach((id, i) => track(id, `Import próbek (${i + 1}/${res.job_ids.length})`));
      return null;
    } catch (err) {
      return errorMessage(err);
    }
  }, [track]);

  const clearFinished = useCallback(() => setJobs((prev) => prev.filter((j) => j.state !== "done" && j.state !== "failed")), []);

  const value = useMemo(
    () => ({
      jobs,
      activeCount: jobs.filter((j) => j.state !== "done" && j.state !== "failed").length,
      startScan, triggerDemo, importSamples, clearFinished,
    }),
    [jobs, startScan, triggerDemo, importSamples, clearFinished],
  );
  return <ScanJobsContext.Provider value={value}>{children}</ScanJobsContext.Provider>;
}

export function useScanJobs(): ScanJobsContextValue {
  const ctx = useContext(ScanJobsContext);
  if (!ctx) throw new Error("useScanJobs must be used inside ScanJobsProvider");
  return ctx;
}
