import type { ChartOption } from "../components/charts/echarts";
import type { ChartTheme } from "../components/charts/theme";
import { money, moneyCompact } from "../components/format";

/** One stacked part of a cycle's bar: "From individuals" and how to read it off a row. */
export type CycleSeries<T> = { name: string; value: (row: T) => number };

/** A bar per cycle, oldest on the left, stacked from `series`. */
export function cycleTotalsOption<T extends { cycle: number }>(
  rows: T[],
  series: CycleSeries<T>[],
  theme: ChartTheme,
): ChartOption {
  const oldestFirst = [...rows].sort((a, b) => a.cycle - b.cycle);
  return {
    grid: { left: 8, right: 8, top: 40, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: theme.ink } },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: (value) => money(Number(value)),
    },
    xAxis: {
      type: "category",
      data: oldestFirst.map((row) => String(row.cycle)),
      axisLine: { lineStyle: { color: theme.axis } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: theme.dimmed, formatter: (value: number) => moneyCompact(value) },
      splitLine: { lineStyle: { color: theme.grid } },
    },
    series: series.map(({ name, value }) => ({
      type: "bar",
      name,
      stack: "total",
      // One cycle would otherwise be a bar the chart's whole width.
      barMaxWidth: 64,
      data: oldestFirst.map(value),
    })),
  };
}
