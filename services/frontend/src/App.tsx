import type { ReactNode } from "react";
import { Route, Routes } from "react-router-dom";
import type { SocketFactory } from "./api/socket";
import { AppShell } from "./components/layout/AppShell";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import type { Thresholds } from "./domain/levels";
import { IncidentsProvider } from "./hooks/useIncidents";
import { LiveProvider } from "./hooks/useLive";
import { ScanJobsProvider } from "./hooks/useScanJobs";
import { ThresholdsProvider } from "./hooks/useThresholds";
import { UiProvider } from "./hooks/useUi";
import { CalibrationPage } from "./pages/CalibrationPage";
import { CasePage } from "./pages/CasePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { QueuePage } from "./pages/QueuePage";

interface ProvidersProps {
  children: ReactNode;
  socketFactory?: SocketFactory;
  initialThresholds?: Thresholds;
}

/** All app-wide state. Tests reuse it with a fake socket. */
export function AppProviders({ children, socketFactory, initialThresholds }: ProvidersProps) {
  return (
    <ThresholdsProvider initial={initialThresholds}>
      <LiveProvider socketFactory={socketFactory}>
        <IncidentsProvider>
          <ScanJobsProvider>
            <UiProvider>{children}</UiProvider>
          </ScanJobsProvider>
        </IncidentsProvider>
      </LiveProvider>
    </ThresholdsProvider>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<QueuePage />} />
        <Route path="sprawy/:id" element={<CasePage />} />
        <Route path="kalibracja" element={<CalibrationPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export function App({ socketFactory }: { socketFactory?: SocketFactory }) {
  return (
    <ErrorBoundary>
      <AppProviders socketFactory={socketFactory}>
        <AppRoutes />
      </AppProviders>
    </ErrorBoundary>
  );
}
