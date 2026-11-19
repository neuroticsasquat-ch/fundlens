import type { GiftSize, GiftSizeBucket } from "../api/client";
import type { ChartOption } from "../components/charts/echarts";
import type { ChartTheme } from "../components/charts/theme";
import { count, money, moneyCompact } from "../components/format";

/**
 * Each bucket's axis label, in the API's bucket order: FEC's unitemized lump, then donors by their
 * gift size. A range takes in its lower bound and stops short of its upper one; "$200 or less"
 * takes in $200 (every-FEC-dollar spec §4.6).
 */
export const GIFT_SIZE_LABELS: Record<GiftSizeBucket, string> = {
  unitemized: "Unitemized",
  "200_or_less": "$200 or less",
  under_500: "$200–$500",
  under_1000: "$500–$1,000",
  under_2000: "$1,000–$2,000",
  "2000_or_more": "$2,000 or more",
};

const ORDER = Object.keys(GIFT_SIZE_LABELS) as GiftSizeBucket[];

/** `sizes` in bucket order, whatever order they came in. */
export const inBucketOrder = (sizes: GiftSize[]) =>
  [...sizes].sort((a, b) => ORDER.indexOf(a.bucket) - ORDER.indexOf(b.bucket));

/** "$10,300, FEC's unitemized lump"; "$4,550 from 12 donors". */
function tooltip(size: GiftSize): string {
  const label = GIFT_SIZE_LABELS[size.bucket];
  if (size.donors === null) return `${label}: ${money(size.amount)}, reported as one lump`;
  const donors = `${count(size.donors)} ${size.donors === 1 ? "donor" : "donors"}`;
  return `${label}: ${money(size.amount)} from ${donors}`;
}

/**
 * A candidate's money in a cycle by gift size: one vertical bar per bucket, in bucket order, of
 * the money in it. Unitemized money is FEC's lump, which names no donor, so its own bar, in its
 * own colour, never added to a donor's bucket (spec §4.6).
 */
export function giftSizeOption(sizes: GiftSize[], theme: ChartTheme): ChartOption {
  const ordered = inBucketOrder(sizes);
  return {
    grid: { left: 8, right: 24, top: 16, bottom: 8, containLabel: true },
    legend: { show: false },
    tooltip: {
      trigger: "item",
      // ECharts hands the hovered bar's params; its `dataIndex` is the bucket's place in `ordered`.
      formatter: (params: unknown) => tooltip(ordered[(params as { dataIndex: number }).dataIndex]),
    },
    xAxis: {
      type: "category",
      data: ordered.map((size) => GIFT_SIZE_LABELS[size.bucket]),
      axisLine: { lineStyle: { color: theme.axis } },
      axisTick: { show: false },
      axisLabel: { color: theme.dimmed },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: theme.dimmed, formatter: moneyCompact },
      splitLine: { lineStyle: { color: theme.grid } },
    },
    series: [
      {
        type: "bar",
        name: "Gift sizes",
        data: ordered.map((size) => ({
          value: size.amount,
          itemStyle: { color: size.bucket === "unitemized" ? theme.unitemized : theme.itemized },
        })),
      },
    ],
  };
}
