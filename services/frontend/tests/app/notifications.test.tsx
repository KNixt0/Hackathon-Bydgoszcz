import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Hint } from "../../src/components/ui/Hint";
import { mockApi, renderApp } from "../helpers";

const NOTE = {
  id: 7,
  created_at: "2026-11-22T08:00:00Z",
  read_at: null,
  message: "Kierownik zmienił(a) kalibrację: próg oznaczenia 20 → 25, próg krytyczny 70 → 75.",
  details: {},
};

describe("calibration notifications (ported from #33)", () => {
  it("shows the unread count and marks a notification as read", async () => {
    const { calls } = mockApi((call) => {
      if (call.path === "/api/notifications") return { json: { items: [NOTE] } };
      if (call.path === "/api/notifications/7/read") return { json: { id: 7, read_at: "2026-11-22T08:05:00Z" } };
      return undefined;
    });
    renderApp();
    const trigger = await screen.findByRole("button", { name: "Powiadomienia, nieprzeczytane: 1" });
    const user = userEvent.setup();
    await user.click(trigger);
    expect(await screen.findByText(NOTE.message)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Oznacz jako przeczytane" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === "/api/notifications/7/read")).toBe(true));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Oznacz jako przeczytane" })).not.toBeInTheDocument());
    await user.keyboard("{Escape}"); // the open menu hides the rest of the page from assistive tech
    expect(await screen.findByRole("button", { name: "Powiadomienia, nieprzeczytane: 0" })).toBeInTheDocument();
  });

  it("says so when there are none", async () => {
    mockApi();
    renderApp();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Powiadomienia, nieprzeczytane: 0" }));
    expect(await screen.findByText("Brak powiadomień.")).toBeInTheDocument();
  });

  it("offers a retry when the list cannot be loaded", async () => {
    mockApi((call) => (call.path === "/api/notifications" ? { status: 503, json: { detail: "niedostępne" } } : undefined));
    renderApp();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Powiadomienia/ }));
    expect(await screen.findByText("Nie udało się odświeżyć powiadomień.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Spróbuj ponownie" })).toBeInTheDocument();
  });
});

describe("criterion tooltip", () => {
  it("hides on Escape and comes back on the next focus (WCAG 1.4.13)", () => {
    const { container } = render(<Hint text="Kryterium 14: ostrzeżenie przy wynikach historycznych">14</Hint>);
    const trigger = screen.getByText("14");
    expect(trigger).toHaveAccessibleDescription("Kryterium 14: ostrzeżenie przy wynikach historycznych");
    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(container.querySelector(".hint")).toHaveClass("hint--dismissed");
    fireEvent.blur(trigger);
    expect(container.querySelector(".hint")).not.toHaveClass("hint--dismissed");
  });
});
