import { Anchor, Badge, Group, Stack, Tabs, Text, Title } from "@mantine/core";
import { useMemo } from "react";
import { Link, useParams } from "react-router";
import { $api } from "../api/client";
import type { Committee, CommitteeCycle, TopOrganization } from "../api/client";
import { CONTRIBUTION_PAGES, EXPENDITURE_PAGES } from "../api/contributions";
import ContributionsTable from "../components/ContributionsTable";
import DataTable from "../components/DataTable";
import ExpendituresTable from "../components/ExpendituresTable";
import type { Column } from "../components/DataTable";
import QueryStatus from "../components/QueryStatus";
import TopDonorsTable from "../components/TopDonorsTable";
import { count, money } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import { committeeDesignation, committeeType } from "../domain/committees";
import { partyColour } from "../theme";
import CycleHeading from "./CycleHeading";
import CycleTotalsChart from "./CycleTotalsChart";
import type { CycleSeries } from "./cycleTotalsOption";
import { useScrollToHash, useShownCycle } from "./entityCycle";
import { RECIPIENT_COLUMNS } from "./recipientColumns";

const ORGANIZATIONS_COLUMN: Column<CommitteeCycle> = {
  key: "organizations",
  header: "From organizations",
  align: "right",
  render: (row) => money(row.total_from_organizations),
  sortValue: (row) => row.total_from_organizations,
};

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

const ORGANIZATIONS_SERIES: CycleSeries<CommitteeCycle> = {
  name: "From organizations",
  value: (row) => row.total_from_organizations,
};

const NON_CONTRIBUTION_ACCOUNT_COLUMN: Column<CommitteeCycle> = {
  key: "non-contribution-account",
  header: "Non-contribution account",
  align: "right",
  render: (row) => money(row.total_non_contribution_account),
  sortValue: (row) => row.total_non_contribution_account,
};

const NON_CONTRIBUTION_ACCOUNT_SERIES: CycleSeries<CommitteeCycle> = {
  name: "Non-contribution account",
  value: (row) => row.total_non_contribution_account,
};

// Spending for or against candidates, never given to them, so a column after "To candidates" and in
// no bar of the chart, which stacks what the committee received.
const INDEPENDENT_EXPENDITURES_COLUMN: Column<CommitteeCycle> = {
  key: "independent-expenditures",
  header: "Independent expenditures",
  align: "right",
  render: (row) => money(row.ie_total),
  sortValue: (row) => row.ie_total,
};

/**
 * The table's columns and the chart's series, with organizations' money and a hybrid PAC's
 * non-contribution account after "From committees" when the committee has any, and its
 * independent expenditures last when it made any.
 */
function cycleTotals(
  fromOrganizations: boolean,
  nonContributionAccount: boolean,
  independentExpenditures: boolean,
) {
  const columns = [
    ...(fromOrganizations ? [ORGANIZATIONS_COLUMN] : []),
    ...(nonContributionAccount ? [NON_CONTRIBUTION_ACCOUNT_COLUMN] : []),
  ];
  const series = [
    ...(fromOrganizations ? [ORGANIZATIONS_SERIES] : []),
    ...(nonContributionAccount ? [NON_CONTRIBUTION_ACCOUNT_SERIES] : []),
  ];
  return {
    columns: [
      ...CYCLE_COLUMNS.slice(0, 3),
      ...columns,
      ...CYCLE_COLUMNS.slice(3),
      ...(independentExpenditures ? [INDEPENDENT_EXPENDITURES_COLUMN] : []),
    ],
    series: [...CYCLE_SERIES.slice(0, 2), ...series, ...CYCLE_SERIES.slice(2)],
  };
}

const ORGANIZATION_COLUMNS: Column<TopOrganization>[] = [
  {
    key: "rank",
    header: "Rank",
    align: "right",
    render: (organization) => count(organization.rank),
    sortValue: (organization) => organization.rank,
  },
  // Plain text: an organization is grouped by name, not resolved, so it has no page (ADR-0011).
  { key: "organization", header: "Organization", render: (organization) => organization.name },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    render: (organization) => money(organization.amount),
    sortValue: (organization) => organization.amount,
  },
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
  // Most committees take nothing from organizations; theirs is a column of zeros left out.
  const fromOrganizations = committee.cycles.some((row) => row.total_from_organizations !== 0);
  // Only a hybrid PAC has a non-contribution account; every other committee's is 0.
  const nonContributionAccount = committee.cycles.some(
    (row) => row.total_non_contribution_account !== 0,
  );
  // Most committees spend nothing independently of a campaign; a super PAC mostly does that.
  const independentExpenditures = committee.cycles.some((row) => row.ie_total !== 0);
  // Memoized, so the chart's option is not rebuilt on every render.
  const totals = useMemo(
    () => cycleTotals(fromOrganizations, nonContributionAccount, independentExpenditures),
    [fromOrganizations, nonContributionAccount, independentExpenditures],
  );

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
            <CycleTotalsChart rows={committee.cycles} series={totals.series} />
            <DataTable
              columns={totals.columns}
              rows={committee.cycles}
              rowKey={(row) => String(row.cycle)}
              rowProps={(row) => ({ id: `cycle-${row.cycle}` })}
            />
            {nonContributionAccount && (
              <Text c="dimmed" size="sm">
                Non-contribution account: what individuals and organizations give a hybrid PAC
                outside its contribution account, without limit, and counted in no other column.
              </Text>
            )}
            {independentExpenditures && (
              <Text c="dimmed" size="sm">
                Independent expenditures: what the committee spent for or against candidates
                without coordinating with them, for and against together. It is never a
                contribution to them.
              </Text>
            )}
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
            {shown.top_organizations.length > 0 && (
              <section aria-labelledby="top-organizations">
                <Title order={3} id="top-organizations">
                  Top organizations
                </Title>
                <Text c="dimmed" size="sm" mb="sm">
                  Grouped by reported name; not resolved like individual donors.{" "}
                  <Anchor component={Link} to="/methodology">
                    Methodology
                  </Anchor>
                </Text>
                <DataTable
                  key={shown.cycle}
                  columns={ORGANIZATION_COLUMNS}
                  rows={shown.top_organizations}
                  rowKey={(organization) => organization.organization_key}
                />
              </section>
            )}
            {/* The tab is shown by the cycle's net ie_total, which the page already has: a cycle
                whose expenditures net to exactly $0, a correction cancelling a filing, has none. */}
            {shown.ie_total === 0 ? (
              <section aria-labelledby="contributions">
                <Title order={3} id="contributions" mb="sm">
                  Contributions received
                </Title>
                <CommitteeContributions id={committee.committee_id} cycle={shown.cycle} />
              </section>
            ) : (
              <section aria-labelledby="itemized">
                <Title order={3} id="itemized" mb="sm">
                  Itemized
                </Title>
                {/* Not kept mounted: a tab asks the API for its rows only once opened. */}
                <Tabs defaultValue="contributions" keepMounted={false}>
                  <Tabs.List>
                    <Tabs.Tab value="contributions">Contributions received</Tabs.Tab>
                    <Tabs.Tab value="expenditures">Independent expenditures</Tabs.Tab>
                  </Tabs.List>
                  <Tabs.Panel value="contributions" pt="md">
                    <CommitteeContributions id={committee.committee_id} cycle={shown.cycle} />
                  </Tabs.Panel>
                  <Tabs.Panel value="expenditures" pt="md">
                    <CommitteeExpenditures id={committee.committee_id} cycle={shown.cycle} />
                  </Tabs.Panel>
                </Tabs>
              </section>
            )}
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

function CommitteeExpenditures({ id, cycle }: { id: string; cycle: number }) {
  const expenditures = $api.useInfiniteQuery(
    "get",
    "/v1/committees/{committee_id}/expenditures",
    { params: { path: { committee_id: id }, query: { cycle } } },
    EXPENDITURE_PAGES,
  );
  return (
    <ExpendituresTable
      query={expenditures}
      emptyMessage={`No independent expenditures by this committee in ${cycle}.`}
    />
  );
}

export default CommitteePage;
