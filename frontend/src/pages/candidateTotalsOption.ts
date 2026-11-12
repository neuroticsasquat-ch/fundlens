import type { RaceCandidate } from "../api/client";
import type { ChartOption } from "../components/charts/echarts";
import type { ChartTheme } from "../components/charts/theme";
import { money, moneyCompact } from "../components/format";
import { candidateName, candidateTotal } from "../domain/candidates";
import { partyKey } from "../theme";

const SUPPORT = "Independent expenditures for";
const OPPOSE = "Independent expenditures against";

/**
 * One horizontal bar per candidate, in the order given (biggest at the top): what they raised, in
 * their party's colour, then the independent expenditures for and against them stacked after it,
 * with a legend naming those two when any candidate has either. The tooltip names all three.
 */
export function candidateTotalsOption(candidates: RaceCandidate[], theme: ChartTheme): ChartOption {
  const independent = candidates.some(
    (candidate) => candidate.ie_support !== 0 || candidate.ie_oppose !== 0,
  );
  const bar = { type: "bar", stack: "spending" } as const;
  return {
    grid: { left: 8, right: 24, top: independent ? 40 : 8, bottom: 8, containLabel: true },
    // Not "Raised": its bars are each their party's colour, which no one swatch shows.
    legend: { show: independent, top: 0, data: [SUPPORT, OPPOSE], textStyle: { color: theme.ink } },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: (value) => money(Number(value)),
    },
    xAxis: {
      type: "value",
      axisLabel: { color: theme.dimmed, formatter: (value: number) => moneyCompact(value) },
      splitLine: { lineStyle: { color: theme.grid } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: candidates.map(candidateName),
      axisLine: { lineStyle: { color: theme.axis } },
      axisTick: { show: false },
    },
    series: [
      {
        ...bar,
        name: "Raised",
        data: candidates.map((candidate) => ({
          value: candidateTotal(candidate),
          itemStyle: { color: theme.party[partyKey(candidate.party)] },
        })),
      },
      ...(independent
        ? [
            {
              ...bar,
              name: SUPPORT,
              itemStyle: { color: theme.support },
              data: candidates.map((candidate) => candidate.ie_support),
            },
            {
              ...bar,
              name: OPPOSE,
              itemStyle: { color: theme.oppose },
              data: candidates.map((candidate) => candidate.ie_oppose),
            },
          ]
        : []),
    ],
  };
}
