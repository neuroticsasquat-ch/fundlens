import { Anchor, Stack, Text, Title } from "@mantine/core";
import { Link, useParams } from "react-router";
import { $api } from "../api/client";
import type { Payee, PayeeCycle, PayeeTopPayer } from "../api/client";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import QueryStatus from "../components/QueryStatus";
import { count, DASH, money } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import CycleHeading from "./CycleHeading";
import CycleTotalsChart from "./CycleTotalsChart";
import type { CycleSeries } from "./cycleTotalsOption";
import { useScrollToHash, useShownCycle } from "./entityCycle";
import NotFound from "./NotFound";

// A `payee_id`: the first 16 hexadecimal characters, lower case, of the SHA-256 of the payee key
// (every-FEC-dollar spec §5.4). Anything else is no payee at all.
const PAYEE_ID = /^[0-9a-f]{16}$/;

const CYCLE_COLUMNS: Column<PayeeCycle>[] = [
  {
    key: "cycle",
    header: "Cycle",
    render: (row) => row.cycle,
    sortValue: (row) => row.cycle,
  },
  {
    key: "committees",
    header: "Committees paying",
    align: "right",
    render: (row) => count(row.committee_count),
    sortValue: (row) => row.committee_count,
  },
  {
    key: "total",
    header: "Paid",
    align: "right",
    render: (row) => money(row.total),
    sortValue: (row) => row.total,
  },
];

const CYCLE_SERIES: CycleSeries<PayeeCycle>[] = [{ name: "Paid", value: (row) => row.total }];

const PAYER_COLUMNS: Column<PayeeTopPayer>[] = [
  {
    key: "rank",
    header: "Rank",
    align: "right",
    render: (payer) => count(payer.rank),
    sortValue: (payer) => payer.rank,
  },
  {
    key: "committee",
    header: "Committee",
    render: (payer) => (
      <Anchor component={Link} to={`/committee/${payer.committee_id}`}>
        {payer.committee_name ?? payer.committee_id}
      </Anchor>
    ),
  },
  {
    // The candidate the committee's payments are credited to; none for a PAC or a party.
    key: "candidate",
    header: "Candidate",
    render: (payer) =>
      payer.candidate_id === null ? (
        DASH
      ) : (
        <Anchor component={Link} to={`/candidate/${payer.candidate_id}`}>
          {payer.candidate_name ?? payer.candidate_id}
        </Anchor>
      ),
  },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    render: (payer) => money(payer.amount),
    sortValue: (payer) => payer.amount,
  },
];

/** `/payee/:payeeId`: what committees paid one payee in every cycle, and who paid it most in one. */
function PayeePage() {
  const raw = useParams().payeeId ?? "";
  if (!PAYEE_ID.test(raw)) return <NotFound />;
  // Keyed, so a table's sort starts over on another payee.
  return <PayeeView key={raw} id={raw} />;
}

function PayeeView({ id }: { id: string }) {
  // Without `cycle`, the API's top payers are its last cycle's, the one the page shows first.
  const payee = $api.useQuery("get", "/v1/payees/{payee_id}", {
    params: { path: { payee_id: id } },
  });
  usePageTitle(payee.data ? payee.data.display_name : "Payee");

  return (
    <Stack gap="lg" py="md">
      <QueryStatus
        query={payee}
        notFound={
          <Stack>
            <Title order={1}>No payee {id}</Title>
            <Text>
              A person, or a name that names nobody such as petty cash, has no payee page.
            </Text>
            <Anchor component={Link} to="/">
              Back to fundlens
            </Anchor>
          </Stack>
        }
      >
        {(data) => <PayeeDetail payee={data} />}
      </QueryStatus>
    </Stack>
  );
}

function PayeeDetail({ payee }: { payee: Payee }) {
  useScrollToHash();
  const cycles = payee.cycles.map((row) => row.cycle);
  const [cycle, showCycle] = useShownCycle(cycles);
  const place = [payee.city, payee.state].filter(Boolean).join(", ");
  const span =
    payee.first_cycle === payee.last_cycle
      ? `in ${payee.first_cycle}`
      : `${payee.first_cycle}–${payee.last_cycle}`;

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={1}>{payee.display_name}</Title>
        <Text c="dimmed">{place || DASH}</Text>
        <Text>
          {money(payee.total_all_cycles)} paid by committees {span}
        </Text>
        <Text size="sm" c="dimmed">
          Grouped by reported payee name; spellings are merged, but different businesses with the
          same name are not told apart.{" "}
          <Anchor component={Link} to="/methodology" inherit>
            Methodology
          </Anchor>
        </Text>
      </Stack>
      <section aria-labelledby="by-cycle">
        <Title order={2} id="by-cycle" mb="sm">
          Totals by cycle
        </Title>
        {payee.cycles.length === 0 ? (
          <Text c="dimmed">No payments to this payee are recorded in any cycle.</Text>
        ) : (
          <Stack gap="md">
            <CycleTotalsChart rows={payee.cycles} series={CYCLE_SERIES} />
            <DataTable
              columns={CYCLE_COLUMNS}
              rows={payee.cycles}
              rowKey={(row) => String(row.cycle)}
              rowProps={(row) => ({ id: `cycle-${row.cycle}` })}
            />
          </Stack>
        )}
      </section>
      {cycle !== undefined && (
        <section aria-labelledby="in-cycle">
          <Stack gap="lg">
            <CycleHeading cycles={cycles} cycle={cycle} onChange={showCycle} />
            <PaidBy payee={payee} cycle={cycle} />
          </Stack>
        </section>
      )}
    </Stack>
  );
}

/**
 * The committees that paid the payee most in `cycle`. The page's own response has its last
 * cycle's; another cycle's is asked for when it is shown.
 */
function PaidBy({ payee, cycle }: { payee: Payee; cycle: number }) {
  const other = $api.useQuery(
    "get",
    "/v1/payees/{payee_id}",
    { params: { path: { payee_id: payee.payee_id }, query: { cycle } } },
    { enabled: cycle !== payee.cycle },
  );
  const table = (payers: PayeeTopPayer[]) => (
    <DataTable
      // Keyed, so the sort starts over in another cycle.
      key={cycle}
      columns={PAYER_COLUMNS}
      rows={payers}
      rowKey={(row) => row.committee_id}
      emptyMessage={`No committee paid this payee in ${cycle}.`}
    />
  );

  return (
    <section aria-labelledby="paid-by">
      <Title order={3} id="paid-by" mb="sm">
        Paid by
      </Title>
      {cycle === payee.cycle ? (
        table(payee.top_payers)
      ) : (
        <QueryStatus query={other}>{(data) => table(data.top_payers)}</QueryStatus>
      )}
    </section>
  );
}

export default PayeePage;
