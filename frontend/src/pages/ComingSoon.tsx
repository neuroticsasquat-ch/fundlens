import { Anchor, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router";
import { usePageTitle } from "../components/usePageTitle";

/** A route whose page has not been built yet: says so, rather than pretending it is not there. */
function ComingSoon({ name }: { name: string }) {
  usePageTitle(name);
  return (
    <Stack>
      <Title order={1}>{name}</Title>
      <Text>{name} pages are coming.</Text>
      <Anchor component={Link} to="/">
        Back to fundlens
      </Anchor>
    </Stack>
  );
}

export default ComingSoon;
