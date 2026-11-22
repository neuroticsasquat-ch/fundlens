import type { SpendingByCategory } from "../api/client";
import type { ChartOption } from "../components/charts/echarts";
import type { ChartTheme } from "../components/charts/theme";
import { money, moneyCompact } from "../components/format";
import { SPENDING_CATEGORY_LABELS } from "../domain/spending";

/** `categories`, most money first; a tie in the spec's table order. */
export function byAmount(categories: SpendingByCategory[]): SpendingByCategory[] {
  const order = Object.keys(SPENDING_CATEGORY_LABELS);
  return [...categories].sort(
    (a, b) => b.amount - a.amount || order.indexOf(a.category) - order.indexOf(b.category),
  );
}

/**
 * The height, in pixels, of the chart `spendingCategoryOption` draws: a 32px row per category and
 * 40px under them for the axis labels and a margin.
 */
export const spendingCategoryHeight = (categories: SpendingByCategory[]) =>
  40 + 32 * categories.length;

/**
 * A committee's counted spending in a cycle by category: one horizontal bar each, most money at
 * the top. A category netting to $0 or less, refunds over payments, is kept and drawn left of
 * zero, so the bars add up to the committee's total (every-FEC-dollar spec §5.5).
 */
export function spendingCategoryOption(
  categories: SpendingByCategory[],
  theme: ChartTheme,
): ChartOption {
  const ordered = byAmount(categories);
  return {
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    legend: { show: false },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: (value: unknown) => money(Number(value)),
    },
    xAxis: {
      type: "value",
      axisLabel: { color: theme.dimmed, formatter: moneyCompact },
      splitLine: { lineStyle: { color: theme.grid } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: ordered.map((row) => SPENDING_CATEGORY_LABELS[row.category]),
      axisLine: { lineStyle: { color: theme.axis } },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        name: "Spending",
        data: ordered.map((row) => row.amount),
        itemStyle: { color: theme.spending },
      },
    ],
  };
}
