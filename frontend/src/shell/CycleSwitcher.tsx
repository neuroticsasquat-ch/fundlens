import { Select } from "@mantine/core";
import { useNavigate } from "react-router";
import { $api } from "../api/client";
import { useCycleTarget } from "./cycleTarget";

/** Picks a cycle and goes to the same page for it, where the route says what that is. */
function CycleSwitcher({ onPick }: { onPick?: () => void }) {
  const cycles = $api.useQuery("get", "/v1/cycles");
  const { cycle, target } = useCycleTarget();
  const navigate = useNavigate();
  const shown = cycle ?? cycles.data?.[0]?.cycle;

  return (
    <Select
      aria-label="Cycle"
      w={96}
      data={(cycles.data ?? []).map((c) => String(c.cycle))}
      value={shown === undefined ? null : String(shown)}
      allowDeselect={false}
      disabled={!cycles.data}
      onChange={(value) => {
        if (value === null) return;
        navigate(target(Number(value)));
        onPick?.();
      }}
    />
  );
}

export default CycleSwitcher;
