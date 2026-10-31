import { useComputedColorScheme, useMantineTheme } from "@mantine/core";
import type { MantineTheme } from "@mantine/core";
import { useMemo } from "react";
import { PARTY_COLOURS } from "../../theme";
import type { PartyColourKey } from "../../theme";

export type ChartTheme = {
  ink: string;
  dimmed: string;
  axis: string;
  grid: string;
  background: string;
  /** `PARTY_COLOURS`, resolved to the colours ECharts draws with. */
  party: Record<PartyColourKey, string>;
};

// A `blue.6` token as the colour itself: a canvas cannot draw Mantine's CSS variables.
const resolve = (token: string, theme: MantineTheme) => {
  const [name, shade] = token.split(".");
  return theme.colors[name][Number(shade)];
};

/**
 * The chart colours for the colour scheme in force: Mantine's, which follows the system. The same
 * object until the scheme changes, so a chart can memoize its option on it.
 */
export function useChartTheme(): ChartTheme {
  const theme = useMantineTheme();
  const dark = useComputedColorScheme("light") === "dark";
  return useMemo(() => chartTheme(theme, dark), [theme, dark]);
}

function chartTheme(theme: MantineTheme, dark: boolean): ChartTheme {
  return {
    ink: dark ? theme.colors.dark[0] : theme.black,
    dimmed: dark ? theme.colors.dark[2] : theme.colors.gray[6],
    axis: dark ? theme.colors.dark[3] : theme.colors.gray[5],
    grid: dark ? theme.colors.dark[5] : theme.colors.gray[2],
    background: "transparent",
    party: {
      DEM: resolve(PARTY_COLOURS.DEM, theme),
      REP: resolve(PARTY_COLOURS.REP, theme),
      other: resolve(PARTY_COLOURS.other, theme),
    },
  };
}
