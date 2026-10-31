import type { RaceCandidate } from "../api/client";
import type { ChartOption } from "../components/charts/echarts";
import type { ChartTheme } from "../components/charts/theme";
import { money, moneyCompact } from "../components/format";
import { candidateName, candidateTotal } from "../domain/candidates";
import { partyKey } from "../theme";

/** One horizontal bar per candidate, in the order given (biggest at the top), in party colours. */
export function candidateTotalsOption(candidates: RaceCandidate[], theme: ChartTheme): ChartOption {
  return {
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
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
        type: "bar",
        name: "Total",
        data: candidates.map((candidate) => ({
          value: candidateTotal(candidate),
          itemStyle: { color: theme.party[partyKey(candidate.party)] },
        })),
      },
    ],
  };
}
