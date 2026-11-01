import { Alert, Anchor, Button, Group, Stack, Text } from "@mantine/core";
import { Link } from "react-router";
import type { Contribution } from "../api/client";
import type { ContributionsQuery } from "../api/contributions";
import { isProblem } from "../api/query";
import DataTable from "./DataTable";
import type { Column } from "./DataTable";
import QueryStatus from "./QueryStatus";
import { amountColumn, dateColumn, employerColumn, notesColumn } from "./contributionColumns";
import { count, DASH } from "./format";

// No column sorts: the rows are the pages loaded so far, newest first, and sorting them would
// pass off a partial list as the whole one.
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

/**
 * Itemized contributions, as reported, a page at a time: "Load more" fetches the next cursor's
 * page and appends it. The rows already shown stay when a later page fails. `columns` defaults to
 * a recipient's view: who gave, linked to their donor page.
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
  // Until the first page arrives (or fails), the page-level states; after it, the rows stay put.
  if (query.data === undefined) return <QueryStatus query={query}>{() => null}</QueryStatus>;

  const rows = query.data.pages.flatMap((page) => page.contributions);
  const { error, refetch, fetchNextPage } = query;
  // A cursor whose build has been replaced (410) won't read on, and a failed refetch leaves the
  // rows behind it stale: both start again from the first page, whose cursors will. Any other
  // failed page is asked for again.
  const startAgain = query.isRefetchError || (isProblem(error) && error.status === 410);
  return (
    <Stack gap="sm">
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(row) => row.source_record_id}
        emptyMessage={emptyMessage}
      />
      {rows.length > 0 && (
        <Text size="sm" c="dimmed">
          {count(rows.length)} {rows.length === 1 ? "contribution" : "contributions"}, newest first
        </Text>
      )}
      {query.isError ? (
        <Alert
          role="alert"
          color="red"
          title={isProblem(error) ? error.title : "Couldn't reach the API."}
        >
          <Stack gap="xs" align="flex-start">
            <Text size="sm">
              {isProblem(error) ? error.detail : "Check your connection and try again."}
            </Text>
            <Button
              size="xs"
              variant="light"
              loading={query.isFetching}
              onClick={() => void (startAgain ? refetch() : fetchNextPage())}
            >
              {startAgain ? "Start again" : "Try again"}
            </Button>
          </Stack>
        </Alert>
      ) : (
        query.hasNextPage && (
          <Group>
            <Button
              variant="default"
              loading={query.isFetchingNextPage}
              onClick={() => void query.fetchNextPage()}
            >
              Load more
            </Button>
          </Group>
        )
      )}
    </Stack>
  );
}

export default ContributionsTable;
