import { Anchor, Stack, Text, Title } from "@mantine/core";
import { Link, useLocation } from "react-router";
import { usePageTitle } from "../components/usePageTitle";

function NotFound() {
  const { pathname } = useLocation();
  usePageTitle("Not found");
  return (
    <Stack>
      <Title order={1}>Not found</Title>
      <Text>There is no page at {pathname}.</Text>
      <Anchor component={Link} to="/">
        Back to fundlens
      </Anchor>
    </Stack>
  );
}

export default NotFound;
