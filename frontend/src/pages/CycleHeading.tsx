import { Group, Select, Title } from "@mantine/core";

/**
 * The heading over a candidate's or committee's per-cycle sections, with the picker that chooses
 * their cycle (`useShownCycle`).
 */
function CycleHeading({
  cycles,
  cycle,
  onChange,
}: {
  cycles: number[];
  cycle: number;
  onChange: (cycle: number) => void;
}) {
  return (
    <Group justify="space-between" align="flex-end">
      <Title order={2} id="in-cycle">
        In {cycle}
      </Title>
      <Select
        aria-label="Cycle shown"
        data={cycles.map(String)}
        value={String(cycle)}
        onChange={(value) => value && onChange(Number(value))}
        allowDeselect={false}
        w={120}
      />
    </Group>
  );
}

export default CycleHeading;
