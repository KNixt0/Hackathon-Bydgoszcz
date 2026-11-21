import { useEffect, useMemo } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { countLevels } from "../../domain/levels";
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
import { ScanDialog } from "./ScanDialog";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { UserChip } from "./UserChip";

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);

/** Container: wires providers' state into the presentational chrome. */
export function AppShell() {
  const navigate = useNavigate();
  const { thresholds, isGlobal } = useThresholds();
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

  const counts = useMemo(
    () => (incidents.phase === "ready" ? countLevels(incidents.items.map((i) => i.risk_score), thresholds) : null),
    [incidents.phase, incidents.items, thresholds],
  );

  const triggerDemo = async () => {
    const failure = await scans.triggerDemo();
    notify(failure ? "error" : "info", failure ?? "Próbka demo została przekazana do potoku. Postęp widać w zadaniach.");
  };
  const importSamples = async () => {
    const failure = await scans.importSamples();
    notify(failure ? "error" : "info", failure ?? "Import próbek rozpoczęty. Nowe sprawy pojawią się w kolejce.");
  };
  const startScan = async (req: Parameters<typeof scans.startScan>[0]) => {
    const failure = await scans.startScan(req);
    if (!failure) notify("info", "Skanowanie zlecone. Postęp widać w zadaniach.");
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
      <Sidebar thresholds={thresholds} thresholdsAreGlobal={isGlobal} counts={counts} connection={connection} isSupervisor={user.role === "SUPERVISOR"} />
      <div className="main">
        <TopBar
          onOpenPalette={() => ui.setPaletteOpen(true)} onOpenScan={() => ui.setScanOpen(true)} shortcutLabel={isMac ? "⌘K" : "Ctrl K"}
          trailing={<UserChip user={user} onLogout={() => void logout()} />}
        >
          <JobsMenu jobs={scans.jobs} activeCount={scans.activeCount} onClearFinished={scans.clearFinished} />
          <DemoMenu onTriggerDemo={() => void triggerDemo()} onImportSamples={() => void importSamples()} />
        </TopBar>
        <main id="tresc" tabIndex={-1} style={{ outline: "none" }}>
          <Outlet />
        </main>
      </div>
      <CommandPalette open={ui.paletteOpen} onOpenChange={ui.setPaletteOpen} incidents={incidents.items} thresholds={thresholds} onCommand={onCommand} />
      <ScanDialog open={ui.scanOpen} onOpenChange={ui.setScanOpen} onSubmit={startScan} />
      <Notices notices={ui.notices} onDismiss={ui.dismissNotice} />
    </div>
  );
}
