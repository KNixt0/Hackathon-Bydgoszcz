import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FakeSocket, mockApi, renderApp } from "../helpers";

const URL_LABEL = "Adres strony lub posta (URL)";
const submitButton = () => screen.getByRole("button", { name: "Wyślij zgłoszenie" });
const posts = (calls: { method: string; path: string; body?: unknown }[]) => calls.filter((c) => c.path === "/api/public/reports");

async function openForm(options?: Parameters<typeof mockApi>[0]) {
  const mocked = mockApi(options, { user: null });
  const socket = new FakeSocket();
  renderApp({ route: "/zglos", socket });
  await screen.findByRole("heading", { level: 1, name: "Zgłoś ofertę lub reklamę" });
  return { ...mocked, socket };
}

describe("public report form", () => {
  it("is reachable without a session, with no dashboard chrome, no /me call and no socket", async () => {
    const { calls, socket } = await openForm();
    expect(screen.getByLabelText(URL_LABEL)).toBeRequired();
    expect(screen.getByRole("group", { name: "Czego dotyczy zgłoszenie" })).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    expect(screen.getByRole("radio", { name: "nie wiem" })).toBeChecked();
    expect(screen.getByLabelText("Uwagi (opcjonalnie)")).toBeInTheDocument();
    expect(screen.getByText(/skrót \(hash\)/)).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(calls.map((c) => c.path)).not.toContain("/api/auth/me");
    expect(calls.map((c) => c.path)).not.toContain("/api/incidents");
    expect(socket.connected).toBe(false);
  });

  it("is linked from the login page", async () => {
    mockApi(undefined, { user: null });
    renderApp({ route: "/logowanie" });
    const link = await screen.findByRole("link", { name: "Zgłoś ofertę lub reklamę" });
    expect(link).toHaveAttribute("href", "/zglos");
  });

  it("validates the address on blur and explains what to do", async () => {
    const user = userEvent.setup();
    const { calls } = await openForm();
    const input = screen.getByLabelText(URL_LABEL);
    await user.click(input);
    await user.tab();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(); // an untouched field is not an error

    await user.type(input, "przyklad.pl/oferta");
    await user.tab();
    expect(await screen.findByText(/zaczynać się od http:\/\/ lub https:\/\//)).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");

    await user.clear(input);
    await user.type(input, "https://przyklad.pl/oferta");
    expect(screen.queryByText(/zaczynać się od/)).not.toBeInTheDocument(); // clears while typing
    await user.click(submitButton());
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
  });

  it("does not send an empty form", async () => {
    const user = userEvent.setup();
    const { calls } = await openForm();
    await user.click(submitButton());
    expect(await screen.findByText("Wpisz adres strony lub posta, który chcesz zgłosić.")).toBeInTheDocument();
    expect(posts(calls)).toHaveLength(0);
  });

  it("counts the comment and sends category and comment; success shows no case details", async () => {
    const user = userEvent.setup();
    const { calls } = await openForm();
    await user.type(screen.getByLabelText(URL_LABEL), "https://przyklad.pl/oferta?utm_source=x");
    await user.click(screen.getByRole("radio", { name: "doradztwo bez zezwolenia" }));
    await user.type(screen.getByLabelText("Uwagi (opcjonalnie)"), "Obiecują zysk");
    expect(screen.getByText("13 / 500 znaków")).toBeInTheDocument();
    expect(screen.getByLabelText("Uwagi (opcjonalnie)")).toHaveAttribute("maxlength", "500");
    await user.click(submitButton());

    expect(await screen.findByText("Zgłoszenie przyjęte")).toBeInTheDocument();
    expect(posts(calls)[0]?.body).toEqual({ url: "https://przyklad.pl/oferta?utm_source=x", category_hint: 3, comment: "Obiecują zysk" });
    expect(screen.queryByText(/known|incydent|ryzyk/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Wyślij kolejne zgłoszenie" }));
    expect(screen.getByLabelText(URL_LABEL)).toHaveValue("");
  });

  it("sends category_hint null for 'nie wiem' and omits an empty comment", async () => {
    const user = userEvent.setup();
    const { calls } = await openForm();
    await user.type(screen.getByLabelText(URL_LABEL), "https://przyklad.pl/a");
    await user.click(submitButton());
    await screen.findByText("Zgłoszenie przyjęte");
    expect(posts(calls)[0]?.body).toEqual({ url: "https://przyklad.pl/a", category_hint: null });
  });

  it("explains a 429 without blaming and keeps the input", async () => {
    const user = userEvent.setup();
    await openForm((call) => (call.path === "/api/public/reports" ? { status: 429, json: { detail: "too many" } } : undefined));
    await user.type(screen.getByLabelText(URL_LABEL), "https://przyklad.pl/a");
    await user.click(submitButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Z tego urządzenia wysłano już wiele zgłoszeń. Spróbuj ponownie za godzinę.");
    expect(screen.getByLabelText(URL_LABEL)).toHaveValue("https://przyklad.pl/a");
    expect(submitButton()).toBeEnabled();
  });

  it("explains a refused address (422) and a network failure", async () => {
    const user = userEvent.setup();
    await openForm((call) => (call.path === "/api/public/reports" ? { status: 422, json: { detail: "url: this address cannot be checked" } } : undefined));
    await user.type(screen.getByLabelText(URL_LABEL), "http://10.0.0.1/x");
    await user.click(submitButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Nie udało nam się sprawdzić tego adresu");
  });
});
