import { Badge } from "@mantine/core";
import { DASH } from "./format";

const SIDES = {
  S: { label: "For", color: "teal" },
  O: { label: "Against", color: "orange" },
} as const;

/**
 * Whether outside spending was for a candidate or against them, as a badge; a dash where it names
 * neither, as an electioneering communication and some 24/48-hour rows do.
 */
function SideBadge({ side }: { side: "S" | "O" | null }) {
  if (side === null) return DASH;
  return (
    <Badge variant="light" color={SIDES[side].color}>
      {SIDES[side].label}
    </Badge>
  );
}

export default SideBadge;
