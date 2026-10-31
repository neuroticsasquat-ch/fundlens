import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, vi } from "vitest";
import { server } from "./api";
import { matchMedia } from "./media";

// What Mantine needs of the browser that jsdom does not have (Mantine's Vitest guide).
const { getComputedStyle } = window;
window.getComputedStyle = (element) => getComputedStyle(element);
window.HTMLElement.prototype.scrollIntoView = () => {};
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserver;
Object.defineProperty(document, "fonts", {
  value: { addEventListener: vi.fn(), removeEventListener: vi.fn(), ready: Promise.resolve() },
});

beforeAll(() => {
  server.listen({ onUnhandledFrame: "error" });
});

beforeEach(() => {
  // The system prefers light unless a test says otherwise.
  vi.stubGlobal("matchMedia", matchMedia({ dark: false }));
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

afterAll(() => {
  server.close();
});
