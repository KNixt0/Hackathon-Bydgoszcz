import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useIncidents } from "../../hooks/useIncidents";
import { useAuth, useUser } from "../../hooks/useAuth";
import { useConnectionStatus } from "../../hooks/useLive";
import { useScanJobs } from "../../hooks/useScanJobs";
import { useThresholds } from "../../hooks/useThresholds";
import { useUi } from "../../hooks/useUi";
import { Notices } from "../ui/Notices";
import { CommandPalette, type PaletteCommand } from "./CommandPalette";
import { DemoMenu } from "./DemoMenu";
import { JobsMenu } from "./JobsMenu";
import { NotificationsMenu } from "./NotificationsMenu";
import { ScanDialog } from "./ScanDialog";
import { ConnectionIndicator } from "./ConnectionIndicator";
import { Header } from "./Header";
import { UserChip } from "./UserChip";

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);

/** Container: wires providers' state into the presentational chrome. */
export function AppShell() {
  const navigate = useNavigate();
  const { thresholds } = useThresholds();
  const user = useUser();
  const { logout } = useAuth();
  const incidents = useIncidents();
  const connection = useConnectionStatus();
  const scans = useScanJobs();
  const ui = useUi();
  const { setPaletteOpen, notify } = ui;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setPaletteOpen]);

  const triggerDemo = async () => {
    const failure = await scans.triggerDemo();
    notify(failure ? "error" : "info", failure ?? "Próbka demonstracyjna została przekazana do analizy. Postęp widać w zadaniach.");
  };
  const importSamples = async () => {
    const failure = await scans.importSamples();
    notify(failure ? "error" : "info", failure ?? "Import próbek rozpoczęty. Nowe sprawy pojawią się w kolejce.");
  };
  const startScan = async (req: Parameters<typeof scans.startScan>[0]) => {
    const failure = await scans.startScan(req);
    if (!failure) notify("info", "Analiza zlecona. Postęp widać w zadaniach.");
    return failure;
  };

  const onCommand = (command: PaletteCommand) => {
    if (command.type === "navigate") navigate(command.to);
    else if (command.type === "scan") ui.setScanOpen(true);
    else void triggerDemo();
  };

  return (
    <div className="shell">
      <a className="skip-link" href="#tresc">Przejdź do treści</a>
      <Header
        onOpenPalette={() => ui.setPaletteOpen(true)} onOpenScan={() => ui.setScanOpen(true)} shortcutLabel={isMac ? "⌘K" : "Ctrl K"}
        isSupervisor={user.role === "SUPERVISOR"}
        trailing={<UserChip user={user} onLogout={() => void logout()} />}
      >
        <JobsMenu jobs={scans.jobs} activeCount={scans.activeCount} onClearFinished={scans.clearFinished} />
        <NotificationsMenu />
        <DemoMenu onTriggerDemo={() => void triggerDemo()} onImportSamples={() => void importSamples()} />
        <ConnectionIndicator status={connection} />
      </Header>
      <main id="tresc" tabIndex={-1} className="main">
        <Outlet />
      </main>
      <footer className="foot">Narzędzie analityczne UKNF, prototyp. Dane są przetwarzane lokalnie. <span data-testid="build-version">Wersja 2026.11.22.2</span></footer>
      <CommandPalette open={ui.paletteOpen} onOpenChange={ui.setPaletteOpen} incidents={incidents.items} thresholds={thresholds} onCommand={onCommand} />
      <ScanDialog open={ui.scanOpen} onOpenChange={ui.setScanOpen} onSubmit={startScan} />
      <Notices notices={ui.notices} onDismiss={ui.dismissNotice} />
    </div>
  );
}
