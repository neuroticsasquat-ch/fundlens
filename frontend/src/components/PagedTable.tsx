import { Alert, Button, Group, Stack, Text } from "@mantine/core";
import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { isProblem } from "../api/query";
import DataTable from "./DataTable";
import type { Column } from "./DataTable";
import QueryStatus from "./QueryStatus";
import { count } from "./format";

/**
 * An itemized list a cursor page at a time: "Load more" fetches the next cursor's page and appends
 * it. The rows already shown stay when a later page fails. No column should sort: the rows are the
 * pages loaded so far, newest first, and sorting them would pass off a partial list as the whole
 * one.
 */
function PagedTable<Page, Row>({
  query,
  rowsOf,
  rowKey,
  columns,
  noun,
  emptyMessage,
}: {
  query: UseInfiniteQueryResult<InfiniteData<Page>, unknown>;
  rowsOf: (page: Page) => Row[];
  rowKey: (row: Row) => string;
  columns: Column<Row>[];
  /** What a row is, one and many: `["contribution", "contributions"]`. */
  noun: readonly [string, string];
  emptyMessage: string;
}) {
  // Until the first page arrives (or fails), the page-level states; after it, the rows stay put.
  if (query.data === undefined) return <QueryStatus query={query}>{() => null}</QueryStatus>;

  const rows = query.data.pages.flatMap(rowsOf);
  const { error, refetch, fetchNextPage } = query;
  // A cursor whose build has been replaced (410) won't read on, and a failed refetch leaves the
  // rows behind it stale: both start again from the first page, whose cursors will. Any other
  // failed page is asked for again.
  const startAgain = query.isRefetchError || (isProblem(error) && error.status === 410);
  return (
    <Stack gap="sm">
      <DataTable columns={columns} rows={rows} rowKey={rowKey} emptyMessage={emptyMessage} />
      {rows.length > 0 && (
        <Text size="sm" c="dimmed">
          {count(rows.length)} {rows.length === 1 ? noun[0] : noun[1]}, newest first
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

export default PagedTable;
