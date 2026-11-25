import { Stack, Title } from "@mantine/core";
import type { OutsideSpending, OutsideSpendingKind } from "../api/client";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import OutsideSpendingNotes from "../components/OutsideSpendingNotes";
import { DASH, money } from "../components/format";
import { byKind, kindsWithSpending, OUTSIDE_SPENDING_KINDS } from "../domain/outsideSpending";
import type { KindAmounts } from "../domain/outsideSpending";

type Row = KindAmounts & { kind: OutsideSpendingKind };

// A kind's side it never has is a dash, not $0: party coordinated expenditures are never against a
// candidate, and an electioneering communication is for and against no one (spec §6.1).
const COLUMNS: Column<Row>[] = [
  { key: "kind", header: "Kind", render: (row) => OUTSIDE_SPENDING_KINDS[row.kind].label },
  {
    key: "for",
    header: "For",
    align: "right",
    render: (row) => (row.kind === "electioneering_communication" ? DASH : money(row.support)),
  },
  {
    key: "against",
    header: "Against",
    align: "right",
    render: (row) =>
      row.kind === "electioneering_communication" || row.kind === "party_coordinated"
        ? DASH
        : money(row.oppose),
  },
  {
    key: "neither",
    header: "Neither side",
    align: "right",
    // Only an electioneering communication has money on no side; `money` gives every other kind
    // a dash.
    render: (row) => money(row.none),
  },
];

/**
 * What others spent on a candidate in one cycle (every-FEC-dollar spec §6.5), a row for each kind
 * there was, by side, and what each kind is. Never one total: money for a candidate and against
 * them point opposite ways. Nothing at all when nobody spent anything on them.
 */
function CandidateOutsideSpending({
  spending,
  cycle,
}: {
  spending: OutsideSpending;
  cycle: number;
}) {
  const kinds = kindsWithSpending(spending);
  if (kinds.length === 0) return null;
  const amounts = byKind(spending);
  return (
    <section aria-labelledby="outside-spending">
      <Title order={3} id="outside-spending" mb="sm">
        Outside spending in {cycle}
      </Title>
      <Stack gap="md">
        <DataTable
          columns={COLUMNS}
          rows={kinds.map((kind) => ({ kind, ...amounts[kind] }))}
          rowKey={(row) => row.kind}
        />
        <OutsideSpendingNotes kinds={kinds} />
      </Stack>
    </section>
  );
}

export default CandidateOutsideSpending;
