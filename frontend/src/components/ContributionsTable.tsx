import { Anchor } from "@mantine/core";
import { Link } from "react-router";
import type { Contribution, ContributionPage } from "../api/client";
import type { ContributionsQuery } from "../api/contributions";
import type { Column } from "./DataTable";
import PagedTable from "./PagedTable";
import { amountColumn, dateColumn, employerColumn, notesColumn } from "./contributionColumns";
import { DASH } from "./format";

const RECEIVED_COLUMNS: Column<Contribution>[] = [
  dateColumn,
  {
    key: "contributor",
    header: "Contributor",
    // As reported, linked to the donor it was resolved to; a build not yet resolved has none.
    render: (row) =>
      row.donor_id === null ? (
        (row.contributor_name ?? DASH)
      ) : (
        <Anchor component={Link} to={`/donor/${row.donor_id}`}>
          {row.contributor_name ?? DASH}
        </Anchor>
      ),
  },
  employerColumn,
  amountColumn,
  notesColumn,
];

const NOUN = ["contribution", "contributions"] as const;
const contributionsOf = (page: ContributionPage) => page.contributions;

/**
 * Itemized contributions, as reported, a page at a time (`PagedTable`). `columns` defaults to a
 * recipient's view: who gave, linked to their donor page.
 */
function ContributionsTable({
  query,
  emptyMessage,
  columns = RECEIVED_COLUMNS,
}: {
  query: ContributionsQuery;
  emptyMessage: string;
  columns?: Column<Contribution>[];
}) {
  return (
    <PagedTable
      query={query}
      rowsOf={contributionsOf}
      rowKey={(row) => row.source_record_id}
      columns={columns}
      noun={NOUN}
      emptyMessage={emptyMessage}
    />
  );
}

export default ContributionsTable;
