import { Anchor, Select, Stack, Text, Title } from "@mantine/core";
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import { $api } from "../api/client";
import type { Office, RaceSummary } from "../api/client";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import QueryStatus from "../components/QueryStatus";
import { count, money, moneyCompact } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import { officeLabel, raceLabel, stateName } from "../domain/states";
import { raceRoute } from "../search/target";
import { parseCycle } from "../shell/cycleTarget";
import NotFound from "./NotFound";

const SECTIONS: { office: Office; anchor: string }[] = [
  { office: "P", anchor: "president" },
  { office: "S", anchor: "senate" },
  { office: "H", anchor: "house" },
];

const total = (race: RaceSummary) => race.total_individual + race.total_committee;

const COLUMNS: Column<RaceSummary>[] = [
  {
    key: "race",
    header: "Race",
    render: (race) => (
      // Dimmed with its row: nobody is running in it.
      <Anchor
        component={Link}
        to={raceRoute(race.slug)}
        c={race.candidate_count === 0 ? "dimmed" : undefined}
      >
        {raceLabel(race)}
      </Anchor>
    ),
  },
  {
    key: "candidates",
    header: "Candidates",
    align: "right",
    render: (race) => count(race.candidate_count),
  },
  {
    key: "individual",
    header: "From individuals",
    align: "right",
    render: (race) => money(race.total_individual),
    sortValue: (race) => race.total_individual,
  },
  {
    key: "committee",
    header: "From committees",
    align: "right",
    render: (race) => money(race.total_committee),
    sortValue: (race) => race.total_committee,
  },
  {
    key: "total",
    header: "Total",
    align: "right",
    render: (race) => money(total(race)),
    sortValue: total,
  },
];

/** `/cycles/:cycle`: every race in the cycle, by office, then state and district. */
function CyclePage() {
  const cycle = parseCycle(useParams().cycle);
  if (cycle === undefined) return <NotFound />;
  // Keyed, so the state filter starts over in another cycle.
  return <CycleIndex key={cycle} cycle={cycle} />;
}

function CycleIndex({ cycle }: { cycle: number }) {
  usePageTitle(`${cycle} races`);
  const races = $api.useQuery("get", "/v1/cycles/{cycle}/races", {
    params: { path: { cycle } },
  });
  const summary = $api.useQuery("get", "/v1/cycles").data?.find((c) => c.cycle === cycle);
  const [state, setState] = useState<string | null>(null);
  const { hash } = useLocation();

  // The sections are not on the page until the races arrive, so the browser cannot scroll to
  // `#senate` by itself.
  useEffect(() => {
    if (races.data && hash) document.getElementById(hash.slice(1))?.scrollIntoView();
  }, [races.data, hash]);

  return (
    <Stack gap="lg" py="md">
      <Stack gap={4}>
        <Title order={1}>{cycle} races</Title>
        {summary && (
          <Text c="dimmed">
            {count(summary.race_count)} races · {moneyCompact(summary.total_amount)} raised
          </Text>
        )}
      </Stack>
      <QueryStatus
        query={races}
        notFound={
          <Stack>
            <Text>No {cycle} cycle.</Text>
            <Anchor component={Link} to="/">
              Back to fundlens
            </Anchor>
          </Stack>
        }
      >
        {(rows) => {
          const states = [...new Set(rows.map((r) => r.state).filter((s) => s !== "US"))]
            .map((code) => ({ value: code, label: stateName(code) }))
            .sort((a, b) => a.label.localeCompare(b.label));
          return (
            <Stack gap="lg">
              <Select
                aria-label="State"
                w={240}
                data={[{ value: "", label: "All states" }, ...states]}
                value={state ?? ""}
                allowDeselect={false}
                onChange={(value) => setState(value || null)}
              />
              {SECTIONS.map(({ office, anchor }) => {
                const inOffice = rows.filter((r) => r.office === office);
                if (inOffice.length === 0) return null;
                // President is the whole country's race, never one state's.
                const shown =
                  state === null || office === "P"
                    ? inOffice
                    : inOffice.filter((r) => r.state === state);
                return (
                  <section key={office} aria-labelledby={anchor}>
                    <Title order={2} id={anchor} mb="sm">
                      {officeLabel(office)}
                    </Title>
                    <DataTable
                      columns={COLUMNS}
                      rows={shown}
                      rowKey={(r) => r.race_id}
                      rowProps={(r) => (r.candidate_count === 0 ? { c: "dimmed" } : {})}
                      emptyMessage={`No ${officeLabel(office)} races in ${stateName(state ?? "")}.`}
                    />
                  </section>
                );
              })}
            </Stack>
          );
        }}
      </QueryStatus>
    </Stack>
  );
}

export default CyclePage;
