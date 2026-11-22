import { Anchor, Badge, Group, Stack, Text, Title } from "@mantine/core";
import { Link, useSearchParams } from "react-router";
import { $api } from "../api/client";
import QueryStatus from "../components/QueryStatus";
import { usePageTitle } from "../components/usePageTitle";
import { MIN_QUERY } from "../search/SearchBox";
import { groupByKind, searchAliases, searchTarget } from "../search/target";

/** `/search?q=`: every hit for a query, grouped by kind, at a URL that can be shared. */
function SearchPage() {
  const q = (useSearchParams()[0].get("q") ?? "").trim();
  usePageTitle(`Search: ${q}`);
  const search = $api.useQuery(
    "get",
    "/v1/search",
    { params: { query: { q } } },
    { enabled: q.length >= MIN_QUERY },
  );

  return (
    <Stack gap="lg" py="md">
      <Title order={1}>Search: {q}</Title>
      {q.length < MIN_QUERY ? (
        <Text>Type at least two characters to search.</Text>
      ) : (
        <QueryStatus query={search}>
          {(results) =>
            results.length === 0 ? (
              <Text>No results for ‘{q}’.</Text>
            ) : (
              groupByKind(results).map((group) => (
                <section key={group.kind} aria-labelledby={`results-${group.kind}`}>
                  <Title order={2} id={`results-${group.kind}`} mb="sm">
                    {group.label}
                  </Title>
                  <Stack gap="xs" component="ul" style={{ listStyle: "none", padding: 0 }}>
                    {group.hits.map(({ result }) => {
                      const aliases = searchAliases(result);
                      return (
                        <li key={`${result.kind}:${result.id}`}>
                          <Group gap="xs" wrap="nowrap">
                            <Anchor component={Link} to={searchTarget(result)}>
                              {result.name}
                            </Anchor>
                            <Badge size="sm" variant="light">
                              {result.kind}
                            </Badge>
                          </Group>
                          {aliases && (
                            <Text size="sm" c="dimmed">
                              {aliases}
                            </Text>
                          )}
                        </li>
                      );
                    })}
                  </Stack>
                </section>
              ))
            )
          }
        </QueryStatus>
      )}
    </Stack>
  );
}

export default SearchPage;
