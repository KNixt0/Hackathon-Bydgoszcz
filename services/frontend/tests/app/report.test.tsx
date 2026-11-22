import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderApp } from "../helpers";

describe("removed public reports", () => {
  it("does not offer the public form on login", async () => {
    const { calls } = mockApi(undefined, { user: null });
    renderApp({ route: "/logowanie" });
    await screen.findByRole("heading", { name: "Logowanie" });
    expect(screen.queryByRole("link", { name: /Zgłoś/ })).not.toBeInTheDocument();
    expect(calls.some((call) => call.path.startsWith("/api/public/"))).toBe(false);
  });
  it("old public-form URLs do not display a reporting form", async () => {
    mockApi();
    renderApp({ route: "/zglos" });
    await screen.findByRole("link", { name: "Kolejka spraw" });
    expect(screen.queryByRole("heading", { name: "Zgłoś ofertę lub reklamę" })).not.toBeInTheDocument();
  });
});
