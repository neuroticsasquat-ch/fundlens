import { Stack, Text } from "@mantine/core";
import { useMemo } from "react";
import type { RaceCandidate } from "../api/client";
import EChart from "../components/charts/EChart";
import { useChartTheme } from "../components/charts/theme";
import { count } from "../components/format";
import { candidateSpending } from "../domain/candidates";
import { candidateTotalsOption } from "./candidateTotalsOption";

// The most bars charted. A presidential race lists every filer (1,602 in 2024, most with nothing),
// and a bar each would make a canvas taller than the browser will draw.
const CHARTED = 15;

/**
 * The race split: the candidates with the most money raised and spent for or against them, each a
 * bar of what they raised, coloured by party, and the independent expenditures for and against
 * them, most first rather than in the API's order; a candidate with none is left out, and so is
 * the chart when nobody has any.
 */
function CandidateTotalsChart({ candidates }: { candidates: RaceCandidate[] }) {
  const theme = useChartTheme();
  const charted = useMemo(
    () =>
      candidates
        .filter((candidate) => candidateSpending(candidate) > 0)
        .sort((a, b) => candidateSpending(b) - candidateSpending(a))
        .slice(0, CHARTED),
    [candidates],
  );
  const option = useMemo(() => candidateTotalsOption(charted, theme), [charted, theme]);
  if (charted.length === 0) return null;
  return (
    <Stack gap={4}>
      <EChart option={option} style={{ width: "100%", height: 48 + 40 * charted.length }} />
      {charted.length < candidates.length && (
        <Text size="sm" c="dimmed">
          The {count(charted.length)} candidates with the most money, of{" "}
          {count(candidates.length)}. The table lists them all.
        </Text>
      )}
    </Stack>
  );
}

export default CandidateTotalsChart;
