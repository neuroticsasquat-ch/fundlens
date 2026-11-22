import { Anchor, Badge, Group, Text } from "@mantine/core";
import { Link } from "react-router";
import type { OperatingExpenditurePage } from "../api/client";
import type { OperatingExpendituresQuery } from "../api/contributions";
import { SPENDING_CATEGORY_LABELS, withSubItems } from "../domain/spending";
import type { SpendingRow } from "../domain/spending";
import type { Column } from "./DataTable";
import PagedTable from "./PagedTable";
import { DASH, isoDate, money } from "./format";

// How far a sub-item's payee is set in under the payment it itemizes, per level.
const INDENT = 20;

const COLUMNS: Column<SpendingRow>[] = [
  { key: "date", header: "Date", render: ({ expenditure }) => isoDate(expenditure.date) },
  {
    key: "payee",
    header: "Payee",
    // As reported, linked to the payee's page where the key has one: a person, or a name that
    // names nobody (PETTY CASH), has none (ADR-0012).
    render: ({ expenditure, depth }) => {
      const name = expenditure.payee_name ?? DASH;
      return (
        <Text inherit pl={depth * INDENT}>
          {depth > 0 && <span aria-hidden="true">↳ </span>}
          {expenditure.payee_id === null ? (
            name
          ) : (
            <Anchor component={Link} to={`/payee/${expenditure.payee_id}`} inherit>
              {name}
            </Anchor>
          )}
        </Text>
      );
    },
  },
  { key: "purpose", header: "Purpose", render: ({ expenditure }) => expenditure.purpose ?? DASH },
  {
    key: "category",
    header: "Category",
    // NULL only in a build made before categories were (every-FEC-dollar spec §5.8).
    render: ({ expenditure }) =>
      expenditure.spending_category === null
        ? DASH
        : SPENDING_CATEGORY_LABELS[expenditure.spending_category],
  },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    render: ({ expenditure }) => money(expenditure.amount),
  },
  {
    key: "notes",
    header: "Notes",
    render: ({ expenditure }) => (
      <Group gap={4} wrap="nowrap">
        {!expenditure.counted && (
          <Badge variant="outline" color="gray">
            Not counted
          </Badge>
        )}
        {expenditure.is_in_kind && (
          <Badge variant="light" color="grape">
            In-kind
          </Badge>
        )}
      </Group>
    ),
  },
];

const NOUN = ["payment", "payments"] as const;
const rowsOf = (page: OperatingExpenditurePage) => withSubItems(page.expenditures);

/**
 * A committee's itemized operating expenditures, as filed, a page at a time (`PagedTable`): each
 * payment followed by the sub-items that itemize it, set in under it (a card bill's charges). The
 * tally counts payments, not their sub-items.
 */
function OperatingExpendituresTable({
  query,
  order,
  emptyMessage,
}: {
  query: OperatingExpendituresQuery;
  order: string;
  emptyMessage: string;
}) {
  return (
    <PagedTable
      query={query}
      rowsOf={rowsOf}
      rowKey={({ expenditure }) => expenditure.source_record_id}
      columns={COLUMNS}
      noun={NOUN}
      order={order}
      emptyMessage={emptyMessage}
      isItem={({ depth }) => depth === 0}
      // Dimmed, as a sub-item is never added to the total: its payment is.
      rowProps={({ depth }) => (depth > 0 ? { c: "dimmed" } : {})}
    />
  );
}

export default OperatingExpendituresTable;
