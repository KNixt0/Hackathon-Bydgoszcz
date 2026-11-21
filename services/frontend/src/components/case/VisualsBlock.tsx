import * as Tabs from "@radix-ui/react-tabs";
import type { Incident } from "../../types/incident";
import { ComplianceMatrix } from "./ComplianceMatrix";
import { FinancialsPanel } from "./FinancialsPanel";
import { ForensicsPanel } from "./ForensicsPanel";
import { RelationshipGraph } from "./RelationshipGraph";

export type VisualTab = "zgodnosc" | "powiazania" | "opinie" | "finanse";
export const VISUAL_TABS: VisualTab[] = ["zgodnosc", "powiazania", "opinie", "finanse"];

interface Props {
  incident: Incident;
  tab: VisualTab;
  onTabChange: (tab: VisualTab) => void;
}

function Count({ n, label }: { n: number; label: string }) {
  if (n <= 0) return null;
  return <b className="num" title={label}>{n}<span className="sr-only"> ({label.toLowerCase()})</span></b>;
}

/** Four analytical views as tabs with counts; each renders its own empty state when the engine returned no data. */
export function VisualsBlock({ incident, tab, onTabChange }: Props) {
  const failed = incident.rules.filter((r) => r.status === "fail").length;
  return (
    <section className="csec" id="wizualizacje" aria-labelledby="wizualizacje-h">
      <h2 className="section-title" id="wizualizacje-h">Analiza</h2>
      <Tabs.Root value={tab} onValueChange={(v) => onTabChange(v as VisualTab)} className="vtabs">
        <Tabs.List className="ltabs" aria-label="Widoki analityczne">
          <Tabs.Trigger className="ltab" value="zgodnosc">Macierz kryteriów<Count n={failed} label="Naruszone kryteria" /></Tabs.Trigger>
          <Tabs.Trigger className="ltab" value="powiazania">Graf powiązań<Count n={incident.graph.flagged_paths.length} label="Oznaczone ścieżki" /></Tabs.Trigger>
          <Tabs.Trigger className="ltab" value="opinie">Opinie i konta<Count n={incident.forensics?.anomalies.length ?? 0} label="Anomalie" /></Tabs.Trigger>
          <Tabs.Trigger className="ltab" value="finanse">Finanse i KRS<Count n={incident.financials?.flags.length ?? 0} label="Sygnały ostrzegawcze" /></Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content className="vpanel" value="zgodnosc"><ComplianceMatrix rules={incident.rules} /></Tabs.Content>
        <Tabs.Content className="vpanel" value="powiazania"><RelationshipGraph graph={incident.graph} /></Tabs.Content>
        <Tabs.Content className="vpanel" value="opinie"><ForensicsPanel forensics={incident.forensics} /></Tabs.Content>
        <Tabs.Content className="vpanel" value="finanse"><FinancialsPanel financials={incident.financials} /></Tabs.Content>
      </Tabs.Root>
    </section>
  );
}
