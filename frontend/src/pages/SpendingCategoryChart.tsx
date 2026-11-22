import { useMemo } from "react";
import type { SpendingByCategory } from "../api/client";
import EChart from "../components/charts/EChart";
import { useChartTheme } from "../components/charts/theme";
import { spendingCategoryHeight, spendingCategoryOption } from "./spendingCategoryOption";

/** A committee's spending in a cycle by category (`spendingCategoryOption`). */
function SpendingCategoryChart({ categories }: { categories: SpendingByCategory[] }) {
  const theme = useChartTheme();
  const option = useMemo(() => spendingCategoryOption(categories, theme), [categories, theme]);
  return (
    <EChart
      option={option}
      style={{ width: "100%", height: spendingCategoryHeight(categories) }}
    />
  );
}

export default SpendingCategoryChart;
