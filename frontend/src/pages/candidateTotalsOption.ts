import type { RaceCandidate } from "../api/client";
import type { ChartOption } from "../components/charts/echarts";
import type { ChartTheme } from "../components/charts/theme";
import { money, moneyCompact } from "../components/format";
import { candidateName, candidateTotal } from "../domain/candidates";
import { partyKey } from "../theme";

/**
 * A kind of outside spending with a side, as the second panel draws it: `value` is the amount for
 * a candidate, drawn right of zero, or against them, drawn left of it.
 */
type SignedSeries = {
  name: string;
  side: "support" | "oppose";
  colour: (theme: ChartTheme) => string;
  value: (candidate: RaceCandidate) => number;
};

// Against first, as it is drawn on the left; within a side, independent expenditures nearest zero.
const SIGNED: SignedSeries[] = [
  {
    name: "Independent expenditures against",
    side: "oppose",
    colour: (theme) => theme.oppose,
    value: (candidate) => candidate.outside_spending.independent_expenditure.oppose,
  },
  {
    name: "Communication costs against",
    side: "oppose",
    colour: (theme) => theme.communicationOppose,
    value: (candidate) => candidate.outside_spending.communication_cost.oppose,
  },
  {
    name: "Independent expenditures for",
    side: "support",
    colour: (theme) => theme.support,
    value: (candidate) => candidate.outside_spending.independent_expenditure.support,
  },
  {
    name: "Communication costs for",
    side: "support",
    colour: (theme) => theme.communicationSupport,
    value: (candidate) => candidate.outside_spending.communication_cost.support,
  },
  {
    // Always in support (spec §6.1).
    name: "Party coordinated expenditures",
    side: "support",
    colour: (theme) => theme.coordinated,
    value: (candidate) => candidate.outside_spending.party_coordinated,
  },
];

const ELECTIONEERING = "Electioneering communications";
const electioneering = (candidate: RaceCandidate) =>
  candidate.outside_spending.electioneering_communication ?? 0;

/** The signed kinds any of these candidates has, and whether any has electioneering. */
function panels(candidates: RaceCandidate[]) {
  return {
    signed: SIGNED.filter((series) => candidates.some((candidate) => series.value(candidate) !== 0)),
    electioneering: candidates.some((candidate) => electioneering(candidate) !== 0),
  };
}

// Where each panel after "Raised" starts, as a share of the chart's width, by how many there are:
// the "Raised" panel, leftmost, also holds the candidates' names.
const STARTS: Record<number, number[]> = { 1: [], 2: [60], 3: [40, 80] };

// Above the bars: a margin for the "Raised" panel alone, else the panels' headings.
const top = (count: number) => (count > 1 ? 32 : 8);
// Below them: the legend, under every panel, when there is outside spending to tell apart.
const LEGEND = 32;
const bottom = (count: number) => (count > 1 ? 8 + LEGEND : 8);

const panelCount = (candidates: RaceCandidate[]) => {
  const { signed, electioneering } = panels(candidates);
  return 1 + (signed.length > 0 ? 1 : 0) + (electioneering ? 1 : 0);
};

/**
 * The height, in pixels, of the chart `candidateTotalsOption` draws for these candidates: its
 * headings, a 40px row per candidate, 40px under them for the axis labels and a margin, and the
 * legend.
 */
export const candidateTotalsHeight = (candidates: RaceCandidate[]) => {
  const count = panelCount(candidates);
  return top(count) + 40 + 40 * candidates.length + (count > 1 ? LEGEND : 0);
};

/**
 * What each candidate raised, one horizontal bar each in their party's colour, in the order given
 * (biggest at the top). Beside it, on the same candidates' rows, what others spent on them
 * (every-FEC-dollar spec §6.5), a panel for each that any candidate has:
 *
 * - **For and against:** independent expenditures, communication costs and party coordinated
 *   expenditures, stacked by side, against a candidate left of zero and for them right of it.
 * - **Electioneering:** electioneering communications, which call for no vote, so a bar of their
 *   own on no side.
 *
 * Outside spending is never money the candidate received, so none is stacked onto what a
 * candidate raised, and no kind is added to another across sides. The tooltip, legend and axes
 * give every amount as a positive one.
 */
export function candidateTotalsOption(candidates: RaceCandidate[], theme: ChartTheme): ChartOption {
  const { signed, electioneering: hasElectioneering } = panels(candidates);
  const count = panelCount(candidates);
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

  if (count === 1) {
    return {
      grid: { left: 8, right: 24, top: top(1), bottom: bottom(1), containLabel: true },
      // Not "Raised": its bars are each their party's colour, which no one swatch shows.
      legend: { show: false },
      tooltip,
      xAxis: valueAxis(0, moneyCompact),
      yAxis: categoryAxis(0, true),
      series: [raised],
    };
  }

  // Each panel after "Raised": its heading, its series and how its axis labels a value.
  const others = [
    ...(signed.length > 0
      ? [
          {
            heading: "For and against",
            label: (value: number) => moneyCompact(Math.abs(value)),
            series: (index: number) =>
              signed.map((series) => ({
                type: "bar" as const,
                // ECharts stacks a side's amounts on that side of zero (`stackStrategy`
                // "samesign"), so a kind is never added to one on the other side.
                stack: "signed",
                name: series.name,
                xAxisIndex: index,
                yAxisIndex: index,
                itemStyle: { color: series.colour(theme) },
                ...(series.side === "support"
                  ? { data: candidates.map(series.value) }
                  : {
                      // `0 - x`, not `-x`, so a candidate with none is 0 rather than -0.
                      data: candidates.map((candidate) => 0 - series.value(candidate)),
                      tooltip: { valueFormatter: (value: unknown) => money(0 - Number(value)) },
                    }),
              })),
          },
        ]
      : []),
    ...(hasElectioneering
      ? [
          {
            heading: "Electioneering",
            label: moneyCompact,
            series: (index: number) => [
              {
                type: "bar" as const,
                name: ELECTIONEERING,
                xAxisIndex: index,
                yAxisIndex: index,
                itemStyle: { color: theme.electioneering },
                data: candidates.map(electioneering),
              },
            ],
          },
        ]
      : []),
  ];
  const starts = STARTS[count];
  const panelTop = top(count);
  const panelBottom = bottom(count);
  const heading = { top: 0, textStyle: { color: theme.ink, fontSize: 14, fontWeight: 600 } };
  const series = [raised, ...others.flatMap((panel, i) => panel.series(i + 1))];
  return {
    title: [
      { ...heading, text: "Raised", left: 8 },
      ...others.map((panel, i) => ({ ...heading, text: panel.heading, left: `${starts[i]}%` })),
    ],
    // Each panel stops 4% of the width short of the next, for a gap between them.
    grid: [
      {
        left: 8,
        right: `${100 - starts[0] + 4}%`,
        top: panelTop,
        bottom: panelBottom,
        containLabel: true,
      },
      ...others.map((_, i) => ({
        left: `${starts[i]}%`,
        right: i + 1 < starts.length ? `${100 - starts[i + 1] + 4}%` : 24,
        top: panelTop,
        bottom: panelBottom,
        containLabel: true,
      })),
    ],
    // Every series but "Raised", whose bars are each their party's colour; one line, scrolled
    // where it is too long for the width.
    legend: {
      show: true,
      type: "scroll",
      bottom: 0,
      left: 8,
      right: 24,
      data: series.slice(1).map(({ name }) => name),
      textStyle: { color: theme.ink },
    },
    // Hovering any panel points at the candidate's row in all of them, and the tooltip lists
    // every series.
    axisPointer: { link: [{ yAxisIndex: "all" }] },
    tooltip,
    xAxis: [
      valueAxis(0, moneyCompact),
      ...others.map((panel, i) => valueAxis(i + 1, panel.label)),
    ],
    yAxis: [categoryAxis(0, true), ...others.map((_, i) => categoryAxis(i + 1, false))],
    series,
  };
}
