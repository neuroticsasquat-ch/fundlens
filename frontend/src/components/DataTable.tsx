import { Table, Text, UnstyledButton } from "@mantine/core";
import type { ComponentProps, ReactNode } from "react";
import { useState } from "react";

export type Column<T> = {
  key: string;
  header: string;
  /** `right` also sets tabular figures, for numbers. */
  align?: "left" | "right";
  render: (row: T) => ReactNode;
  /** Present ⇒ the column sorts on this value; `null` sorts last either way. */
  sortValue?: (row: T) => number | string | null;
};

export type Sort = { key: string; direction: "asc" | "desc" };

type Props<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  caption?: string;
  /** Unset ⇒ the rows' own order until a header is clicked. */
  defaultSort?: Sort;
  /** Extra props for a row's `tr`: dimming, ids. */
  rowProps?: (row: T) => Partial<ComponentProps<typeof Table.Tr>>;
  /** Rendered instead of the table when there are no rows. */
  emptyMessage?: string;
};

/** `rows` sorted on `column`, stably, with `null` values last in either direction. */
function sortRows<T>(rows: T[], column: Column<T>, direction: Sort["direction"]): T[] {
  const value = column.sortValue!;
  return rows
    .map((row, index) => ({ row, index, v: value(row) }))
    .sort((a, b) => {
      if (a.v === null || b.v === null) {
        return a.v === b.v ? a.index - b.index : a.v === null ? 1 : -1;
      }
      const order =
        typeof a.v === "number" && typeof b.v === "number"
          ? a.v - b.v
          : String(a.v).localeCompare(String(b.v));
      return (direction === "asc" ? order : -order) || a.index - b.index;
    })
    .map(({ row }) => row);
}

// A first click shows the biggest numbers, or strings from A.
function firstDirection<T>(rows: T[], column: Column<T>): Sort["direction"] {
  const sample = rows.map(column.sortValue!).find((v) => v !== null);
  return typeof sample === "string" ? "asc" : "desc";
}

/**
 * A table over typed column definitions; a column with `sortValue` sorts by clicking its header
 * (a second click flips it). Scrolls sideways inside its container on narrow screens.
 */
function DataTable<T>({
  columns,
  rows,
  rowKey,
  caption,
  defaultSort,
  rowProps,
  emptyMessage,
}: Props<T>) {
  const [sort, setSort] = useState<Sort | undefined>(defaultSort);

  if (rows.length === 0 && emptyMessage !== undefined)
    return <Text c="dimmed">{emptyMessage}</Text>;

  const sortColumn = sort && columns.find((column) => column.key === sort.key && column.sortValue);
  const shown = sortColumn ? sortRows(rows, sortColumn, sort.direction) : rows;

  const toggle = (column: Column<T>) =>
    setSort(
      sort?.key === column.key
        ? { key: column.key, direction: sort.direction === "asc" ? "desc" : "asc" }
        : { key: column.key, direction: firstDirection(rows, column) },
    );

  const numeric = { fontVariantNumeric: "tabular-nums" } as const;

  return (
    <Table.ScrollContainer minWidth={640}>
      <Table striped highlightOnHover>
        {caption && <Table.Caption>{caption}</Table.Caption>}
        <Table.Thead>
          <Table.Tr>
            {columns.map((column) => {
              const active = sort?.key === column.key ? sort.direction : undefined;
              return (
                <Table.Th
                  key={column.key}
                  ta={column.align}
                  aria-sort={
                    column.sortValue
                      ? active === "asc"
                        ? "ascending"
                        : active === "desc"
                          ? "descending"
                          : "none"
                      : undefined
                  }
                >
                  {column.sortValue ? (
                    <UnstyledButton fw={700} fz="sm" onClick={() => toggle(column)}>
                      {column.header}
                      <span aria-hidden="true">
                        {active === "asc" ? " ▲" : active === "desc" ? " ▼" : ""}
                      </span>
                    </UnstyledButton>
                  ) : (
                    column.header
                  )}
                </Table.Th>
              );
            })}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {shown.map((row) => (
            <Table.Tr key={rowKey(row)} {...rowProps?.(row)}>
              {columns.map((column) => (
                <Table.Td
                  key={column.key}
                  ta={column.align}
                  style={column.align === "right" ? numeric : undefined}
                >
                  {column.render(row)}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

export default DataTable;
