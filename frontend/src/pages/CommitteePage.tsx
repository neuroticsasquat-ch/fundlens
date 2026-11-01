import { Anchor, Badge, Group, Stack, Text, Title } from "@mantine/core";
import { Link, useParams } from "react-router";
import { $api } from "../api/client";
import type { Committee, CommitteeCycle } from "../api/client";
import { CONTRIBUTION_PAGES } from "../api/contributions";
import ContributionsTable from "../components/ContributionsTable";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import QueryStatus from "../components/QueryStatus";
import TopDonorsTable from "../components/TopDonorsTable";
import { money } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import { committeeDesignation, committeeType } from "../domain/committees";
import { partyColour } from "../theme";
import CycleHeading from "./CycleHeading";
import CycleTotalsChart from "./CycleTotalsChart";
import type { CycleSeries } from "./cycleTotalsOption";
import { useScrollToHash, useShownCycle } from "./entityCycle";
import { RECIPIENT_COLUMNS } from "./recipientColumns";

const CYCLE_COLUMNS: Column<CommitteeCycle>[] = [
  {
    key: "cycle",
    header: "Cycle",
    render: (row) => row.cycle,
    sortValue: (row) => row.cycle,
  },
  {
    key: "individual",
    header: "From individuals",
    align: "right",
    render: (row) => money(row.total_individual),
    sortValue: (row) => row.total_individual,
  },
  {
    key: "committees",
    header: "From committees",
    align: "right",
    render: (row) => money(row.total_from_committees),
    sortValue: (row) => row.total_from_committees,
  },
  {
    key: "self",
    header: "Self-funding",
    align: "right",
    render: (row) => money(row.self_funding),
    sortValue: (row) => row.self_funding,
  },
  {
    key: "to-candidates",
    header: "To candidates",
    align: "right",
    render: (row) => money(row.total_to_candidates),
    sortValue: (row) => row.total_to_candidates,
  },
];

const CYCLE_SERIES: CycleSeries<CommitteeCycle>[] = [
  { name: "From individuals", value: (row) => row.total_individual },
  { name: "From committees", value: (row) => row.total_from_committees },
  { name: "Self-funding", value: (row) => row.self_funding },
];

/** `/committee/:id`: a committee's money in every cycle; whom it gave to and got from in one. */
function CommitteePage() {
  const id = useParams().id ?? "";
  // Keyed, so a table's sort starts over on another committee.
  return <CommitteeView key={id} id={id} />;
}

function CommitteeView({ id }: { id: string }) {
  const committee = $api.useQuery("get", "/v1/committees/{committee_id}", {
    params: { path: { committee_id: id } },
  });
  usePageTitle(committee.data ? (committee.data.name ?? id) : "Committee");

  return (
    <Stack gap="lg" py="md">
      <QueryStatus
        query={committee}
        notFound={
          <Stack>
            <Title order={1}>No committee {id}</Title>
            <Anchor component={Link} to="/">
              Back to fundlens
            </Anchor>
          </Stack>
        }
      >
        {(data) => <CommitteeDetail committee={data} />}
      </QueryStatus>
    </Stack>
  );
}

function CommitteeDetail({ committee }: { committee: Committee }) {
  useScrollToHash();
  const cycles = committee.cycles.map((row) => row.cycle);
  const [cycle, showCycle] = useShownCycle(cycles);
  const shown = committee.cycles.find((row) => row.cycle === cycle);
  const kind = [committeeType(committee.type), committeeDesignation(committee.designation)];

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Group gap="sm">
          <Title order={1}>{committee.name ?? committee.committee_id}</Title>
          {committee.party && (
            <Badge size="lg" variant="light" color={partyColour(committee.party)}>
              {committee.party}
            </Badge>
          )}
          {committee.is_conduit && <Badge size="lg">Conduit</Badge>}
        </Group>
        <Text c="dimmed">
          {[...kind, `FEC ${committee.committee_id}`].filter(Boolean).join(" · ")}
        </Text>
        {committee.connected_org && (
          <Text c="dimmed">Connected organization: {committee.connected_org}</Text>
        )}
        {committee.is_conduit && (
          <Text>
            A conduit forwards earmarked contributions to the committees they were meant for.
            fundlens counts each earmark once, at its recipient, so a conduit receives nothing
            here.
          </Text>
        )}
      </Stack>
      <section aria-labelledby="by-cycle">
        <Title order={2} id="by-cycle" mb="sm">
          Totals by cycle
        </Title>
        {committee.cycles.length === 0 ? (
          <Text c="dimmed">No money is recorded for this committee in any cycle.</Text>
        ) : (
          <Stack gap="md">
            <CycleTotalsChart rows={committee.cycles} series={CYCLE_SERIES} />
            <DataTable
              columns={CYCLE_COLUMNS}
              rows={committee.cycles}
              rowKey={(row) => String(row.cycle)}
              rowProps={(row) => ({ id: `cycle-${row.cycle}` })}
            />
          </Stack>
        )}
      </section>
      {shown && (
        <section aria-labelledby="in-cycle">
          <Stack gap="lg">
            <CycleHeading cycles={cycles} cycle={shown.cycle} onChange={showCycle} />
            <section aria-labelledby="top-recipients">
              <Title order={3} id="top-recipients" mb="sm">
                Top recipients
              </Title>
              <DataTable
                // Keyed, so the sort starts over in another cycle.
                key={shown.cycle}
                columns={RECIPIENT_COLUMNS}
                rows={shown.top_recipients}
                rowKey={(row) => `${row.recipient_kind}-${row.recipient_id}`}
                emptyMessage={`No contributions to candidates or committees in ${shown.cycle}.`}
              />
            </section>
            <section aria-labelledby="top-donors">
              <Title order={3} id="top-donors" mb="sm">
                Top donors
              </Title>
              <TopDonorsTable
                key={shown.cycle}
                rows={shown.top_donors}
                emptyMessage={`No resolved individual donors in ${shown.cycle}.`}
              />
            </section>
            <section aria-labelledby="contributions">
              <Title order={3} id="contributions" mb="sm">
                Contributions received
              </Title>
              <CommitteeContributions id={committee.committee_id} cycle={shown.cycle} />
            </section>
          </Stack>
        </section>
      )}
    </Stack>
  );
}

function CommitteeContributions({ id, cycle }: { id: string; cycle: number }) {
  const contributions = $api.useInfiniteQuery(
    "get",
    "/v1/committees/{committee_id}/contributions",
    { params: { path: { committee_id: id }, query: { cycle } } },
    CONTRIBUTION_PAGES,
  );
  return (
    <ContributionsTable
      query={contributions}
      emptyMessage={`No itemized contributions to this committee in ${cycle}.`}
    />
  );
}

export default CommitteePage;
