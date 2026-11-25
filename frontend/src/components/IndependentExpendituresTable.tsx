import { Anchor, Badge, Group } from "@mantine/core";
import { Link } from "react-router";
import type { IndependentExpenditure, IndependentExpenditurePage } from "../api/client";
import type { IndependentExpendituresQuery } from "../api/contributions";
import type { Column } from "./DataTable";
import PagedTable from "./PagedTable";
import SideBadge from "./SideBadge";
import { DASH, isoDate, money } from "./format";

const COLUMNS: Column<IndependentExpenditure>[] = [
  { key: "date", header: "Date", render: (row) => isoDate(row.date) },
  {
    key: "candidate",
    header: "Candidate",
    // A candidate the filing names who is none of the cycle's has no page: the money is in the
    // spender's total alone.
    render: (row) =>
      row.candidate_id === null ? (
        DASH
      ) : (
        <Anchor component={Link} to={`/candidate/${row.candidate_id}`}>
          {row.candidate_name ?? row.candidate_id}
        </Anchor>
      ),
  },
  {
    key: "side",
    header: "For or against",
    // A 24/48-hour report may name neither side: the money is in the spender's total alone.
    render: (row) => <SideBadge side={row.support_oppose} />,
  },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    // A 24- or 48-hour report's figure stands until a periodic report restates it (every-FEC-dollar
    // spec §6.3), so it is an estimate.
    render: (row) =>
      row.source_file === "ie_24_48" ? (
        <Group gap="xs" justify="flex-end" wrap="nowrap">
          <Badge variant="outline" color="gray" title="Reported on a 24- or 48-hour report">
            24/48-hour estimate
          </Badge>
          {money(row.amount)}
        </Group>
      ) : (
        money(row.amount)
      ),
  },
];

const NOUN = ["independent expenditure", "independent expenditures"] as const;
const expendituresOf = (page: IndependentExpenditurePage) => page.expenditures;

/**
 * A committee's independent expenditures, as filed, a page at a time (`PagedTable`). A row from
 * the 24/48-hour file is marked an estimate from a 24- or 48-hour report.
 */
function IndependentExpendituresTable({
  query,
  emptyMessage,
}: {
  query: IndependentExpendituresQuery;
  emptyMessage: string;
}) {
  return (
    <PagedTable
      query={query}
      rowsOf={expendituresOf}
      rowKey={(row) => row.source_record_id}
      columns={COLUMNS}
      noun={NOUN}
      emptyMessage={emptyMessage}
    />
  );
}

export default IndependentExpendituresTable;
