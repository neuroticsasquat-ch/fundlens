import { Stack, Text } from "@mantine/core";
import { useMemo } from "react";
import type { GiftSize } from "../api/client";
import EChart from "../components/charts/EChart";
import { useChartTheme } from "../components/charts/theme";
import { giftSizeOption } from "./giftSizeOption";

/**
 * A candidate's money in a cycle by gift size, each donor's net gifts to the candidate, with
 * FEC's unitemized lump as a bar of its own. Says so instead when the cycle has no bucket, and
 * notes when a candidate with individuals' money has only the lump: a build loaded before donors
 * were resolved (spec §4.6).
 */
function GiftSizeChart({
  sizes,
  cycle,
  totalIndividual,
}: {
  sizes: GiftSize[];
  cycle: number;
  totalIndividual: number;
}) {
  const theme = useChartTheme();
  const option = useMemo(() => giftSizeOption(sizes, theme), [sizes, theme]);
  if (sizes.length === 0) {
    return <Text c="dimmed">No gift sizes in {cycle}.</Text>;
  }
  const itemized = sizes.some((size) => size.bucket !== "unitemized");
  return (
    <Stack gap={4}>
      <EChart option={option} style={{ width: "100%", height: 280 }} />
      <Text size="sm" c="dimmed">
        A donor&apos;s gift size is everything they gave the candidate in {cycle}, refunds taken
        off, so twenty $50 gifts make one $1,000 donor. Unitemized is the money the campaign
        reported as one lump, from givers it did not have to name; it is no donor&apos;s.
      </Text>
      {!itemized && totalIndividual !== 0 && (
        <Text size="sm" c="dimmed">
          No donors are resolved for {cycle} yet, so only the unitemized lump is shown.
        </Text>
      )}
    </Stack>
  );
}

export default GiftSizeChart;
