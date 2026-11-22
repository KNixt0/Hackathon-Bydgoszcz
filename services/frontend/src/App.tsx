import { createContext, useContext, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { SocketFactory } from "./api/socket";
import { AppShell } from "./components/layout/AppShell";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import type { Thresholds } from "./domain/levels";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { IncidentsProvider } from "./hooks/useIncidents";
import { LiveProvider } from "./hooks/useLive";
import { ScanJobsProvider } from "./hooks/useScanJobs";
import { ThresholdsProvider } from "./hooks/useThresholds";
import { UiProvider } from "./hooks/useUi";
import { AuditPage } from "./pages/AuditPage";
import { CalibrationPage } from "./pages/CalibrationPage";
import { CasePage } from "./pages/CasePage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { QueuePage } from "./pages/QueuePage";

interface ProvidersProps {
  children: ReactNode;
  socketFactory?: SocketFactory;
  initialThresholds?: Thresholds;
}

interface SessionOptions {
  socketFactory?: SocketFactory;
  initialThresholds?: Thresholds;
}
const SessionOptionsContext = createContext<SessionOptions>({});

/** App-wide state that exists before login. Tests reuse it with a fake socket. */
export function AppProviders({ children, socketFactory, initialThresholds }: ProvidersProps) {
  return (
    <SessionOptionsContext.Provider value={{ socketFactory, initialThresholds }}>
      <AuthProvider>
        <UiProvider>{children}</UiProvider>
      </AuthProvider>
    </SessionOptionsContext.Provider>
  );
}

/** State that needs a session (API data, the live socket): mounted only after login, dropped on logout. */
function SessionProviders({ children }: { children: ReactNode }) {
  const { socketFactory, initialThresholds } = useContext(SessionOptionsContext);
  return (
    <ThresholdsProvider initial={initialThresholds}>
      <LiveProvider socketFactory={socketFactory}>
        <IncidentsProvider>
          <ScanJobsProvider>{children}</ScanJobsProvider>
        </IncidentsProvider>
      </LiveProvider>
    </ThresholdsProvider>
  );
}

/** Route guard: everything but /logowanie needs a session. */
function RequireSession() {
  const { state } = useAuth();
  const location = useLocation();
  if (state.phase === "loading") return <div className="boot" aria-busy="true" aria-label="Sprawdzanie sesji" />;
  if (state.phase === "anonymous") return <Navigate to="/logowanie" replace state={{ from: `${location.pathname}${location.search}${location.hash}` }} />;
  return (
    <SessionProviders>
      <AppShell />
    </SessionProviders>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="logowanie" element={<LoginPage />} />
      <Route element={<RequireSession />}>
        <Route index element={<QueuePage />} />
        <Route path="sprawy/:id" element={<CasePage />} />
        <Route path="kalibracja" element={<CalibrationPage />} />
        <Route path="audyt" element={<AuditPage />} />
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
