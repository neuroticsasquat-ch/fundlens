import { Stack, Text } from "@mantine/core";
import { useMemo } from "react";
import type { RaceCandidate } from "../api/client";
import EChart from "../components/charts/EChart";
import { useChartTheme } from "../components/charts/theme";
import { count } from "../components/format";
import { candidateTotal } from "../domain/candidates";
import { candidateTotalsHeight, candidateTotalsOption } from "./candidateTotalsOption";

// The most bars charted. A presidential race lists every filer (1,602 in 2024, most with nothing),
// and a bar each would make a canvas taller than the browser will draw.
const CHARTED = 15;

const independentExpenditures = (candidate: RaceCandidate) =>
  candidate.ie_support + candidate.ie_oppose;

/**
 * The race split: the candidates who raised the most, most first rather than in the API's order,
 * each a bar of what they raised, coloured by party, with the independent expenditures for and
 * against them in a panel beside it. Others' spending never orders them: a candidate who raised
 * nothing is charted, below everyone who raised money, only when there were independent
 * expenditures for or against them, and those order such candidates among themselves. A candidate
 * with neither is left out, and so is the chart when nobody has any.
 */
function CandidateTotalsChart({ candidates }: { candidates: RaceCandidate[] }) {
  const theme = useChartTheme();
  const charted = useMemo(
    () =>
      candidates
        .filter(
          (candidate) =>
            candidateTotal(candidate) > 0 || candidate.ie_support > 0 || candidate.ie_oppose > 0,
        )
        .sort(
          (a, b) =>
            candidateTotal(b) - candidateTotal(a) ||
            independentExpenditures(b) - independentExpenditures(a),
        )
        .slice(0, CHARTED),
    [candidates],
  );
  const option = useMemo(() => candidateTotalsOption(charted, theme), [charted, theme]);
  if (charted.length === 0) return null;
  return (
    <Stack gap={4}>
      <EChart option={option} style={{ width: "100%", height: candidateTotalsHeight(charted) }} />
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
