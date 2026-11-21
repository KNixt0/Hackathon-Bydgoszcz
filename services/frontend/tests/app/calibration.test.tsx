import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { confusionAt, misclassifiedAt } from "../../src/domain/calibration";
import { countLevels } from "../../src/domain/levels";
import { calibrationSet, incidentSummaries } from "../fixtures/data.mjs";
import { mockApi, renderApp } from "../helpers";

const text = (id: string) => screen.getByTestId(id).textContent;
const scores = incidentSummaries.map((i) => i.risk_score);

async function ready() {
  await waitFor(() => expect(screen.getByTestId("cm-tp")).toBeInTheDocument());
  await waitFor(() => expect(text("queue-red")).not.toBe("0"));
}

describe("calibration panel", () => {
  it("computes the confusion matrix and metrics for the default threshold from the labelled set", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const c = confusionAt(calibrationSet.items, 70);
    expect(text("cm-tp")).toBe(String(c.tp));
    expect(text("cm-fp")).toBe(String(c.fp));
    expect(text("cm-fn")).toBe(String(c.fn));
    expect(text("cm-tn")).toBe(String(c.tn));
    expect(text("metric-precision")).toBe(`${Math.round((c.tp / (c.tp + c.fp)) * 100)}%`);
    expect(text("metric-recall")).toBe(`${Math.round((c.tp / (c.tp + c.fn)) * 100)}%`);
    expect(text("queue-red")).toBe(String(countLevels(scores, { red: 70, orange: 35 }).red));
  });

  it("moving the red handle with the keyboard changes counts, matrix and error lists immediately", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    const before = { red: text("queue-red"), fn: text("cm-fn"), fp: text("cm-fp") };

    const handle = screen.getByRole("slider", { name: "Próg krytyczny" });
    handle.focus();
    await user.keyboard("{PageDown}{PageDown}{PageDown}"); // 70 → 40
    expect(handle).toHaveAttribute("aria-valuenow", "40");

    const c = confusionAt(calibrationSet.items, 40);
    expect(text("cm-tp")).toBe(String(c.tp));
    expect(text("cm-fn")).toBe(String(c.fn));
    expect(text("cm-fp")).toBe(String(c.fp));
    expect(text("queue-red")).toBe(String(countLevels(scores, { red: 40, orange: 35 }).red));
    expect(text("queue-red")).not.toBe(before.red);
    expect(Number(text("cm-fn"))).toBeLessThan(Number(before.fn));
    expect(Number(text("cm-fp"))).toBeGreaterThan(Number(before.fp));

    const wrong = misclassifiedAt(calibrationSet.items, 40);
    const fp = within(screen.getByTestId("false-positives"));
    expect(fp.getAllByRole("listitem")).toHaveLength(wrong.falsePositives.length);
    expect(fp.getByText(wrong.falsePositives[0]?.title ?? "")).toBeInTheDocument();
    expect(within(screen.getByTestId("false-negatives")).getAllByRole("listitem")).toHaveLength(wrong.falseNegatives.length);
  });

  it("typing a threshold works too and is persisted in localStorage", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    fireEvent.change(screen.getByLabelText("Krytyczne od"), { target: { value: "90" } });
    expect(text("queue-red")).toBe(String(countLevels(scores, { red: 90, orange: 35 }).red));
    expect(JSON.parse(window.localStorage.getItem("investwatch.thresholds.v1") ?? "{}")).toEqual({ red: 90, orange: 35 });
  });

  it("the orange handle changes the verification band and pushes red when dragged past it", async () => {
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    fireEvent.change(screen.getByLabelText("Do weryfikacji od"), { target: { value: "20" } });
    expect(text("queue-orange")).toBe(String(countLevels(scores, { red: 70, orange: 20 }).orange));
    fireEvent.change(screen.getByLabelText("Do weryfikacji od"), { target: { value: "80" } });
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(80);
    expect(text("queue-orange")).toBe("0");
  });

  it("the threshold set here drives the queue", async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    fireEvent.change(screen.getByLabelText("Krytyczne od"), { target: { value: "50" } });
    await user.click(screen.getByRole("link", { name: /Kolejka spraw/ }));
    await waitFor(() => expect(screen.getAllByTestId("queue-row").length).toBe(30));
    const expected = countLevels(scores, { red: 50, orange: 35 });
    expect(screen.getAllByTestId("queue-row").filter((r) => r.dataset.level === "red")).toHaveLength(expected.red);
    expect(within(screen.getByTestId("count-red")).getByText(String(expected.red))).toBeInTheDocument();
  });

  it("restores a stored threshold on load and can reset to defaults", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem("investwatch.thresholds.v1", JSON.stringify({ red: 55, orange: 25 }));
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(55);
    await user.click(screen.getByRole("button", { name: /Przywróć 35 \/ 70/ }));
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(70);
    expect(screen.getByLabelText("Do weryfikacji od")).toHaveValue(35);
  });

  it("ignores corrupted localStorage", async () => {
    window.localStorage.setItem("investwatch.thresholds.v1", "{not json");
    mockApi();
    renderApp({ route: "/kalibracja" });
    await ready();
    expect(screen.getByLabelText("Krytyczne od")).toHaveValue(70);
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
    expect(screen.getByRole("slider", { name: "Próg krytyczny" })).toBeInTheDocument();
  });
});
