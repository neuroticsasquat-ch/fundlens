import type { OutsideSpending, OutsideSpendingKind } from "../api/client";

/**
 * The four kinds of outside spending (every-FEC-dollar spec §6.1), in the order a page lists them:
 * what each is called and what it is, in a line.
 */
export const OUTSIDE_SPENDING_KINDS: Record<
  OutsideSpendingKind,
  { label: string; explanation: string }
> = {
  independent_expenditure: {
    label: "Independent expenditures",
    explanation:
      "advertising and other spending that expressly calls for a candidate's election or defeat, " +
      "made without the campaign's cooperation, by committees and by others alike.",
  },
  communication_cost: {
    label: "Communication costs",
    explanation:
      "what a corporation or union spent urging its own members, or its executives and " +
      "shareholders, to vote for or against a candidate.",
  },
  party_coordinated: {
    label: "Party coordinated expenditures",
    explanation:
      "what a party committee spent in cooperation with its own candidate, within a legal limit; " +
      "always in support.",
  },
  electioneering_communication: {
    label: "Electioneering communications",
    explanation:
      "broadcast ads naming a candidate shortly before an election that call for no vote, so for " +
      "neither side; an ad naming several candidates is split equally among them.",
  },
};

/** The kinds in `OUTSIDE_SPENDING_KINDS`' order. */
export const KIND_ORDER = Object.keys(OUTSIDE_SPENDING_KINDS) as OutsideSpendingKind[];

/** A kind's money, by side: `none` holds an electioneering communication's, which has no side. */
export type KindAmounts = { support: number; oppose: number; none: number | null };

/** `spending`'s money of each kind, by side. */
export function byKind(spending: OutsideSpending): Record<OutsideSpendingKind, KindAmounts> {
  return {
    independent_expenditure: { ...spending.independent_expenditure, none: null },
    communication_cost: { ...spending.communication_cost, none: null },
    party_coordinated: { support: spending.party_coordinated, oppose: 0, none: null },
    electioneering_communication: {
      support: 0,
      oppose: 0,
      none: spending.electioneering_communication,
    },
  };
}

const hasAmounts = ({ support, oppose, none }: KindAmounts) =>
  support !== 0 || oppose !== 0 || (none ?? 0) !== 0;

/** The kinds `spending` has any money of, in order. */
export const kindsWithSpending = (spending: OutsideSpending): OutsideSpendingKind[] => {
  const amounts = byKind(spending);
  return KIND_ORDER.filter((kind) => hasAmounts(amounts[kind]));
};

/** Whether anyone spent anything of any kind on a candidate or race. */
export const hasOutsideSpending = (spending: OutsideSpending) =>
  kindsWithSpending(spending).length > 0;

/**
 * Every dollar spent on a candidate, for, against or neither, added up: an order for candidates
 * who raised nothing, never a figure to show. Money for a candidate and against them point
 * opposite ways (spec §6.5: no total on a candidate).
 */
export const outsideSpendingVolume = (spending: OutsideSpending) =>
  spending.independent_expenditure.support +
  spending.independent_expenditure.oppose +
  spending.communication_cost.support +
  spending.communication_cost.oppose +
  spending.party_coordinated +
  (spending.electioneering_communication ?? 0);
