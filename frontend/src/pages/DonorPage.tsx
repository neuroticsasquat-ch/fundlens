import { Anchor, Button, Group, List, Select, Stack, Text, Title } from "@mantine/core";
import { useMemo, useState } from "react";
import { Link, Navigate, useLocation, useParams, useSearchParams } from "react-router";
import { $api } from "../api/client";
import type { Contribution, Donor, DonorCycle } from "../api/client";
import { CONTRIBUTION_PAGES } from "../api/contributions";
import ContributionsTable from "../components/ContributionsTable";
import {
  amountColumn,
  dateColumn,
  employerColumn,
  notesColumn,
} from "../components/contributionColumns";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import QueryStatus from "../components/QueryStatus";
import { count, DASH, money } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import { donorName } from "../domain/donors";
import { parseCycle } from "../shell/cycleTarget";
import CycleTotalsChart from "./CycleTotalsChart";
import type { CycleSeries } from "./cycleTotalsOption";
import NotFound from "./NotFound";
import { RECIPIENT_COLUMNS } from "./recipientColumns";

// The API's `donor_id`: a positive integer. Anything else is no donor at all.
const DONOR_ID = /^[1-9][0-9]*$/;

const CYCLE_COLUMNS: Column<DonorCycle>[] = [
  {
    key: "cycle",
    header: "Cycle",
    render: (row) => row.cycle,
    sortValue: (row) => row.cycle,
  },
  {
    key: "contributions",
    header: "Contributions",
    align: "right",
    render: (row) => count(row.contribution_count),
    sortValue: (row) => row.contribution_count,
  },
  {
    key: "amount",
    header: "Given",
    align: "right",
    render: (row) => money(row.amount),
    sortValue: (row) => row.amount,
  },
];

const CYCLE_SERIES: CycleSeries<DonorCycle>[] = [{ name: "Given", value: (row) => row.amount }];

// The contributions filter's "every cycle" value; the URL leaves `?cycle=` out for it.
const ALL_CYCLES = "all";

/**
 * A donor's `/contributions` request: every cycle, newest first, or one. The name-variant list and
 * the table ask for every cycle the same way, so they share one cached query.
 */
const contributionsInit = (donor_id: number, cycle?: number) => ({
  params: { path: { donor_id }, query: cycle === undefined ? {} : { cycle } },
});

/** One way the donor's contributions report them, and on how many. */
type ReportedVariant = { label: string; contributions: number };

/**
 * The distinct contributor keys among `rows` (name, ZIP5, employer, occupation; CONTEXT.md),
 * written as reported rather than normalized, most contributions first.
 */
function reportedVariants(rows: Contribution[]): ReportedVariant[] {
  const variants = new Map<string, ReportedVariant>();
  for (const row of rows) {
    const zip5 = row.contributor_zip?.slice(0, 5);
    const label = [
      row.contributor_name ?? DASH,
      row.contributor_employer,
      row.contributor_occupation,
      zip5 && `ZIP ${zip5}`,
    ]
      .filter(Boolean)
      .join(" · ");
    const variant = variants.get(label) ?? { label, contributions: 0 };
    variant.contributions += 1;
    variants.set(label, variant);
  }
  return [...variants.values()].sort(
    (a, b) => b.contributions - a.contributions || a.label.localeCompare(b.label),
  );
}

/** `/donor/:id`: one resolved donor, their money by cycle, whom they gave to, and every gift. */
function DonorPage() {
  const raw = useParams().id ?? "";
  if (!DONOR_ID.test(raw)) return <NotFound />;
  const id = Number(raw);
  // Keyed, so a table's sort and the variant list start over on another donor.
  return <DonorView key={id} id={id} />;
}

function DonorView({ id }: { id: number }) {
  const { search, hash } = useLocation();
  // The API answers a merged donor's old id with a 301 to the id it became, which fetch follows.
  const donor = $api.useQuery("get", "/v1/donors/{donor_id}", {
    params: { path: { donor_id: id } },
  });
  usePageTitle(donor.data ? donorName(donor.data) : "Donor");

  return (
    <Stack gap="lg" py="md">
      <QueryStatus
        query={donor}
        notFound={
          <Stack>
            <Title order={1}>No donor {id}</Title>
            <Anchor component={Link} to="/">
              Back to fundlens
            </Anchor>
          </Stack>
        }
      >
        {(data) =>
          // A followed redirect: show the canonical id in the address bar.
          data.donor_id === id ? (
            <DonorDetail donor={data} />
          ) : (
            <Navigate replace to={{ pathname: `/donor/${data.donor_id}`, search, hash }} />
          )
        }
      </QueryStatus>
    </Stack>
  );
}

function DonorDetail({ donor }: { donor: Donor }) {
  const [search, setSearch] = useSearchParams();
  const cycles = donor.cycles.map((row) => row.cycle);
  const wanted = parseCycle(search.get("cycle") ?? undefined);
  const cycle = wanted !== undefined && cycles.includes(wanted) ? wanted : undefined;
  const showCycle = (value: string) =>
    setSearch(value === ALL_CYCLES ? {} : { cycle: value }, {
      replace: true,
      preventScrollReset: true,
    });

  const place = [donor.city, donor.state].filter(Boolean).join(", ");
  const span =
    donor.first_cycle === donor.last_cycle
      ? `in ${donor.first_cycle}`
      : `${donor.first_cycle}–${donor.last_cycle}`;

  // A recipient's name, from the top-recipient list, for the contributions table.
  const columns = useMemo(() => {
    const names = new Map(
      donor.top_recipients.map((row) => [`${row.recipient_kind}/${row.recipient_id}`, row.name]),
    );
    const recipient: Column<Contribution> = {
      key: "recipient",
      header: "Recipient",
      render: (row) => {
        const to = row.candidate_id
          ? `candidate/${row.candidate_id}`
          : `committee/${row.recipient_committee_id}`;
        return (
          <Anchor component={Link} to={`/${to}`}>
            {names.get(to) ?? row.candidate_id ?? row.recipient_committee_id}
          </Anchor>
        );
      },
    };
    return [
      dateColumn,
      { key: "cycle", header: "Cycle", render: (row: Contribution) => row.cycle },
      recipient,
      {
        key: "reported-as",
        header: "Reported as",
        render: (row: Contribution) => row.contributor_name ?? DASH,
      },
      employerColumn,
      amountColumn,
      notesColumn,
    ];
  }, [donor.top_recipients]);

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={1}>{donorName(donor)}</Title>
        <Text c="dimmed">
          {[donor.employer, donor.occupation, place].filter(Boolean).join(" · ") || DASH}
        </Text>
        <Text>
          {money(donor.total_all_cycles)} given {span}
        </Text>
        <NameVariants donor={donor} />
      </Stack>
      <section aria-labelledby="by-cycle">
        <Title order={2} id="by-cycle" mb="sm">
          Totals by cycle
        </Title>
        {donor.cycles.length === 0 ? (
          <Text c="dimmed">No money is recorded for this donor in any cycle.</Text>
        ) : (
          <Stack gap="md">
            <CycleTotalsChart rows={donor.cycles} series={CYCLE_SERIES} />
            <DataTable
              columns={CYCLE_COLUMNS}
              rows={donor.cycles}
              rowKey={(row) => String(row.cycle)}
            />
          </Stack>
        )}
      </section>
      <section aria-labelledby="top-recipients">
        <Title order={2} id="top-recipients" mb="sm">
          Top recipients
        </Title>
        <DataTable
          columns={RECIPIENT_COLUMNS}
          rows={donor.top_recipients}
          rowKey={(row) => `${row.recipient_kind}-${row.recipient_id}`}
          emptyMessage="No counted contributions to candidates or committees."
        />
      </section>
      <section aria-labelledby="contributions">
        <Group justify="space-between" align="flex-end" mb="sm">
          <Title order={2} id="contributions">
            Contributions
          </Title>
          <Select
            aria-label="Contributions cycle"
            data={[
              { value: ALL_CYCLES, label: "All cycles" },
              ...cycles.map((c) => ({ value: String(c), label: String(c) })),
            ]}
            value={cycle === undefined ? ALL_CYCLES : String(cycle)}
            onChange={(value) => value && showCycle(value)}
            allowDeselect={false}
            w={140}
          />
        </Group>
        <DonorContributions
          // Keyed, so another cycle's pages start from the first.
          key={cycle ?? ALL_CYCLES}
          id={donor.donor_id}
          cycle={cycle}
          columns={columns}
        />
      </section>
    </Stack>
  );
}

/**
 * "Appears under N name variants" (gold's contributor-key count), and a disclosure listing how
 * the contributions loaded so far write the donor. It asks for them only once opened.
 */
function NameVariants({ donor }: { donor: Donor }) {
  const [opened, setOpened] = useState(false);
  const contributions = $api.useInfiniteQuery(
    "get",
    "/v1/donors/{donor_id}/contributions",
    contributionsInit(donor.donor_id),
    { ...CONTRIBUTION_PAGES, enabled: opened },
  );
  const rows = contributions.data?.pages.flatMap((page) => page.contributions) ?? [];
  const variants = reportedVariants(rows);
  const n = donor.contributor_key_count;

  return (
    <Stack gap={4} align="flex-start">
      <Group gap="xs">
        <Text>
          Appears under {count(n)} name {n === 1 ? "variant" : "variants"}
        </Text>
        <Button
          variant="subtle"
          size="compact-sm"
          aria-expanded={opened}
          aria-controls="name-variants"
          onClick={() => setOpened((open) => !open)}
        >
          {opened ? "Hide" : "Show as reported"}
        </Button>
      </Group>
      {opened && (
        <Stack gap={4} id="name-variants">
          <QueryStatus query={contributions}>
            {() => (
              <>
                <List size="sm" aria-label="Name variants as reported">
                  {variants.map((variant) => (
                    <List.Item key={variant.label}>
                      {variant.label}{" "}
                      <Text span c="dimmed" size="sm">
                        ({count(variant.contributions)})
                      </Text>
                    </List.Item>
                  ))}
                </List>
                <Text size="xs" c="dimmed">
                  As written on {contributions.hasNextPage ? "the newest " : ""}
                  {count(rows.length)} {rows.length === 1 ? "contribution" : "contributions"};
                  spellings that normalize alike, such as a comma or a suffix, are one variant.
                </Text>
              </>
            )}
          </QueryStatus>
        </Stack>
      )}
    </Stack>
  );
}

function DonorContributions({
  id,
  cycle,
  columns,
}: {
  id: number;
  cycle: number | undefined;
  columns: Column<Contribution>[];
}) {
  const contributions = $api.useInfiniteQuery(
    "get",
    "/v1/donors/{donor_id}/contributions",
    contributionsInit(id, cycle),
    CONTRIBUTION_PAGES,
  );
  return (
    <ContributionsTable
      query={contributions}
      columns={columns}
      emptyMessage={
        cycle === undefined
          ? "No itemized contributions from this donor."
          : `No itemized contributions from this donor in ${cycle}.`
      }
    />
  );
}

export default DonorPage;
