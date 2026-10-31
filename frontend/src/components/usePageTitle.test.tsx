import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { usePageTitle } from "./usePageTitle";

describe("usePageTitle", () => {
  it("suffixes the page's title and is just fundlens without one", () => {
    const { rerender } = renderHook((title?: string) => usePageTitle(title), {
      initialProps: "2024 races",
    });
    expect(document.title).toBe("2024 races · fundlens");

    rerender(undefined);
    expect(document.title).toBe("fundlens");
  });
});
