import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, expect, vi } from "vitest";

// jsdom has no layout: report a fixed size so charts render as they do in a browser.
class ResizeObserverStub {
  private readonly callback: ResizeObserverCallback;
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }
  observe(target: Element) {
    const contentRect = { width: 640, height: 220, top: 0, left: 0, right: 640, bottom: 220, x: 0, y: 0 };
    this.callback([{ target, contentRect } as unknown as ResizeObserverEntry], this as unknown as ResizeObserver);
  }
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;

// jsdom lacks these; Radix (slider, dialog) and cmdk call them.
Element.prototype.scrollIntoView = vi.fn();
Element.prototype.hasPointerCapture = vi.fn(() => false);
Element.prototype.setPointerCapture = vi.fn();
Element.prototype.releasePointerCapture = vi.fn();
window.matchMedia ??= ((query: string) => ({
  matches: false, media: query, onchange: null, addListener: vi.fn(), removeListener: vi.fn(),
  addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
})) as unknown as typeof window.matchMedia;

// The demo criterion is a clean console: any console.error / console.warn during a test fails it
// (React key warnings, act() warnings, Radix a11y warnings, unhandled render errors…).
let errorSpy: ReturnType<typeof vi.spyOn>;
let warnSpy: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
  warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
});

afterEach(() => {
  const noise = [...errorSpy.mock.calls, ...warnSpy.mock.calls].map((args) => args.map(String).join(" ").slice(0, 300));
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
  expect(noise, "console.error / console.warn must stay silent").toEqual([]);
});
