import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { AuditEntry } from "../../src/types/api";
import type { Incident } from "../../src/types/incident";
import { analystUser, calibrationSet, orangeCase, redCase, supervisorUser } from "../fixtures/data.mjs";
import { mockApi, renderApp } from "../helpers";

const redUrl = `/sprawy/${redCase.id}`;

async function caseReady(title: string) {
  expect(await screen.findByRole("heading", { level: 1, name: title })).toBeInTheDocument();
  return within(screen.getByTestId("workflow"));
}

/** Serves `incident` for its id (detail and workflow calls echo it back with the change). */
function withCase(incident: Incident) {
  return (call: { path: string; method: string }) => (call.method === "GET" && call.path === `/api/incidents/${incident.id}` ? { json: incident } : undefined);
}

describe("case workflow", () => {
  it("analyst on a new case: take it, start the review; no supervisor action", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi();
    renderApp({ route: redUrl });
    const wf = await caseReady(redCase.title);
    expect(wf.getByTestId("assignee")).toHaveTextContent("nikt, sprawa nieprzypisana");
    expect(wf.getByRole("button", { name: "Przejmij sprawę" })).toBeInTheDocument();
    expect(wf.queryByRole("button", { name: "Zatwierdź eskalację" })).not.toBeInTheDocument();

    await user.click(wf.getByRole("button", { name: "Przejmij sprawę" }));
    await waitFor(() => expect(wf.getByTestId("assignee")).toHaveTextContent(`${analystUser.email} (Ty)`));
    expect(calls.find((c) => c.path === `/api/incidents/${redCase.id}/assign`)?.method).toBe("POST");
    expect(wf.queryByRole("button", { name: "Przejmij sprawę" })).not.toBeInTheDocument();

    await user.click(wf.getByRole("button", { name: "Rozpocznij weryfikację" }));
    await waitFor(() => expect(calls.find((c) => c.path.endsWith("/transition"))?.body).toEqual({ to: "in_review" }));
    expect(await wf.findByRole("button", { name: "Wnioskuj o eskalację" })).toBeInTheDocument();
    expect(wf.getByRole("button", { name: "Zamknij: naruszenie potwierdzone" })).toBeInTheDocument();
    expect(wf.getByRole("button", { name: "Zamknij: fałszywy alarm" })).toBeInTheDocument();
    // the history is refetched after every decision
    await waitFor(() => expect(calls.filter((c) => c.path.endsWith("/history")).length).toBeGreaterThanOrEqual(3));
  });

  it("requesting an escalation proposes the module's path (Module 3: warning list)", async () => {
    const user = userEvent.setup();
    const inReview = { ...structuredClone(redCase), status: "in_review" as const };
    const { calls } = mockApi(withCase(inReview));
    renderApp({ route: redUrl });
    const wf = await caseReady(redCase.title);
    await user.click(wf.getByRole("button", { name: "Wnioskuj o eskalację" }));
    const dialog = within(await screen.findByTestId("transition-dialog"));
    expect(dialog.getByLabelText("Ścieżka eskalacji")).toHaveValue("LEGAL_WARNING_LIST");
    await user.type(dialog.getByLabelText(/Uzasadnienie/), "Rekomendacje bez licencji");
    await user.click(dialog.getByRole("button", { name: "Wyślij wniosek" }));
    await waitFor(() => expect(calls.find((c) => c.path.endsWith("/transition"))?.body).toEqual({
      to: "escalation_requested", reason: "Rekomendacje bez licencji", escalation_path: "LEGAL_WARNING_LIST",
    }));
    await waitFor(() => expect(screen.queryByTestId("transition-dialog")).not.toBeInTheDocument());
  });

  it("a pending escalation: the analyst waits or withdraws, the supervisor approves or rejects", async () => {
    const requested = { ...structuredClone(orangeCase), status: "escalation_requested" as const, workflow: { ...orangeCase.workflow, escalation_path: "THIRD_PARTY_AUDIT" as const } };
    mockApi(withCase(requested));
    const analystView = renderApp({ route: `/sprawy/${orangeCase.id}` });
    let wf = await caseReady(orangeCase.title);
    expect(wf.getByText("Wniosek czeka na decyzję kierownika.")).toBeInTheDocument();
    expect(wf.getByRole("button", { name: "Wycofaj wniosek" })).toBeInTheDocument();
    expect(wf.queryByRole("button", { name: "Zatwierdź eskalację" })).not.toBeInTheDocument();
    analystView.unmount();

    const user = userEvent.setup();
    const { calls } = mockApi(withCase(requested), { user: supervisorUser });
    renderApp({ route: `/sprawy/${orangeCase.id}` });
    wf = await caseReady(orangeCase.title);
    expect(wf.getByRole("button", { name: "Odrzuć eskalację" })).toBeInTheDocument();
    await user.click(wf.getByRole("button", { name: "Zatwierdź eskalację" }));
    const dialog = within(await screen.findByTestId("transition-dialog"));
    expect(dialog.getByLabelText("Ścieżka eskalacji")).toHaveValue("THIRD_PARTY_AUDIT");
    await user.click(dialog.getByRole("button", { name: "Zatwierdź eskalację" }));
    await waitFor(() => expect(calls.find((c) => c.path.endsWith("/transition"))?.body).toEqual({ to: "escalated", escalation_path: "THIRD_PARTY_AUDIT" }));
  });

  it("closing requires a reason; the request is only sent once one is given", async () => {
    const user = userEvent.setup();
    const escalated = { ...structuredClone(redCase), status: "escalated" as const };
    const { calls } = mockApi(withCase(escalated), { user: supervisorUser });
    renderApp({ route: redUrl });
    const wf = await caseReady(redCase.title);
    await user.click(wf.getByRole("button", { name: "Zamknij: naruszenie potwierdzone" }));
    const dialog = within(await screen.findByTestId("transition-dialog"));
    expect(dialog.getByLabelText("Działanie końcowe")).toHaveValue("warning_list_request"); // Module 3 default
    await user.click(dialog.getByRole("button", { name: "Zamknij sprawę" }));
    expect(dialog.getByRole("alert")).toHaveTextContent("Uzasadnienie jest wymagane");
    expect(calls.some((c) => c.path.endsWith("/transition"))).toBe(false);

    await user.selectOptions(dialog.getByLabelText("Działanie końcowe"), "enhanced_monitoring");
    await user.type(dialog.getByLabelText(/Uzasadnienie/), "Naruszenie art. 76");
    await user.click(dialog.getByRole("button", { name: "Zamknij sprawę" }));
    await waitFor(() => expect(calls.find((c) => c.path.endsWith("/transition"))?.body).toEqual({
      to: "resolved", reason: "Naruszenie art. 76", resolution_action: "enhanced_monitoring",
    }));
    expect(await wf.findByText("Wzmożony monitoring (co 6 godzin)")).toBeInTheDocument();
    expect(wf.queryByRole("button", { name: /Zamknij/ })).not.toBeInTheDocument();
  });

  it("shows the server's refusal in the dialog and keeps it open", async () => {
    const user = userEvent.setup();
    const inReview = { ...structuredClone(redCase), status: "in_review" as const };
    mockApi((call) => (call.path.endsWith("/transition") ? { status: 409, json: { detail: "transition not allowed" } } : withCase(inReview)(call)));
    renderApp({ route: redUrl });
    const wf = await caseReady(redCase.title);
    await user.click(wf.getByRole("button", { name: "Zamknij: fałszywy alarm" }));
    const dialog = within(await screen.findByTestId("transition-dialog"));
    await user.type(dialog.getByLabelText(/Uzasadnienie/), "Materiał edukacyjny");
    await user.click(dialog.getByRole("button", { name: "Zamknij sprawę" }));
    expect(await dialog.findByRole("alert")).toHaveTextContent("Tej zmiany nie można wykonać na obecnym etapie sprawy");
  });

  it("labels the alert, lists the decision history and offers the warning-list draft for Module 3", async () => {
    const user = userEvent.setup();
    const history: AuditEntry[] = [
      { id: 1, at: "2026-11-21T09:00:00Z", actor_email: analystUser.email, actor_role: "ANALYST", action: "assign", incident_id: redCase.id, previous: { assigned_to: null }, new: { assigned_to: analystUser.email }, reason: null },
      { id: 2, at: "2026-11-21T09:05:00Z", actor_email: analystUser.email, actor_role: "ANALYST", action: "export", incident_id: redCase.id, previous: null, new: { format: "pdf" }, reason: null },
      { id: 3, at: "2026-11-21T09:10:00Z", actor_email: analystUser.email, actor_role: "ANALYST", action: "transition", incident_id: redCase.id, previous: { status: "new" }, new: { status: "in_review" }, reason: "Pilne" },
    ];
    const { calls } = mockApi((call) => (call.path.endsWith("/history") ? { json: { items: history } } : undefined));
    renderApp({ route: redUrl });
    const wf = await caseReady(redCase.title);
    const list = within(await screen.findByTestId("decision-history"));
    expect(list.getAllByRole("listitem")).toHaveLength(2); // exports are in the audit log, not in the decisions
    expect(list.getByText("Uzasadnienie: Pilne")).toBeInTheDocument();
    expect(list.getByText(/Etap: Nowe →/)).toHaveTextContent("Etap: Nowe → W weryfikacji");

    expect(wf.getByRole("link", { name: /Wniosek o wpis na listę ostrzeżeń/ })).toHaveAttribute("href", `/api/incidents/${redCase.id}/warning-list-request.pdf`);
    await user.selectOptions(wf.getByLabelText("Ocena trafności alarmu"), "true_positive");
    await waitFor(() => expect(calls.find((c) => c.path.endsWith("/label"))?.body).toEqual({ label: "true_positive" }));
    await waitFor(() => expect(wf.getByLabelText("Ocena trafności alarmu")).toHaveValue("true_positive"));
  });

  it("no warning-list draft outside Module 3", async () => {
    mockApi();
    renderApp({ route: `/sprawy/${orangeCase.id}` });
    const wf = await caseReady(orangeCase.title);
    expect(wf.queryByRole("link", { name: /Wniosek o wpis/ })).not.toBeInTheDocument();
  });
});

describe("global thresholds", () => {
  it("an analyst previews locally and sees who set the global values; no save button", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi((call) => (call.path === "/api/settings/thresholds" ? { json: { flag: 30, critical: 80, updated_by: supervisorUser.email, updated_at: "2026-11-20T08:00:00Z" } } : undefined));
    renderApp({ route: "/kalibracja" });
    const box = await screen.findByTestId("global-thresholds");
    await waitFor(() => expect(screen.getByLabelText("Flagowanie od")).toHaveValue(30));
    expect(box).toHaveTextContent(`Ustawił ${supervisorUser.email}`);
    expect(within(box).getByText("Progi globalne zmienia kierownik.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Zapisz jako progi globalne" })).not.toBeInTheDocument();
    const handle = screen.getByRole("slider", { name: "Próg flagowania" });
    handle.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByLabelText("Flagowanie od")).toHaveValue(31);
    expect(box).toHaveTextContent("Podgląd lokalny: 31 / 80");
    expect(calls.some((c) => c.method === "PUT")).toBe(false);
  });

  it("a supervisor saves the preview as the global thresholds", async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(undefined, { user: supervisorUser });
    renderApp({ route: "/kalibracja" });
    const save = await screen.findByRole("button", { name: "Zapisz jako progi globalne" });
    expect(save).toBeDisabled(); // nothing changed yet
    const handle = screen.getByRole("slider", { name: "Próg flagowania" });
    handle.focus();
    await user.keyboard("{PageUp}"); // 20 → 30
    await user.click(save);
    await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ flag: 30, critical: 70 }));
    expect(await screen.findByText(/Ustawił kierownik@uknf.local/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Zapisz jako progi globalne" })).toBeDisabled();
    expect(window.localStorage.getItem("investwatch.thresholds.v2")).toBeNull();
  });

  it("marks analyst-labelled cases in the calibration set", async () => {
    const items = calibrationSet.items.map((it, i) => (i < 2 ? { ...it, label_source: "analyst" as const } : it));
    mockApi((call) => (call.path === "/api/calibration" ? { json: { items } } : undefined));
    renderApp({ route: "/kalibracja" });
    const list = within(await screen.findByTestId("analyst-labelled"));
    expect(list.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText(/w tym 2 oznaczonych przez analityków/)).toBeInTheDocument();
  });
});
