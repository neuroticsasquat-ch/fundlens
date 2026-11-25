import type { OutsideSpending } from "../api/client";
import { money } from "../components/format";
import { byKind, kindsWithSpending, OUTSIDE_SPENDING_KINDS } from "../domain/outsideSpending";

/**
 * Outside spending on a race by kind, in a line under its heading: "independent expenditures
 * $150,000 for candidates and $125,000 against · electioneering communications $101,319". Never
 * one figure for every kind (NEU-2170): money for candidates and against them point opposite
 * ways, and an electioneering communication points neither. Null when there was none.
 */
export function outsideSpendingSummary(spending: OutsideSpending): string | null {
  const amounts = byKind(spending);
  const parts = kindsWithSpending(spending).map((kind) => {
    const label = OUTSIDE_SPENDING_KINDS[kind].label.toLowerCase();
    const { support, oppose, none } = amounts[kind];
    if (kind === "electioneering_communication") return `${label} ${money(none)}`;
    if (kind === "party_coordinated") return `${label} ${money(support)}`;
    return `${label} ${money(support)} for candidates and ${money(oppose)} against`;
  });
  return parts.length === 0 ? null : `Outside spending: ${parts.join(" · ")}`;
}
