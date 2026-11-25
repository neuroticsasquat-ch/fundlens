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

/**
 * How the panels share the chart: side by side, sharing the candidates' rows, or, where the chart
 * is too narrow for that (a phone), stacked one above the next, each the full width and naming the
 * candidates itself.
 */
export type CandidateTotalsLayout = { stacked: boolean };

// Side by side: where each panel after "Raised" starts, as a share of the chart's width, by how
// many there are: the "Raised" panel, leftmost, also holds the candidates' names.
const STARTS: Record<number, number[]> = { 1: [], 2: [60], 3: [40, 80] };

// Above the bars: a margin for the "Raised" panel alone, else the panels' headings.
const top = (count: number) => (count > 1 ? 32 : 8);
// Below them: the legend, under every panel, when there is outside spending to tell apart.
const LEGEND = 32;
const bottom = (count: number) => (count > 1 ? 8 + LEGEND : 8);
// A panel's bars: a 40px row per candidate, and 40px under them for the axis labels and a margin.
const bars = (candidates: RaceCandidate[]) => 40 + 40 * candidates.length;
// Stacked: between one panel's axis labels and the next one's heading.
const GAP = 16;
// Stacked: the legend lists its entries one per line, each this tall with the gap below it.
const LEGEND_ENTRY = 24;

const panelCount = (candidates: RaceCandidate[]) => {
  const { signed, electioneering } = panels(candidates);
  return 1 + (signed.length > 0 ? 1 : 0) + (electioneering ? 1 : 0);
};

/** How many series the legend lists: every one but "Raised". */
const legendCount = (candidates: RaceCandidate[]) => {
  const { signed, electioneering } = panels(candidates);
  return signed.length + (electioneering ? 1 : 0);
};

/**
 * The height, in pixels, of the chart `candidateTotalsOption` draws for these candidates: the
 * headings and bars of one panel, or of each when they are stacked, and the legend.
 */
export const candidateTotalsHeight = (
  candidates: RaceCandidate[],
  { stacked }: CandidateTotalsLayout = { stacked: false },
) => {
  const count = panelCount(candidates);
  const panel = top(count) + bars(candidates);
  if (count === 1) return panel;
  if (!stacked) return panel + LEGEND;
  return count * (panel + GAP) + LEGEND_ENTRY * legendCount(candidates);
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
 * give every amount as a positive one. The panels are side by side unless `stacked`.
 */
export function candidateTotalsOption(
  candidates: RaceCandidate[],
  theme: ChartTheme,
  { stacked }: CandidateTotalsLayout = { stacked: false },
): ChartOption {
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
    // Three panels share the width, so a narrow one has room for fewer amounts than ECharts
    // ticks: a label that would run into the one before it is left out.
    axisLabel: { color: theme.dimmed, formatter, hideOverlap: true },
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
  const panelTop = top(count);
  const style = { textStyle: { color: theme.ink, fontSize: 14, fontWeight: 600 } };
  const headings = ["Raised", ...others.map((panel) => panel.heading)];
  const series = [raised, ...others.flatMap((panel, i) => panel.series(i + 1))];
  const { legend, ...layout } = stacked ? stackedLayout() : besideLayout();
  return {
    ...layout,
    // Every series but "Raised", whose bars are each their party's colour.
    legend: {
      show: true,
      bottom: 0,
      left: 8,
      data: series.slice(1).map(({ name }) => name),
      textStyle: { color: theme.ink },
      ...legend,
    },
    // Hovering any panel points at the candidate's row in all of them, and the tooltip lists
    // every series.
    axisPointer: { link: [{ yAxisIndex: "all" }] },
    tooltip,
    xAxis: [
      valueAxis(0, moneyCompact),
      ...others.map((panel, i) => valueAxis(i + 1, panel.label)),
    ],
    series,
  };

  /** Side by side, on one set of rows, which only the leftmost panel, "Raised", names. */
  function besideLayout() {
    const starts = STARTS[count];
    const panelBottom = bottom(count);
    return {
      title: headings.map((text, i) => ({
        ...style,
        text,
        top: 0,
        left: i === 0 ? 8 : `${starts[i - 1]}%`,
      })),
      // Each panel stops 4% of the width short of the next, for a gap between them.
      grid: headings.map((_, i) => ({
        left: i === 0 ? 8 : `${starts[i - 1]}%`,
        right: i < starts.length ? `${100 - starts[i] + 4}%` : 24,
        top: panelTop,
        bottom: panelBottom,
        containLabel: true,
      })),
      yAxis: headings.map((_, i) => categoryAxis(i, i === 0)),
      // One line, scrolled where it is too long for the width.
      legend: { type: "scroll", right: 24 } as const,
    };
  }

  /**
   * One above the next, each the full width under its heading: too narrow to share, a panel
   * beside "Raised" would leave no room for its bars once the names took theirs. So every panel
   * names the candidates, down its own rows.
   */
  function stackedLayout() {
    const panel = panelTop + bars(candidates) + GAP;
    return {
      title: headings.map((text, i) => ({ ...style, text, top: i * panel, left: 8 })),
      grid: headings.map((_, i) => ({
        left: 8,
        right: 24,
        top: i * panel + panelTop,
        height: bars(candidates),
        containLabel: true,
      })),
      yAxis: headings.map((_, i) => categoryAxis(i, true)),
      // An entry a line, all of them: one line would show a narrow chart's entries one at a time.
      // Each is ECharts' 14px legend item and the gap under it.
      legend: { type: "plain", orient: "vertical", itemGap: LEGEND_ENTRY - 14 } as const,
    };
  }
}
