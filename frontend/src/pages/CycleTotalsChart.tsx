import { useMemo } from "react";
import EChart from "../components/charts/EChart";
import { useChartTheme } from "../components/charts/theme";
import { cycleTotalsOption } from "./cycleTotalsOption";
import type { CycleSeries } from "./cycleTotalsOption";

/** A candidate's or committee's money by cycle, as stacked bars. */
function CycleTotalsChart<T extends { cycle: number }>({
  rows,
  series,
}: {
  rows: T[];
  series: CycleSeries<T>[];
}) {
  const theme = useChartTheme();
  const option = useMemo(() => cycleTotalsOption(rows, series, theme), [rows, series, theme]);
  return <EChart option={option} style={{ width: "100%", height: 280 }} />;
}

export default CycleTotalsChart;
