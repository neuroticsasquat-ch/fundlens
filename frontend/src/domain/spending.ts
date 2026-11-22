import type { OperatingExpenditure, SpendingCategory } from "../api/client";

/**
 * Each spending category's name, in the order of every-FEC-dollar spec §5.3's table: what the
 * money bought, then money passed on, card bills and the rest.
 */
export const SPENDING_CATEGORY_LABELS: Record<SpendingCategory, string> = {
  media: "Media",
  digital: "Digital",
  mail: "Mail",
  fundraising: "Fundraising",
  payroll: "Payroll",
  consulting: "Consulting",
  field: "Field",
  polling_research: "Polling and research",
  travel: "Travel",
  events: "Events",
  administrative: "Administrative",
  legal_compliance: "Legal and compliance",
  transfers_fees: "Transfers and fees",
  credit_card: "Credit card bills",
  other: "Other",
};

/** `categories` in the table's order, whatever order they came in. */
export function inCategoryOrder(categories: SpendingCategory[]): SpendingCategory[] {
  const order = Object.keys(SPENDING_CATEGORY_LABELS);
  return [...categories].sort((a, b) => order.indexOf(a) - order.indexOf(b));
}

/** An itemized payment, or a sub-item `depth` levels under the payment it itemizes. */
export type SpendingRow = { expenditure: OperatingExpenditure; depth: number };

/**
 * Payments in their order, each followed by its sub-items, and theirs, depth first: a card bill,
 * then its charges.
 */
export function withSubItems(expenditures: OperatingExpenditure[], depth = 0): SpendingRow[] {
  return expenditures.flatMap((expenditure) => [
    { expenditure, depth },
    ...withSubItems(expenditure.sub_items, depth + 1),
  ]);
}
