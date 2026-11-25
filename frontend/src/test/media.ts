import { vi } from "vitest";

/**
 * A `window.matchMedia` stand-in (jsdom has none) whose `prefers-color-scheme: dark` answer is
 * `dark`, and whose every `max-width` query matches when `narrow` (a phone's screen); every other
 * query does not match. `setup.ts` installs the light, wide one before each test; a test re-stubs
 * it to render the dark scheme, or a phone:
 *
 *     vi.stubGlobal("matchMedia", matchMedia({ dark: true }));
 *     vi.stubGlobal("matchMedia", matchMedia({ dark: false, narrow: true }));
 */
export function matchMedia({ dark, narrow = false }: { dark: boolean; narrow?: boolean }) {
  return vi.fn((query: string) => ({
    matches:
      (dark && query === "(prefers-color-scheme: dark)") ||
      (narrow && query.startsWith("(max-width:")),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
