import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { Incident, ObservationVersion } from "../../src/types/incident";
import { redCase } from "../fixtures/data.mjs";
import { mockApi, renderApp } from "../helpers";

const url = `/sprawy/${redCase.id}`;

function caseWith(extra: Partial<Incident>, versions: ObservationVersion[] = []) {
  const incident = { ...structuredClone(redCase), ...extra } as Incident;
  return (call: { path: string; method: string }) => {
    if (call.path === `/api/incidents/${redCase.id}`) return { json: incident };
    if (call.path.endsWith("/versions")) return { json: { items: versions } };
    return undefined;
  };
}

const evidenceVersion: ObservationVersion = {
  id: 1, content_hash: "a".repeat(64), risk_score: 89.2, changed: false, created_at: "2026-11-14T21:01:00Z",
  outcome: "content", http_status: 200, published_at: "2026-11-10", is_evidence: true, has_snapshot: true,
};
const removedVersion: ObservationVersion = {
  id: 2, content_hash: "a".repeat(64), risk_score: 89.2, changed: true, created_at: "2026-11-21T09:00:00Z",
  outcome: "removed", http_status: 404, published_at: null, is_evidence: false, has_snapshot: false,
};

describe("material and follow-up (contract v4)", () => {
  it("keeps publication, detection and the latest check apart and shows the follow-up outcome", async () => {
    mockApi(caseWith({
      status: "awaiting_correction",
      observation: { published_at: "2026-11-10", detected_at: "2026-11-14T21:01:00Z", evidence_version_id: 1, content_state: "removed", last_checked_at: "2026-11-21T09:00:00Z" },
      follow_up: { intervention_at: "2026-11-15T10:00:00Z", note: "Pismo do podmiotu", due: "2026-11-29T10:00:00Z", outcome: "removed" },
    }, [removedVersion, evidenceVersion]));
    renderApp({ route: url });
    const panel = within(await screen.findByTestId("observation"));
    expect(panel.getByText("Opublikowano")).toBeInTheDocument();
    expect(panel.getByText("10.11.2026")).toBeInTheDocument();
    expect(panel.getByText("Pierwsze wykrycie")).toBeInTheDocument();
    expect(screen.getByTestId("content-state")).toHaveTextContent("Usunięta");
    expect(screen.getByTestId("follow-up-outcome")).toHaveTextContent("Treść usunięta");
    const rows = within(await screen.findByTestId("observations")).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Treść usunięta (HTTP 404)");
    expect(rows[2]).toHaveTextContent("Wykrycie: materiał dowodowy sprawy");
  });

  it("asks the backend to check the source again", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(caseWith({}, [evidenceVersion]));
    renderApp({ route: url });
    await screen.findByTestId("observation");
    await user.click(screen.getByRole("button", { name: "Sprawdź źródło teraz" }));
    await waitFor(() => expect(calls.some((c) => c.path === `/api/incidents/${redCase.id}/rescan` && c.method === "POST")).toBe(true));
    expect(await screen.findByText(/Sprawdzenie zlecone/)).toBeInTheDocument();
  });

  it("says when a material is outside UKNF's remit", async () => {
    mockApi(caseWith({
      scope: { in_scope: false, category: "consumer_credit", basis: "out_of_scope", reason: "Kredyt lub pożyczka konsumencka, nie instrument finansowy.", authority_hint: "Ochrona konsumentów (UOKiK)." },
    }));
    renderApp({ route: url });
    const note = await screen.findByTestId("out-of-scope");
    expect(note).toHaveTextContent("Poza właściwością UKNF");
    expect(note).toHaveTextContent("Kredyt konsumencki");
    expect(note).toHaveTextContent("Wskazówka: Ochrona konsumentów (UOKiK).");
  });
});
