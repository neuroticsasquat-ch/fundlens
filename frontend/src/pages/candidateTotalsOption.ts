import type { RaceCandidate } from "../api/client";
import type { ChartOption } from "../components/charts/echarts";
import type { ChartTheme } from "../components/charts/theme";
import { money, moneyCompact } from "../components/format";
import { candidateName, candidateTotal } from "../domain/candidates";
import { partyKey } from "../theme";

const SUPPORT = "Independent expenditures for";
const OPPOSE = "Independent expenditures against";

// Where the independent expenditures' panel starts, as a share of the chart's width: the
// "Raised" panel left of it also holds the candidates' names.
const SPLIT = 60;

// Above the bars: nothing but a margin for the "Raised" panel alone; the panels' headings and the
// legend under the second one's when there are two.
const top = (independent: boolean) => (independent ? 56 : 8);

const hasIndependentExpenditures = (candidates: RaceCandidate[]) =>
  candidates.some((candidate) => candidate.ie_support !== 0 || candidate.ie_oppose !== 0);

/**
 * The height, in pixels, of the chart `candidateTotalsOption` draws for these candidates: its
 * headings, a 40px row per candidate and 40px under them for the axis labels and a margin.
 */
export const candidateTotalsHeight = (candidates: RaceCandidate[]) =>
  top(hasIndependentExpenditures(candidates)) + 40 + 40 * candidates.length;

/**
 * What each candidate raised, one horizontal bar each in their party's colour, in the order given
 * (biggest at the top). When any candidate has independent expenditures, a second panel beside it,
 * on the same candidates' rows, draws them: against a candidate left of zero, for them right of
 * it. They are others' spending, never money the candidate received (spec §7.1), so none is
 * stacked onto what a candidate raised. The tooltip, legend and axis give both as positive amounts.
 */
export function candidateTotalsOption(candidates: RaceCandidate[], theme: ChartTheme): ChartOption {
  const independent = hasIndependentExpenditures(candidates);
  const names = candidates.map(candidateName);
  const tooltip = {
    trigger: "axis",
    axisPointer: { type: "shadow" },
    valueFormatter: (value: unknown) => money(Number(value)),
  } as const;
  const valueAxis = (gridIndex: number, formatter: (value: number) => string) => ({
    type: "value" as const,
    gridIndex,
    axisLabel: { color: theme.dimmed, formatter },
    splitLine: { lineStyle: { color: theme.grid } },
  });
  const categoryAxis = (gridIndex: number, labelled: boolean) => ({
    type: "category" as const,
    gridIndex,
    inverse: true,
    data: names,
    axisLine: { lineStyle: { color: theme.axis } },
    axisTick: { show: false },
    axisLabel: { show: labelled },
  });
  const raised = {
    type: "bar" as const,
    name: "Raised",
    xAxisIndex: 0,
    yAxisIndex: 0,
    data: candidates.map((candidate) => ({
      value: candidateTotal(candidate),
      itemStyle: { color: theme.party[partyKey(candidate.party)] },
    })),
  };

  if (!independent) {
    return {
      grid: { left: 8, right: 24, top: top(false), bottom: 8, containLabel: true },
      // Not "Raised": its bars are each their party's colour, which no one swatch shows.
      legend: { show: false },
      tooltip,
      xAxis: valueAxis(0, moneyCompact),
      yAxis: categoryAxis(0, true),
      series: [raised],
    };
  }

  const heading = { top: 0, textStyle: { color: theme.ink, fontSize: 14, fontWeight: 600 } };
  const ie = { type: "bar" as const, stack: "independent", xAxisIndex: 1, yAxisIndex: 1 };
  return {
    title: [
      { ...heading, text: "Raised", left: 8 },
      { ...heading, text: "Independent expenditures", left: `${SPLIT}%` },
    ],
    // The "Raised" panel stops 4% of the width short of the second, for a gap between them.
    grid: [
      { left: 8, right: `${100 - SPLIT + 4}%`, top: top(true), bottom: 8, containLabel: true },
      { left: `${SPLIT}%`, right: 24, top: top(true), bottom: 8, containLabel: true },
    ],
    // Against first, as it is drawn on the left.
    legend: {
      show: true,
      top: 26,
      left: `${SPLIT}%`,
      data: [OPPOSE, SUPPORT],
      formatter: (name: string) => (name === SUPPORT ? "For" : "Against"),
      textStyle: { color: theme.ink },
    },
    // Hovering either panel points at the candidate's row in both, and the tooltip lists all three.
    axisPointer: { link: [{ yAxisIndex: "all" }] },
    tooltip,
    xAxis: [
      valueAxis(0, moneyCompact),
      valueAxis(1, (value) => moneyCompact(Math.abs(value))),
    ],
    yAxis: [categoryAxis(0, true), categoryAxis(1, false)],
    series: [
      raised,
      {
        ...ie,
        name: SUPPORT,
        itemStyle: { color: theme.support },
        data: candidates.map((candidate) => candidate.ie_support),
      },
      {
        ...ie,
        name: OPPOSE,
        itemStyle: { color: theme.oppose },
        // `0 - x`, not `-x`, so a candidate with none is 0 rather than -0.
        data: candidates.map((candidate) => 0 - candidate.ie_oppose),
        tooltip: { valueFormatter: (value: unknown) => money(0 - Number(value)) },
      },
    ],
  };
}
