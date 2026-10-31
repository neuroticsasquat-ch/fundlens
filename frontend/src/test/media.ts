import { vi } from "vitest";

/**
 * A `window.matchMedia` stand-in (jsdom has none) whose `prefers-color-scheme: dark` answer is
 * `dark`; every other query does not match. `setup.ts` installs the light one before each test;
 * a test re-stubs it to render the dark scheme:
 *
 *     vi.stubGlobal("matchMedia", matchMedia({ dark: true }));
 */
export function matchMedia({ dark }: { dark: boolean }) {
  return vi.fn((query: string) => ({
    matches: dark && query === "(prefers-color-scheme: dark)",
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
