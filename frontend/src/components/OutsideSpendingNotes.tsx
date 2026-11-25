import { Anchor, Stack, Text } from "@mantine/core";
import { Link } from "react-router";
import type { OutsideSpendingKind } from "../api/client";
import { OUTSIDE_SPENDING_KINDS } from "../domain/outsideSpending";

/**
 * A line saying what each of `kinds` is, and where the methodology says how they are counted:
 * under a table of outside spending, for the kinds it shows.
 */
function OutsideSpendingNotes({ kinds }: { kinds: OutsideSpendingKind[] }) {
  return (
    <Stack gap={4}>
      {kinds.map((kind) => (
        <Text key={kind} c="dimmed" size="sm">
          {OUTSIDE_SPENDING_KINDS[kind].label}: {OUTSIDE_SPENDING_KINDS[kind].explanation}
        </Text>
      ))}
      <Text c="dimmed" size="sm">
        Outside spending is others&apos; money, never in what a candidate raised. The{" "}
        <Anchor component={Link} to="/methodology" inherit>
          methodology
        </Anchor>{" "}
        says where each kind comes from and how it is counted.
      </Text>
    </Stack>
  );
}

export default OutsideSpendingNotes;
