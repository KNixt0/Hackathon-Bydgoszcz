import { lazy, Suspense } from "react";
import { Link, BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import { EmptyState } from "./components/ui/States";
import { IncidentsProvider } from "./hooks/useIncidents";
import { LiveProvider } from "./hooks/useLive";
import { ScanJobsProvider } from "./hooks/useScanJobs";
import { ThresholdsProvider } from "./hooks/useThresholds";
import { UiProvider } from "./hooks/useUi";
import { QueuePage } from "./pages/QueuePage";

const CasePage = lazy(() => import("./pages/CasePage").then((m) => ({ default: m.CasePage })));
const CalibrationPage = lazy(() => import("./pages/CalibrationPage").then((m) => ({ default: m.CalibrationPage })));

function NotFound() {
  return (
    <div className="page">
      <EmptyState
        title="Nie ma takiej strony"
        text="Adres jest nieprawidłowy albo strona została przeniesiona."
        action={<Link to="/" className="btn btn--primary">Wróć do kolejki spraw</Link>}
      />
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <LiveProvider>
          <ThresholdsProvider>
            <UiProvider>
              <IncidentsProvider>
                <ScanJobsProvider>
                  <Routes>
                    <Route element={<AppShell />}>
                      <Route index element={<QueuePage />} />
                      <Route path="sprawy/:id" element={<Suspense fallback={<div className="page" aria-busy="true" />}><CasePage /></Suspense>} />
                      <Route path="kalibracja" element={<Suspense fallback={<div className="page" aria-busy="true" />}><CalibrationPage /></Suspense>} />
                      <Route path="*" element={<NotFound />} />
                    </Route>
                  </Routes>
                </ScanJobsProvider>
              </IncidentsProvider>
            </UiProvider>
          </ThresholdsProvider>
        </LiveProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

