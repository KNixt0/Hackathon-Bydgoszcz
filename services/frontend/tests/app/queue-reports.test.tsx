import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { deriveTier } from "../../src/domain/priority";
import { DEFAULT_THRESHOLDS } from "../../src/domain/levels";
import { incidentSummaries, orangeCase, redSummary } from "../fixtures/data.mjs";
import { FakeSocket, mockApi, renderApp } from "../helpers";

const rows = () => screen.getAllByTestId("queue-row");
async function ready() {
  await waitFor(() => expect(screen.getAllByTestId("queue-row").length).toBeGreaterThan(0));
}
const rowOf = (title: string) => {
  const row = rows().find((r) => r.textContent?.includes(title));
  if (!row) throw new Error(`no row ${title}`);
  return within(row);
};
const anomaly = incidentSummaries.find((i) => deriveTier(i.risk_score, i.user_reports_count, DEFAULT_THRESHOLDS) === "crowd_anomaly");
const withNoReports = incidentSummaries.find((i) => i.user_reports_count === 0 && i.risk_score < 20);

describe("queue with public reports", () => {
  it("shows the report count and the tier per row, nothing for quiet low-risk cases", async () => {
    mockApi();
    renderApp();
    await ready();
    if (!anomaly || !withNoReports) throw new Error("fixtures missing");
    const crowd = rowOf(anomaly.title);
    expect(crowd.getByTestId("report-count")).toHaveTextContent(/^\d+ zgłoszeń$/);
    expect(crowd.getByText("Rozbieżność: zgłaszane przez użytkowników")).toBeInTheDocument();
    const viral = incidentSummaries.find((i) => i.title.startsWith("„Podwój kapitał"));
    expect(rowOf(viral?.title ?? "").getByText("Krytyczne i zgłaszane")).toBeInTheDocument();
    expect(rowOf(viral?.title ?? "").getByTestId("report-count")).toHaveTextContent("7 zgłoszeń");
    const quiet = rowOf(withNoReports.title);
    expect(quiet.queryByTestId("report-count")).not.toBeInTheDocument();
    expect(quiet.queryByText(/Rozbieżność|Krytyczne i zgłaszane|Wysokie ryzyko/)).not.toBeInTheDocument();
    expect(rowOf(orangeCase.title).getByTestId("report-count")).toHaveTextContent("3 zgłoszenia");
  });

  it("finds the crowd anomalies with the tier filter and reports it in the count", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp();
    await ready();
    await user.selectOptions(screen.getByLabelText("Priorytet zgłoszeń"), "crowd_anomaly");
    const expected = incidentSummaries.filter((i) => deriveTier(i.risk_score, i.user_reports_count, DEFAULT_THRESHOLDS) === "crowd_anomaly");
    expect(rows()).toHaveLength(expected.length);
    expect(rows().every((r) => within(r).queryByText("Rozbieżność: zgłaszane przez użytkowników"))).toBe(true);
  });

  it("sorts by priority and goes back to risk order", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp();
    await ready();
    const titles = () => rows().map((r) => r.querySelector(".queue__title")?.textContent);
    const byRisk = titles();
    await user.selectOptions(screen.getByLabelText("Sortuj według"), "priority");
    const byPriority = titles();
    expect(byPriority).not.toEqual(byRisk);
    const expectedFirst = [...incidentSummaries].sort((a, b) => b.priority_score - a.priority_score)[0];
    expect(byPriority[0]).toBe(expectedFirst?.title);
    await user.selectOptions(screen.getByLabelText("Sortuj według"), "risk");
    expect(titles()).toEqual(byRisk);
  });

  it("shows a persistent alert:viral banner with its own wording, pins the case and can be dismissed", async () => {
    const user = userEvent.setup();
    mockApi();
    const socket = new FakeSocket();
    renderApp({ socket });
    await ready();
    const viral = { ...redSummary, risk_score: 71, user_reports_count: 5, priority_score: 90 };
    act(() => {
      socket.emit("incident:new", viral);
      socket.emit("alert:viral", viral);
    });
    const banner = screen.getByRole("region", { name: "Alerty zgłoszeń użytkowników" });
    expect(banner).toHaveTextContent("Krytyczna sprawa zgłaszana przez wielu użytkowników");
    expect(banner).toHaveTextContent("5 zgłoszeń");
    expect(within(banner).getByRole("link", { name: "Otwórz sprawę" })).toHaveAttribute("href", `/sprawy/${redSummary.id}`);
    expect(screen.queryByRole("region", { name: "Alerty wysokiego ryzyka" })).not.toBeInTheDocument();
    expect(rows()[0]).toHaveTextContent(redSummary.title);
    await user.click(within(banner).getByRole("button", { name: /Zamknij alert zgłoszeń/ }));
    expect(screen.queryByRole("region", { name: "Alerty zgłoszeń użytkowników" })).not.toBeInTheDocument();
  });

  it("updates a row's count from incident:updated", async () => {
    mockApi();
    const socket = new FakeSocket();
    renderApp({ socket });
    await ready();
    const target = incidentSummaries.find((i) => i.user_reports_count === 0 && i.risk_score >= 20);
    if (!target) throw new Error("fixture missing");
    act(() => socket.emit("incident:updated", { ...target, user_reports_count: 1 }));
    expect(rowOf(target.title).getByTestId("report-count")).toHaveTextContent("1 zgłoszenie");
    await waitFor(() => expect(screen.getAllByTestId("queue-row").length).toBeGreaterThan(0));
  });
});

describe("case page with public reports", () => {
  it("shows the count and the reports as plain text", async () => {
    mockApi();
    renderApp({ route: `/sprawy/${orangeCase.id}` });
    expect(await screen.findByTestId("case-report-count")).toHaveTextContent("3 zgłoszenia");
    const list = await screen.findByTestId("case-reports");
    expect(within(list).getAllByRole("listitem")).toHaveLength(3);
    expect(list).toHaveTextContent("Reklama influencera lub podmiotu trzeciego");
    expect(list.querySelector("b")).toBeNull(); // markup in a comment stays text
  });

  it("explains the crowd anomaly on the case page", async () => {
    if (!anomaly) throw new Error("fixture missing");
    mockApi();
    renderApp({ route: `/sprawy/${anomaly.id}` });
    expect(await screen.findByText(/możliwy fałszywie ujemny wynik modelu/)).toBeInTheDocument();
    expect(await screen.findByTestId("case-reports")).toBeInTheDocument();
  });
});
