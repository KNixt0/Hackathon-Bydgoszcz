import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { bestF1Threshold, confusionAt, metricsAt, misclassifiedAt } from "../../src/domain/calibration";
import { flagSentence, segText } from "../../src/domain/calibrationCopy";
import { countLevels } from "../../src/domain/levels";
import { calibrationSet, incidentSummaries } from "../fixtures/data.mjs";
import { mockApi, renderApp } from "../helpers";

const text = (id: string) => screen.getByTestId(id).textContent;
const scores = incidentSummaries.map((i) => i.risk_score);
const flagField = () => screen.getByLabelText("Próg flagowania");
const critField = () => screen.getByLabelText("Próg krytyczny");
const slider = () => screen.getByRole("slider", { name: "Próg flagowania" });

async function ready() {
  await waitFor(() => expect(screen.getByTestId("live-sentence")).toHaveTextContent("sprawdzonych spraw"));
  await waitFor(() => expect(text("queue-red")).not.toBe("0"));
}

/** Charts and tables for analysts mount only after the disclosure is opened. */
async function openDetails() {
  const user = userEvent.setup();
  await user.click(screen.getByText("Szczegóły dla analityka"));
  await waitFor(() => expect(screen.getByTestId("cm-tp")).toBeInTheDocument());
}

const DEFAULTS = { red: 70, orange: 20 };
const V2_KEY = "investwatch.thresholds.v2";

describe("calibration screen", () => {
  it("shows one sentence, the two opposing counts and the secondary figures at the default flag threshold (risk_score >= 20)", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const c = confusionAt(calibrationSet.items, 20);
    expect(text("live-sentence")).toBe(segText(flagSentence(20, c)));
    expect(text("false-alarms-count")).toBe(String(c.fp));
    expect(text("missed-count")).toBe(String(c.fn));
    expect(screen.getByTestId("false-alarms")).toHaveTextContent(`z ${c.fp + c.tn} zgodnych spraw`);
    expect(screen.getByTestId("missed")).toHaveTextContent(`z ${c.tp + c.fn} naruszeń`);
    expect(text("metric-precision")).toBe(`${Math.round((c.tp / (c.tp + c.fp)) * 100)}%`);
    expect(text("metric-recall")).toBe(`${Math.round((c.tp / (c.tp + c.fn)) * 100)}%`);
    const levels = countLevels(scores, DEFAULTS);
    expect(text("queue-red")).toBe(String(levels.red));
    expect(text("queue-flagged")).toBe(String(levels.red + levels.orange));
    expect(flagField()).toHaveValue("20");
    expect(critField()).toHaveValue(70);
    // English terms only in abbr titles on the main panel
    expect(screen.getByText("Trafność alertów").closest("abbr")).toHaveAttribute("title", "po angielsku: precision");
    expect(screen.getByText("Wykrywalność naruszeń").closest("abbr")).toHaveAttribute("title", "po angielsku: recall");
  });

  it("the details for analysts are closed by default and their tables mount on first open", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const details = screen.getByTestId("analyst-details");
    expect(details).not.toHaveAttribute("open");
    expect(screen.queryByTestId("cm-tp")).not.toBeInTheDocument();
    expect(screen.queryByTestId("score-histogram")).not.toBeInTheDocument();
    await openDetails();
    expect(details).toHaveAttribute("open");
    const c = confusionAt(calibrationSet.items, 20);
    expect([text("cm-tp"), text("cm-fp"), text("cm-fn"), text("cm-tn")]).toEqual([c.tp, c.fp, c.fn, c.tn].map(String));
    expect(text("metric-f1")).toBe(`${Math.round((metricsAt(calibrationSet.items, 20).f1 ?? 0) * 100)}%`);
    expect(screen.getByTestId("score-histogram")).toBeInTheDocument();
    expect(screen.getByTestId("pr-curve")).toBeInTheDocument();
  });

  it("moving the slider changes the sentence, both opposing counts, the queue and the error lists", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    await openDetails();
    const before = { flagged: text("queue-flagged"), fn: text("missed-count"), fp: text("false-alarms-count"), red: text("queue-red"), sentence: text("live-sentence") };

    const handle = slider();
    fireEvent.change(handle, { target: { value: "40" } });
    expect(handle).toHaveValue("40");
    expect(screen.getByText(": 40")).toBeInTheDocument(); // the value next to the label

    const c = confusionAt(calibrationSet.items, 40);
    expect(text("live-sentence")).toBe(segText(flagSentence(40, c)));
    expect(text("live-sentence")).not.toBe(before.sentence);
    expect(text("false-alarms-count")).toBe(String(c.fp));
    expect(text("missed-count")).toBe(String(c.fn));
    expect(Number(text("missed-count"))).toBeGreaterThan(Number(before.fn));
    expect(Number(text("false-alarms-count"))).toBeLessThan(Number(before.fp));
    expect(text("cm-tp")).toBe(String(c.tp));
    const levels = countLevels(scores, { red: 70, orange: 40 });
    expect(text("queue-flagged")).toBe(String(levels.red + levels.orange));
    expect(text("queue-flagged")).not.toBe(before.flagged);
    expect(text("queue-red")).toBe(before.red); // the critical threshold did not move

    const wrong = misclassifiedAt(calibrationSet.items, 40);
    const rowsIn = (id: string) => within(screen.getByTestId(id)).queryAllByRole("row").length - (within(screen.getByTestId(id)).queryAllByRole("table").length);
    expect(rowsIn("false-positives")).toBe(wrong.falsePositives.length);
    expect(rowsIn("false-negatives")).toBe(wrong.falseNegatives.length);
    expect(wrong.falseNegatives.length).toBeGreaterThan(0);
  });

  it("the control is one native slider 0–100 with the value next to its label, no step buttons or number field", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const handle = slider();
    expect(handle).toHaveAttribute("type", "range");
    expect(handle).toHaveAttribute("min", "0");
    expect(handle).toHaveAttribute("max", "100");
    expect(handle).toHaveAttribute("step", "1");
    expect(handle).toHaveAccessibleDescription(/Strzałki na klawiaturze zmieniają próg o 1/);
    expect(screen.getByText(": 20")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /próg o 1/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("spinbutton")).toHaveLength(1); // only the critical threshold field
  });

  it("the live region announces the sentence only after the value settles", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const region = screen.getByTestId("live-announcement");
    expect(region).toHaveAttribute("role", "status");
    fireEvent.change(flagField(), { target: { value: "50" } });
    expect(region.textContent).not.toContain("Przy progu 50");
    await waitFor(() => expect(region.textContent).toContain("Przy progu 50"));
  });

  it("the critical threshold does not change the errors, only the critical/to-verify split", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const before = { fp: text("false-alarms-count"), fn: text("missed-count"), sentence: text("live-sentence"), flagged: text("queue-flagged") };
    fireEvent.change(critField(), { target: { value: "90" } });
    expect([text("false-alarms-count"), text("missed-count"), text("live-sentence"), text("queue-flagged")]).toEqual(Object.values(before));
    expect(text("queue-red")).toBe(String(countLevels(scores, { red: 90, orange: 20 }).red));
    expect(JSON.parse(window.localStorage.getItem(V2_KEY) ?? "{}")).toEqual({ red: 90, orange: 20 });
  });

  it("the opposing counts follow the flag threshold at several values, including the boundary", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    for (const t of [0, 15, 31, 32, 50, 90]) {
      fireEvent.change(flagField(), { target: { value: String(t) } });
      const c = confusionAt(calibrationSet.items, t);
      expect([text("false-alarms-count"), text("missed-count")]).toEqual([c.fp, c.fn].map(String));
      expect(text("live-sentence")).toBe(segText(flagSentence(t, c)));
    }
  });

  it("raising the flag threshold past the critical one pushes the critical one along and explains the limit", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    fireEvent.change(flagField(), { target: { value: "80" } });
    expect(critField()).toHaveValue(80);
    expect(text("queue-orange")).toBe("0");
    expect(screen.getByText("Próg krytyczny nie może być niższy niż próg oznaczenia (80).")).toBeInTheDocument();
    fireEvent.change(critField(), { target: { value: "10" } });
    expect(critField()).toHaveValue(80);
    expect(flagField()).toHaveValue("80");
  });

  it("the recommended-threshold button sets the flag threshold and then says it is the recommended one", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const best = bestF1Threshold(calibrationSet.items) as number;
    const button = screen.getByRole("button", { name: `Ustaw zalecany próg: ${best}` });
    if (best !== 20) {
      const m = metricsAt(calibrationSet.items, best);
      expect(screen.getByText(new RegExp(`Próg ${best} najlepiej godzi oba cele: wykrywa ${Math.round((m.recall ?? 0) * 100)}% naruszeń`))).toBeInTheDocument();
      await user.click(button);
    }
    expect(flagField()).toHaveValue(String(best));
    expect(critField()).toHaveValue(Math.max(70, best));
    expect(button).toBeDisabled();
    expect(screen.getByText(/To jest zalecany próg/)).toBeInTheDocument();
  });

  it("the thresholds set here drive the queue tabs and rows", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    fireEvent.change(flagField(), { target: { value: "35" } });
    fireEvent.change(critField(), { target: { value: "50" } });
    await user.click(screen.getByRole("link", { name: /Kolejka spraw/ }));
    await waitFor(() => expect(screen.getAllByTestId("queue-row").length).toBe(30));
    const expected = countLevels(scores, { red: 50, orange: 35 });
    expect(screen.getAllByTestId("queue-row").filter((r) => r.dataset.level === "red")).toHaveLength(expected.red);
    expect(screen.getAllByTestId("queue-row").filter((r) => r.dataset.level !== "green")).toHaveLength(expected.red + expected.orange);
    expect(within(screen.getByTestId("count-red")).getByText(String(expected.red))).toBeInTheDocument();
    expect(screen.getByTestId("queue-thresholds")).toHaveTextContent("oznaczenie od 35, krytyczne od 50");
  });

  it("restores a stored v2 preview on load and can go back to the global thresholds", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(V2_KEY, JSON.stringify({ red: 55, orange: 25 }));
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(critField()).toHaveValue(55);
    expect(flagField()).toHaveValue("25");
    expect(screen.getByTestId("global-thresholds")).toHaveTextContent("Podgląd, niezapisane.");
    await user.click(screen.getByRole("button", { name: "Przywróć globalne (20 / 70)" }));
    expect(critField()).toHaveValue(70);
    expect(flagField()).toHaveValue("20");
    expect(screen.getByTestId("global-thresholds")).toHaveTextContent("Obowiązują progi globalne: oznaczenie od 20, krytyczne od 70.");
  });

  it("ignores thresholds stored under the old v1 key (old default of 35 must not stick)", async () => {
    window.localStorage.setItem("investwatch.thresholds.v1", JSON.stringify({ red: 70, orange: 35 }));
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(flagField()).toHaveValue("20");
    expect(window.localStorage.getItem("investwatch.thresholds.v1")).toBeNull();
  });

  it("ignores corrupted localStorage", async () => {
    window.localStorage.setItem(V2_KEY, "{not json");
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(critField()).toHaveValue(70);
    expect(flagField()).toHaveValue("20");
  });

  it("warns that a small labelled set gives unstable figures", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const n = calibrationSet.items.length;
    if (n < 30) expect(screen.getByTestId("small-set")).toHaveTextContent(`Zbiór jest mały (${n} spraw)`);
    else expect(screen.queryByTestId("small-set")).not.toBeInTheDocument();
  });

  it("explains an empty labelled set instead of showing zeros; the threshold still drives the queue", async () => {
    mockApi((call) => (call.path === "/api/calibration" ? { json: { items: [] } } : undefined));
    renderApp({ route: "/kalibracja" });
    expect(await screen.findByText("Brak ocenionych spraw")).toBeInTheDocument();
    expect(screen.queryByTestId("false-alarms")).not.toBeInTheDocument();
    expect(screen.queryByTestId("analyst-details")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("live-sentence")).toHaveTextContent("Nie wiemy, ile z nich to pomyłki"));
    expect(screen.getByRole("link", { name: "Przejdź do kolejki" })).toHaveAttribute("href", "/");
  });

  it("shows an error with retry when the labelled set cannot be loaded; the control stays usable", async () => {
    mockApi((call) => (call.path === "/api/calibration" ? { status: 500, json: { detail: "Błąd serwera kalibracji." } } : undefined));
    renderApp({ route: "/kalibracja" });
    expect(await screen.findByText("Błąd serwera kalibracji.")).toBeInTheDocument();
    expect(screen.getByText("Nie udało się wczytać zbioru oznaczonego")).toBeInTheDocument();
    expect(slider()).toBeInTheDocument();
    expect(critField()).toBeInTheDocument();
  });
});
