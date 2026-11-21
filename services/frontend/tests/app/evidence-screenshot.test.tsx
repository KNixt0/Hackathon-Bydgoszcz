import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { boxStyle, hasScreenshotBox, ScreenshotEvidence } from "../../src/components/evidence";
import type { Evidence, Incident } from "../../src/types/incident";
import { orangeCase } from "../fixtures/data.mjs";

const SHOTS = {
  desktop: "evidence/j1/screenshot-desktop.png",
  tablet: "evidence/j1/screenshot-tablet.png",
  mobile: "evidence/j1/screenshot-mobile.png",
};

const EV: Evidence = {
  id: "v1",
  kind: "quote",
  label: "Ostrzeżenie o ryzyku (pomiar czcionki)",
  quote: "Inwestowanie wiąże się z ryzykiem.",
  span: { start: 0, end: 34 },
  storage_key: SHOTS.desktop,
  bbox: { viewport: "desktop", x: 480, y: 270, w: 192, h: 54 },
};

function incident(over: Partial<Incident["source"]["archive"]> = {}): Incident {
  return {
    ...orangeCase,
    source: { ...orangeCase.source, archive: { html_key: null, screenshot_key: SHOTS.desktop, screenshots: SHOTS, ...over } },
    evidence: [EV],
    rules: orangeCase.rules.map((r) =>
      r.id === "4"
        ? { ...r, status: "fail", method: "rendered", score: 0.61, explanation: "Tekst główny 16 px, ostrzeżenie 10 px (0,62×).", evidence_ids: ["v1"] }
        : r,
    ),
  };
}

/** jsdom does no layout: give the loaded image its intrinsic size. */
function load(img: HTMLElement, w: number, h: number) {
  Object.defineProperty(img, "naturalWidth", { value: w, configurable: true });
  Object.defineProperty(img, "naturalHeight", { value: h, configurable: true });
  fireEvent.load(img);
}

describe("ScreenshotEvidence", () => {
  it("draws the box scaled to the screenshot with alt text and the measured explanation", () => {
    render(<ScreenshotEvidence evidence={EV} incident={incident()} />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "/api/evidence/evidence/j1/screenshot-desktop.png");
    expect(img.getAttribute("alt")).toMatch(/ramką wokół: Ostrzeżenie o ryzyku/);
    expect(screen.queryByTestId("violation-box")).toBeNull(); // not before the image size is known
    load(img, 1920, 1080);
    const box = screen.getByTestId("violation-box");
    expect(box.style.left).toBe("25%");
    expect(box.style.top).toBe("25%");
    expect(box.style.width).toBe("10%");
    expect(box.style.height).toBe("5%");
    expect(screen.getByText("Tekst główny 16 px, ostrzeżenie 10 px (0,62×).")).toBeInTheDocument();
    expect(screen.getByText("pomiar w przeglądarce")).toBeInTheDocument();
  });

  it("switches viewports with the keyboard; the box only shows on its own viewport", async () => {
    const user = userEvent.setup();
    render(<ScreenshotEvidence evidence={EV} incident={incident()} />);
    const mobile = screen.getByRole("button", { name: "Telefon" });
    expect(screen.getByRole("button", { name: /Komputer/ })).toHaveAttribute("aria-pressed", "true");
    mobile.focus();
    await user.keyboard("{Enter}");
    expect(mobile).toHaveAttribute("aria-pressed", "true");
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "/api/evidence/evidence/j1/screenshot-mobile.png");
    load(img, 390, 2400);
    expect(screen.queryByTestId("violation-box")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Przełącz" }));
    expect(screen.getByRole("img")).toHaveAttribute("src", "/api/evidence/evidence/j1/screenshot-desktop.png");
  });

  it("has a focusable, labelled screenshot frame and no switcher with a single screenshot", () => {
    render(<ScreenshotEvidence evidence={EV} incident={incident({ screenshots: undefined })} />);
    expect(screen.queryByRole("group", { name: "Rozmiar ekranu" })).toBeNull();
    const frame = screen.getByRole("group", { name: /Zrzut ekranu: komputer 1920×1080/ });
    expect(frame).toHaveAttribute("tabindex", "0");
  });

  it("reports a box outside a height-capped screenshot instead of drawing it", () => {
    const ev = { ...EV, bbox: { ...EV.bbox!, y: 9000 } };
    render(<ScreenshotEvidence evidence={ev} incident={incident()} />);
    load(screen.getByRole("img"), 1920, 8000);
    expect(screen.queryByTestId("violation-box")).toBeNull();
    expect(screen.getByText(/poza zapisaną częścią zrzutu/)).toBeInTheDocument();
  });

  it("shows an error when the archived image cannot be loaded", () => {
    render(<ScreenshotEvidence evidence={EV} incident={incident()} />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByText(/Nie udało się wczytać zrzutu/)).toBeInTheDocument();
  });
});

describe("helpers", () => {
  it("clamps the box to the image and recognises screenshot evidence", () => {
    expect(boxStyle({ viewport: "mobile", x: 300, y: 0, w: 200, h: 10 }, { w: 400, h: 100 })).toEqual({
      left: "75%", top: "0%", width: "25%", height: "10%",
    });
    expect(boxStyle({ viewport: "mobile", x: 0, y: 0, w: 1, h: 1 }, { w: 0, h: 0 })).toBeNull();
    expect(hasScreenshotBox(EV)).toBe(true);
    expect(hasScreenshotBox({ ...EV, bbox: undefined })).toBe(false);
  });
});
