import { Alert, Button, Group, Stack, Text } from "@mantine/core";
import type { Table } from "@mantine/core";
import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import type { ComponentProps } from "react";
import { isProblem } from "../api/query";
import DataTable from "./DataTable";
import type { Column } from "./DataTable";
import QueryStatus from "./QueryStatus";
import { count } from "./format";

/**
 * An itemized list a cursor page at a time: "Load more" fetches the next cursor's page and appends
 * it. The rows already shown stay when a later page fails. No column should sort: the rows are the
 * pages loaded so far, in the API's `order`, and sorting them would pass off a partial list as the
 * whole one.
 */
function PagedTable<Page, Row>({
  query,
  rowsOf,
  rowKey,
  columns,
  noun,
  emptyMessage,
  order = "newest first",
  isItem,
  rowProps,
}: {
  query: UseInfiniteQueryResult<InfiniteData<Page>, unknown>;
  rowsOf: (page: Page) => Row[];
  rowKey: (row: Row) => string;
  columns: Column<Row>[];
  /** What a row is, one and many: `["contribution", "contributions"]`. */
  noun: readonly [string, string];
  emptyMessage: string;
  /** How the API ordered the rows, for the tally under them. */
  order?: string;
  /** Which rows the tally counts, unset ⇒ every row: a sub-item shown under its payment is not. */
  isItem?: (row: Row) => boolean;
  rowProps?: (row: Row) => Partial<ComponentProps<typeof Table.Tr>>;
}) {
  // Until the first page arrives (or fails), the page-level states; after it, the rows stay put.
  if (query.data === undefined) return <QueryStatus query={query}>{() => null}</QueryStatus>;

  const rows = query.data.pages.flatMap(rowsOf);
  const items = isItem ? rows.filter(isItem).length : rows.length;
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
        rowKey={rowKey}
        rowProps={rowProps}
        emptyMessage={emptyMessage}
      />
      {rows.length > 0 && (
        <Text size="sm" c="dimmed">
          {count(items)} {items === 1 ? noun[0] : noun[1]}, {order}
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
