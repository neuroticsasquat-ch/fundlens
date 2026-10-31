import { DEFAULT_THEME } from "@mantine/core";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import Providers from "../../Providers";
import { createQueryClient } from "../../api/query";
import { matchMedia } from "../../test/media";
import { useChartTheme } from "./theme";

const wrapper = ({ children }: { children: ReactNode }) => (
  <Providers queryClient={createQueryClient()} env="test">
    {children}
  </Providers>
);

describe("useChartTheme", () => {
  it("draws with dark ink when the system prefers dark", async () => {
    vi.stubGlobal("matchMedia", matchMedia({ dark: true }));

    const { result } = renderHook(() => useChartTheme(), { wrapper });

    await waitFor(() => expect(result.current.ink).toBe(DEFAULT_THEME.colors.dark[0]));
    expect(result.current.grid).toBe(DEFAULT_THEME.colors.dark[5]);
    expect(document.documentElement).toHaveAttribute("data-mantine-color-scheme", "dark");
  });

  it("draws with light ink otherwise, and resolves the party colours", () => {
    const { result } = renderHook(() => useChartTheme(), { wrapper });

    expect(result.current.ink).toBe(DEFAULT_THEME.black);
    expect(result.current.background).toBe("transparent");
    expect(result.current.party).toEqual({
      DEM: DEFAULT_THEME.colors.blue[6],
      REP: DEFAULT_THEME.colors.red[6],
      other: DEFAULT_THEME.colors.gray[6],
    });
  });
});
