import { Anchor, Card, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router";
import { $api } from "../api/client";
import QueryStatus from "../components/QueryStatus";
import StatTile from "../components/StatTile";
import { count, isoDate, money, moneyCompact } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import SearchBox from "../search/SearchBox";

const OFFICES = [
  { anchor: "president", name: "President" },
  { anchor: "senate", name: "Senate" },
  { anchor: "house", name: "House" },
];

/** The front door: what fundlens is, a search box, and the current cycle at a glance. */
function HomePage() {
  usePageTitle();
  const cycles = $api.useQuery("get", "/v1/cycles");
  const meta = $api.useQuery("get", "/v1/meta");

  return (
    <Stack gap="xl" py="md">
      <Stack gap="xs">
        <Title order={1}>Who funds federal races.</Title>
        <Text c="dimmed" maw={720}>
          Donor, candidate and committee money for every federal race since 1980, with donors
          resolved across name, employer and address variants.
        </Text>
      </Stack>
      <SearchBox size="lg" autoFocus />
      <QueryStatus query={cycles}>
        {([current, ...earlier]) =>
          current === undefined ? (
            <Text>No cycles are published yet.</Text>
          ) : (
            <Stack gap="lg">
              <Stack gap="xs">
                <Text size="sm" c="dimmed">
                  {current.cycle} cycle
                  {meta.data && ` · data as of ${isoDate(meta.data.published_at)}`}
                </Text>
                <SimpleGrid cols={{ base: 1, sm: 3 }}>
                  <StatTile
                    label="Races"
                    value={count(current.race_count)}
                    to={`/cycles/${current.cycle}`}
                  />
                  <StatTile
                    label="Contributions counted"
                    value={count(current.contribution_count)}
                    to={`/cycles/${current.cycle}`}
                  />
                  <StatTile
                    label="Raised"
                    value={moneyCompact(current.total_amount)}
                    title={money(current.total_amount)}
                    to={`/cycles/${current.cycle}`}
                  />
                </SimpleGrid>
              </Stack>
              <SimpleGrid cols={{ base: 1, sm: 3 }}>
                {OFFICES.map(({ anchor, name }) => (
                  <Card
                    key={anchor}
                    component={Link}
                    to={`/cycles/${current.cycle}#${anchor}`}
                    withBorder
                    style={{ color: "inherit", textDecoration: "none" }}
                  >
                    <Title order={3}>{name}</Title>
                    <Text size="sm" c="dimmed">
                      Every {name} race in {current.cycle}
                    </Text>
                  </Card>
                ))}
              </SimpleGrid>
              {earlier.length > 0 && (
                <Group gap="xs">
                  <Text size="sm">Earlier cycles:</Text>
                  {earlier.map(({ cycle }) => (
                    <Anchor key={cycle} component={Link} to={`/cycles/${cycle}`} size="sm">
                      {cycle}
                    </Anchor>
                  ))}
                </Group>
              )}
            </Stack>
          )
        }
      </QueryStatus>
    </Stack>
  );
}

export default HomePage;
