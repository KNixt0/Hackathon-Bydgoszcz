import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { bestF1Threshold, confusionAt, misclassifiedAt } from "../../src/domain/calibration";
import { countLevels } from "../../src/domain/levels";
import { calibrationSet, incidentSummaries } from "../fixtures/data.mjs";
import { mockApi, renderApp } from "../helpers";

const text = (id: string) => screen.getByTestId(id).textContent;
const scores = incidentSummaries.map((i) => i.risk_score);

async function ready() {
  await waitFor(() => expect(screen.getByTestId("cm-tp")).toBeInTheDocument());
  await waitFor(() => expect(text("queue-red")).not.toBe("0"));
}

const DEFAULTS = { red: 70, orange: 20 };
const V2_KEY = "investwatch.thresholds.v2";

describe("calibration panel", () => {
  it("computes the confusion matrix and metrics at the default flag threshold (risk_score >= 20)", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const c = confusionAt(calibrationSet.items, 20);
    expect(text("cm-tp")).toBe(String(c.tp));
    expect(text("cm-fp")).toBe(String(c.fp));
    expect(text("cm-fn")).toBe(String(c.fn));
    expect(text("cm-tn")).toBe(String(c.tn));
    expect(text("metric-precision")).toBe(`${Math.round((c.tp / (c.tp + c.fp)) * 100)}%`);
    expect(text("metric-recall")).toBe(`${Math.round((c.tp / (c.tp + c.fn)) * 100)}%`);
    const levels = countLevels(scores, DEFAULTS);
    expect(text("queue-red")).toBe(String(levels.red));
    expect(text("queue-flagged")).toBe(String(levels.red + levels.orange));
    expect(screen.getByLabelText("Flagowanie od")).toHaveValue(20);
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(70);
  });

  it("moving the primary (flag) slider with the keyboard changes matrix, flagged count and error lists", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const before = { flagged: text("queue-flagged"), fn: text("cm-fn"), fp: text("cm-fp"), red: text("queue-red") };

    const handle = screen.getByRole("slider", { name: "Próg flagowania" });
    handle.focus();
    await user.keyboard("{PageUp}{PageUp}"); // 20 → 40
    expect(handle).toHaveAttribute("aria-valuenow", "40");

    const c = confusionAt(calibrationSet.items, 40);
    expect(text("cm-tp")).toBe(String(c.tp));
    expect(text("cm-fn")).toBe(String(c.fn));
    expect(text("cm-fp")).toBe(String(c.fp));
    const levels = countLevels(scores, { red: 70, orange: 40 });
    expect(text("queue-flagged")).toBe(String(levels.red + levels.orange));
    expect(text("queue-flagged")).not.toBe(before.flagged);
    expect(text("queue-red")).toBe(before.red); // the critical threshold did not move
    expect(Number(text("cm-fn"))).toBeGreaterThan(Number(before.fn));
    expect(Number(text("cm-fp"))).toBeLessThan(Number(before.fp));

    const wrong = misclassifiedAt(calibrationSet.items, 40);
    const fp = within(screen.getByTestId("false-positives"));
    expect(fp.queryAllByRole("listitem")).toHaveLength(wrong.falsePositives.length);
    expect(within(screen.getByTestId("false-negatives")).getAllByRole("listitem")).toHaveLength(wrong.falseNegatives.length);
    expect(wrong.falseNegatives.length).toBeGreaterThan(0);
  });

  it("the critical threshold does not change the matrix, only the red/orange split", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const before = { tp: text("cm-tp"), fp: text("cm-fp"), fn: text("cm-fn"), tn: text("cm-tn"), flagged: text("queue-flagged") };
    fireEvent.change(screen.getByLabelText("Krytyczne od"), { target: { value: "90" } });
    expect([text("cm-tp"), text("cm-fp"), text("cm-fn"), text("cm-tn"), text("queue-flagged")]).toEqual(Object.values(before));
    expect(text("queue-red")).toBe(String(countLevels(scores, { red: 90, orange: 20 }).red));
    expect(JSON.parse(window.localStorage.getItem(V2_KEY) ?? "{}")).toEqual({ red: 90, orange: 20 });
  });

  it("matrix follows the flag threshold at several values, including the boundary", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    for (const t of [0, 15, 31, 32, 50, 90]) {
      fireEvent.change(screen.getByLabelText("Flagowanie od"), { target: { value: String(t) } });
      const c = confusionAt(calibrationSet.items, t);
      expect([text("cm-tp"), text("cm-fp"), text("cm-fn"), text("cm-tn")]).toEqual([c.tp, c.fp, c.fn, c.tn].map(String));
    }
  });

  it("raising the flag threshold past the critical one pushes the critical one along; critical never drops below the flag threshold", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    fireEvent.change(screen.getByLabelText("Flagowanie od"), { target: { value: "80" } });
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(80);
    expect(text("queue-orange")).toBe("0");
    fireEvent.change(screen.getByLabelText("Krytyczne od"), { target: { value: "10" } });
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(80);
    expect(screen.getByLabelText("Flagowanie od")).toHaveValue(80);
  });

  it("the Best F1 button sets the flag threshold", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const best = bestF1Threshold(calibrationSet.items) as number;
    const button = screen.getByRole("button", { name: new RegExp(`Najlepszy F1: ${best}`) });
    if (best !== 20) await user.click(button);
    expect(screen.getByLabelText("Flagowanie od")).toHaveValue(best);
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(Math.max(70, best));
  });

  it("the explanation describes the flag threshold", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(screen.getByText(/Sprawa jest oflagowana, gdy/)).toBeInTheDocument();
  });

  it("the thresholds set here drive the queue and its flagged count", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    fireEvent.change(screen.getByLabelText("Flagowanie od"), { target: { value: "35" } });
    fireEvent.change(screen.getByLabelText("Krytyczne od"), { target: { value: "50" } });
    await user.click(screen.getByRole("link", { name: /Kolejka spraw/ }));
    await waitFor(() => expect(screen.getAllByTestId("queue-row").length).toBe(30));
    const expected = countLevels(scores, { red: 50, orange: 35 });
    expect(screen.getAllByTestId("queue-row").filter((r) => r.dataset.level === "red")).toHaveLength(expected.red);
    expect(screen.getAllByTestId("queue-row").filter((r) => r.dataset.level !== "green")).toHaveLength(expected.red + expected.orange);
    expect(within(screen.getByTestId("count-red")).getByText(String(expected.red))).toBeInTheDocument();
    expect(screen.getByTestId("nav-flagged")).toHaveTextContent(String(expected.red + expected.orange));
  });

  it("restores a stored v2 threshold on load and can reset to defaults", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(V2_KEY, JSON.stringify({ red: 55, orange: 25 }));
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(55);
    expect(screen.getByLabelText("Flagowanie od")).toHaveValue(25);
    await user.click(screen.getByRole("button", { name: /Przywróć 20 \/ 70/ }));
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(70);
    expect(screen.getByLabelText("Flagowanie od")).toHaveValue(20);
  });

  it("ignores thresholds stored under the old v1 key (old default of 35 must not stick)", async () => {
    window.localStorage.setItem("investwatch.thresholds.v1", JSON.stringify({ red: 70, orange: 35 }));
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(screen.getByLabelText("Flagowanie od")).toHaveValue(20);
    expect(window.localStorage.getItem("investwatch.thresholds.v1")).toBeNull();
  });

  it("ignores corrupted localStorage", async () => {
    window.localStorage.setItem(V2_KEY, "{not json");
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(70);
    expect(screen.getByLabelText("Flagowanie od")).toHaveValue(20);
  });

  it("explains an empty labelled set instead of showing zeros", async () => {
    mockApi((call) => (call.path === "/api/calibration" ? { json: { items: [] } } : undefined));
    renderApp({ route: "/kalibracja" });
    expect(await screen.findByText("Brak oznaczonych spraw")).toBeInTheDocument();
    expect(screen.queryByTestId("cm-tp")).not.toBeInTheDocument();
  });

  it("shows an error with retry when the labelled set cannot be loaded", async () => {
    mockApi((call) => (call.path === "/api/calibration" ? { status: 500, json: { detail: "Błąd serwera kalibracji." } } : undefined));
    renderApp({ route: "/kalibracja" });
    expect(await screen.findByText("Błąd serwera kalibracji.")).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "Próg flagowania" })).toBeInTheDocument();
  });
});
