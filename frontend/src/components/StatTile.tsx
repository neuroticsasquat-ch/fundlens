import { Paper, Text } from "@mantine/core";
import { Link } from "react-router";

/** One headline figure, linking to where it is broken down. `title` is the exact figure. */
function StatTile({
  label,
  value,
  title,
  to,
}: {
  label: string;
  value: string;
  title?: string;
  to: string;
}) {
  return (
    <Paper
      component={Link}
      to={to}
      withBorder
      p="md"
      // A link, so the browser would colour the figure as one.
      style={{ color: "inherit", textDecoration: "none" }}
    >
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Text size="xl" fw={700} title={title} style={{ fontVariantNumeric: "tabular-nums" }}>
        {value}
      </Text>
    </Paper>
  );
}

export default StatTile;
