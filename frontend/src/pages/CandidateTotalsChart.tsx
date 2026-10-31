import { useMemo } from "react";
import type { RaceCandidate } from "../api/client";
import EChart from "../components/charts/EChart";
import { useChartTheme } from "../components/charts/theme";
import { candidateTotalsOption } from "./candidateTotalsOption";

/** The race split: each candidate's total as a bar, coloured by party. */
function CandidateTotalsChart({ candidates }: { candidates: RaceCandidate[] }) {
  const theme = useChartTheme();
  const option = useMemo(() => candidateTotalsOption(candidates, theme), [candidates, theme]);
  return <EChart option={option} style={{ width: "100%", height: 48 + 40 * candidates.length }} />;
}

export default CandidateTotalsChart;
