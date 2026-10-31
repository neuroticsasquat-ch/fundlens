import { Anchor } from "@mantine/core";
import { Link } from "react-router";
import { $api } from "../api/client";

/** The current cycle's race index, once `/v1/cycles` has said which cycle that is. */
function RacesLink({ onClick }: { onClick?: () => void }) {
  const cycles = $api.useQuery("get", "/v1/cycles");
  const current = cycles.data?.[0]?.cycle;
  if (current === undefined) return null;
  return (
    <Anchor component={Link} to={`/cycles/${current}`} onClick={onClick}>
      Races
    </Anchor>
  );
}

export default RacesLink;
