import { Anchor, Group, NativeSelect, SegmentedControl, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { Link } from "react-router";
import { $api } from "../api/client";
import type { CommitteeCycle, Sort, SpendingCategory, TopPayee } from "../api/client";
import { OPERATING_EXPENDITURE_PAGES } from "../api/contributions";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import OperatingExpendituresTable from "../components/OperatingExpendituresTable";
import { availableMoney, count, money } from "../components/format";
import { inCategoryOrder, SPENDING_CATEGORY_LABELS } from "../domain/spending";
import SpendingCategoryChart from "./SpendingCategoryChart";

const PAYEE_COLUMNS: Column<TopPayee>[] = [
  {
    key: "rank",
    header: "Rank",
    align: "right",
    render: (payee) => count(payee.rank),
    sortValue: (payee) => payee.rank,
  },
  {
    key: "payee",
    header: "Payee",
    // A person, or a name that names nobody (PETTY CASH), has no page (ADR-0012).
    render: (payee) =>
      payee.payee_id === null ? (
        payee.name
      ) : (
        <Anchor component={Link} to={`/payee/${payee.payee_id}`}>
          {payee.name}
        </Anchor>
      ),
  },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    render: (payee) => money(payee.amount),
    sortValue: (payee) => payee.amount,
  },
];

const ORDERS: Record<Sort, string> = { date: "newest first", amount: "largest first" };

// The category filter's value for every category.
const ALL_CATEGORIES = "";

const isCategory = (value: string): value is SpendingCategory =>
  Object.hasOwn(SPENDING_CATEGORY_LABELS, value);

/**
 * A committee's operating expenditures in one cycle: its total, by category, the payees it paid
 * most and every payment it itemized. Spending, never a contribution: in no receipt total above
 * it (every-FEC-dollar spec §5). A cycle with no counted payment says so and shows nothing else.
 */
function CommitteeSpending({ id, shown }: { id: string; shown: CommitteeCycle }) {
  const total = shown.total_operating_expenditures;
  return (
    <section aria-labelledby="spending">
      <Title order={3} id="spending" mb="sm">
        Spending
      </Title>
      <Stack gap="lg">
        <Stack gap={4}>
          <Text>
            Operating expenditures in {shown.cycle}:{" "}
            <Text span fw={700} style={{ fontVariantNumeric: "tabular-nums" }}>
              {availableMoney(total)}
            </Text>
          </Text>
          <Text c="dimmed" size="sm">
            {total === null ? (
              <>
                FEC&apos;s operating-expenditure file has no counted payment by this committee
                in {shown.cycle}, or this build does not hold it.
              </>
            ) : (
              <>
                What the committee itemized paying out to run itself, refunds netted off. A card
                bill counts once, as the bill; the charges itemizing it are listed under it and not
                counted again.
              </>
            )}
          </Text>
        </Stack>
        {total !== null && (
          <>
            <section aria-labelledby="spending-categories">
              <Title order={4} id="spending-categories" mb="sm">
                By category
              </Title>
              {shown.spending_by_category.length === 0 ? (
                <Text c="dimmed">No spending categories in {shown.cycle}.</Text>
              ) : (
                <SpendingCategoryChart categories={shown.spending_by_category} />
              )}
            </section>
            <section aria-labelledby="top-payees">
              <Title order={4} id="top-payees">
                Top payees
              </Title>
              <Text c="dimmed" size="sm" mb="sm">
                Grouped by name, its spellings normalized, so &ldquo;LLC&rdquo; and
                &ldquo;L.L.C.&rdquo; are one payee; not resolved like individual donors. A person,
                or a name like petty cash, has no page.{" "}
                <Anchor component={Link} to="/methodology">
                  Methodology
                </Anchor>
              </Text>
              <DataTable
                columns={PAYEE_COLUMNS}
                rows={shown.top_payees}
                rowKey={(payee) => payee.payee_key}
                emptyMessage={`No payee totals in ${shown.cycle}.`}
              />
            </section>
            <ItemizedSpending
              id={id}
              cycle={shown.cycle}
              categories={inCategoryOrder(shown.spending_by_category.map((row) => row.category))}
            />
          </>
        )}
      </Stack>
    </section>
  );
}

function ItemizedSpending({
  id,
  cycle,
  categories,
}: {
  id: string;
  cycle: number;
  categories: SpendingCategory[];
}) {
  const [sort, setSort] = useState<Sort>("date");
  const [category, setCategory] = useState<SpendingCategory | typeof ALL_CATEGORIES>(ALL_CATEGORIES);
  const expenditures = $api.useInfiniteQuery(
    "get",
    "/v1/committees/{committee_id}/expenditures",
    {
      params: {
        path: { committee_id: id },
        query: { cycle, sort, ...(category === ALL_CATEGORIES ? {} : { category }) },
      },
    },
    OPERATING_EXPENDITURE_PAGES,
  );
  return (
    <section aria-labelledby="itemized-spending">
      <Title order={4} id="itemized-spending" mb="sm">
        Itemized spending
      </Title>
      <Stack gap="sm">
        <Group align="flex-end">
          <SegmentedControl
            aria-label="Order"
            value={sort}
            onChange={(value) => setSort(value as Sort)}
            data={[
              { value: "date", label: "Newest first" },
              { value: "amount", label: "Largest first" },
            ]}
          />
          <NativeSelect
            label="Category"
            value={category}
            onChange={(event) => {
              const { value } = event.currentTarget;
              setCategory(isCategory(value) ? value : ALL_CATEGORIES);
            }}
            data={[
              { value: ALL_CATEGORIES, label: "All categories" },
              ...categories.map((value) => ({ value, label: SPENDING_CATEGORY_LABELS[value] })),
            ]}
          />
        </Group>
        <OperatingExpendituresTable
          query={expenditures}
          order={ORDERS[sort]}
          emptyMessage={
            category === ALL_CATEGORIES
              ? `No itemized operating expenditures by this committee in ${cycle}.`
              : `No ${SPENDING_CATEGORY_LABELS[category].toLowerCase()} payments by this ` +
                `committee in ${cycle}.`
          }
        />
        <Text c="dimmed" size="sm">
          Not counted: a sub-item, itemizing the payment it is listed under (a card bill&apos;s
          charge), which is counted whole; or a memo entry FEC does not count. In-kind: an outlay
          a giver made for the committee, counted in its spending but in no payee&apos;s total.
        </Text>
      </Stack>
    </section>
  );
}

export default CommitteeSpending;
