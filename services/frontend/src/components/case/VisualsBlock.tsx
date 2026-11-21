import * as Tabs from "@radix-ui/react-tabs";
import { Landmark, ListChecks, MessagesSquare, Network } from "lucide-react";
import type { Incident } from "../../types/incident";
import { ComplianceMatrix } from "./ComplianceMatrix";
import { FinancialsPanel } from "./FinancialsPanel";
import { ForensicsPanel } from "./ForensicsPanel";
import { RegistryChecks } from "./RegistryChecks";
import { RelationshipGraph } from "./RelationshipGraph";

export type VisualTab = "zgodnosc" | "powiazania" | "opinie" | "finanse";
export const VISUAL_TABS: VisualTab[] = ["zgodnosc", "powiazania", "opinie", "finanse"];

interface Props {
  incident: Incident;
  tab: VisualTab;
  onTabChange: (tab: VisualTab) => void;
}

/** Block 2: four sub-panels; each renders its own empty state when the engine returned no data. */
export function VisualsBlock({ incident, tab, onTabChange }: Props) {
  const failed = incident.rules.filter((r) => r.status === "fail").length;
  return (
    <section className="panel block" id="wizualizacje" aria-labelledby="wizualizacje-h">
      <header className="panel__head">
        <h2 className="panel__title" id="wizualizacje-h"><span className="block__n">2</span>Wykresy i wizualizacje</h2>
      </header>
      <Tabs.Root value={tab} onValueChange={(v) => onTabChange(v as VisualTab)}>
        <Tabs.List className="tabs__list" aria-label="Widoki analityczne">
          <Tabs.Trigger className="tabs__trigger" value="zgodnosc">
            <ListChecks aria-hidden="true" />Macierz zgodności
            {failed > 0 && <span className="tabs__count tabs__count--red" title="Naruszone kryteria">{failed}</span>}
          </Tabs.Trigger>
          <Tabs.Trigger className="tabs__trigger" value="powiazania">
            <Network aria-hidden="true" />Graf powiązań
            {incident.graph.flagged_paths.length > 0 && <span className="tabs__count tabs__count--red" title="Oznaczone ścieżki">{incident.graph.flagged_paths.length}</span>}
          </Tabs.Trigger>
          <Tabs.Trigger className="tabs__trigger" value="opinie">
            <MessagesSquare aria-hidden="true" />Opinie i konta
            {incident.forensics && incident.forensics.anomalies.length > 0 && <span className="tabs__count tabs__count--red" title="Anomalie">{incident.forensics.anomalies.length}</span>}
          </Tabs.Trigger>
          <Tabs.Trigger className="tabs__trigger" value="finanse">
            <Landmark aria-hidden="true" />Finanse i KRS
            {incident.financials && incident.financials.flags.length > 0 && <span className="tabs__count" title="Sygnały ostrzegawcze">{incident.financials.flags.length}</span>}
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content className="tabs__panel" value="zgodnosc">
          <ComplianceMatrix rules={incident.rules} />
          <h3 className="section-title" style={{ borderTop: "1px solid var(--line)" }}>Rejestry i licencje</h3>
          <RegistryChecks checks={incident.registry_checks} />
        </Tabs.Content>
        <Tabs.Content className="tabs__panel" value="powiazania"><RelationshipGraph graph={incident.graph} /></Tabs.Content>
        <Tabs.Content className="tabs__panel" value="opinie"><ForensicsPanel forensics={incident.forensics} /></Tabs.Content>
        <Tabs.Content className="tabs__panel" value="finanse"><FinancialsPanel financials={incident.financials} /></Tabs.Content>
      </Tabs.Root>
    </section>
  );
}
