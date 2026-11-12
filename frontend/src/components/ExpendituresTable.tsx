import { Anchor, Badge } from "@mantine/core";
import { Link } from "react-router";
import type { IndependentExpenditure, IndependentExpenditurePage } from "../api/client";
import type { ExpendituresQuery } from "../api/contributions";
import type { Column } from "./DataTable";
import PagedTable from "./PagedTable";
import { DASH, isoDate, money } from "./format";

const SIDES: Record<IndependentExpenditure["support_oppose"], { label: string; color: string }> = {
  S: { label: "For", color: "teal" },
  O: { label: "Against", color: "orange" },
};

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
    render: (row) => (
      <Badge variant="light" color={SIDES[row.support_oppose].color}>
        {SIDES[row.support_oppose].label}
      </Badge>
    ),
  },
  { key: "amount", header: "Amount", align: "right", render: (row) => money(row.amount) },
];

const NOUN = ["independent expenditure", "independent expenditures"] as const;
const expendituresOf = (page: IndependentExpenditurePage) => page.expenditures;

/** A committee's independent expenditures, as filed, a page at a time (`PagedTable`). */
function ExpendituresTable({
  query,
  emptyMessage,
}: {
  query: ExpendituresQuery;
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

export default ExpendituresTable;
