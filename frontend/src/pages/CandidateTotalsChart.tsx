import { Stack, Text, useMantineTheme } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { useMemo } from "react";
import type { RaceCandidate } from "../api/client";
import EChart from "../components/charts/EChart";
import { useChartTheme } from "../components/charts/theme";
import { count } from "../components/format";
import { candidateTotal } from "../domain/candidates";
import { hasOutsideSpending, outsideSpendingVolume } from "../domain/outsideSpending";
import { candidateTotalsHeight, candidateTotalsOption } from "./candidateTotalsOption";

// The most bars charted. A presidential race lists every filer (1,602 in 2024, most with nothing),
// and a bar each would make a canvas taller than the browser will draw.
const CHARTED = 15;

/**
 * The race split: the candidates who raised the most, most first rather than in the API's order,
 * each a bar of what they raised, coloured by party, with the outside spending of every kind on
 * them in panels beside it. Others' spending never orders them: a candidate who raised nothing is
 * charted, below everyone who raised money, only when there was outside spending on them, and its
 * dollars, of every kind and side, order such candidates among themselves. A candidate with
 * neither is left out, and so is the chart when nobody has any. Below the `sm` breakpoint (a
 * phone) the panels are stacked, one above the next, rather than side by side.
 */
function CandidateTotalsChart({ candidates }: { candidates: RaceCandidate[] }) {
  const theme = useChartTheme();
  const { breakpoints } = useMantineTheme();
  // Read on the first render, not after it, so a phone never draws the side-by-side chart first.
  const stacked = useMediaQuery(`(max-width: ${breakpoints.sm})`, undefined, {
    getInitialValueInEffect: false,
  });
  const charted = useMemo(
    () =>
      candidates
        .filter(
          (candidate) =>
            candidateTotal(candidate) > 0 || hasOutsideSpending(candidate.outside_spending),
        )
        .sort(
          (a, b) =>
            candidateTotal(b) - candidateTotal(a) ||
            outsideSpendingVolume(b.outside_spending) - outsideSpendingVolume(a.outside_spending),
        )
        .slice(0, CHARTED),
    [candidates],
  );
  const option = useMemo(
    () => candidateTotalsOption(charted, theme, { stacked }),
    [charted, theme, stacked],
  );
  if (charted.length === 0) return null;
  return (
    <Stack gap={4}>
      <EChart
        option={option}
        style={{ width: "100%", height: candidateTotalsHeight(charted, { stacked }) }}
      />
      {charted.length < candidates.length && (
        <Text size="sm" c="dimmed">
          The {count(charted.length)} candidates who raised the most, of{" "}
          {count(candidates.length)}. The table lists them all.
        </Text>
      )}
    </Stack>
  );
}

export default CandidateTotalsChart;
