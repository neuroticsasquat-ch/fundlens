import { Anchor, Box, Code, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";
import { Link } from "react-router";
import type { ReportedTotals } from "../api/client";
import { money, percent, reportedMoney } from "../components/format";

/** A reported total's money figures: every field but its source file and reporting period. */
type Measure = {
  [K in keyof ReportedTotals]: ReportedTotals[K] extends number | null ? K : never;
}[keyof ReportedTotals];

/** The figures the panel shows, in order: FEC's own summary of the cycle, as filed. */
const FIGURES: { label: string; measure: Measure }[] = [
  { label: "Raised", measure: "receipts" },
  { label: "Spent", measure: "disbursements" },
  { label: "Cash on hand", measure: "cash_on_hand_end" },
  { label: "Debts", measure: "debts_owed_by" },
  { label: "Loans from the candidate", measure: "candidate_loans" },
  { label: "Other loans", measure: "other_loans" },
  { label: "Unitemized from individuals", measure: "individual_unitemized" },
  { label: "Itemized from individuals", measure: "individual_itemized" },
];

/** "2023-01-01 to 2024-12-31"; before 2008 FEC's files give only the end. */
function period({ period_start, period_end }: ReportedTotals): string {
  if (period_start && period_end) return `${period_start} to ${period_end}`;
  if (period_end) return `to ${period_end}`;
  return "not reported";
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Text component="dt" size="sm" c="dimmed">
        {label}
      </Text>
      <Text component="dd" m={0} fw={600} style={{ fontVariantNumeric: "tabular-nums" }}>
        {value}
      </Text>
    </div>
  );
}

// Before 2008 FEC's summary files have no itemized individual figure, so no cycle has coverage
// (every-FEC-dollar spec §4.7).
const ITEMIZED_FIGURE_FROM = 2008;

/**
 * Why there is no coverage line: `reason`; else, where the reported itemized figure is missing or
 * 0, that there is none to set the itemized total against (spec §4.4).
 */
function NoCoverage({
  reason,
  reported,
  cycle,
  filer,
}: {
  reason?: string;
  reported: ReportedTotals;
  cycle: number;
  filer: string;
}) {
  let shown = reason;
  if (shown === undefined && !reported.individual_itemized) {
    shown =
      cycle < ITEMIZED_FIGURE_FROM
        ? "No coverage: FEC's figures before 2008 do not split itemized money from unitemized."
        : `No coverage: this ${filer} reported no itemized individual money to set it against.`;
  }
  return shown ? (
    <Text size="sm" c="dimmed">
      {shown}
    </Text>
  ) : null;
}

/**
 * A cycle's reported totals: what a campaign or committee reported to FEC it raised, spent, holds
 * and owes, as filed, with its reporting period and source file, and beside them fundlens's
 * itemized total and its coverage of FEC's itemized figure. Never added to the itemized totals:
 * the two answer different questions (every-FEC-dollar spec §4). A measure the cycle's file lacks
 * is "not reported".
 */
function ReportedPanel({
  cycle,
  reported,
  itemizedTotal,
  coverage,
  filer,
  missing,
  noCoverage,
  notes,
}: {
  cycle: number;
  reported: ReportedTotals | null;
  itemizedTotal: number | null;
  coverage: number | null;
  /** Who reported: "campaign" or "committee", for the coverage line. */
  filer: string;
  /** Shown instead of the figures when FEC's files have no row. */
  missing: string;
  /**
   * Why there is no coverage, where the panel has figures but no coverage to show and the reason
   * is not the panel's own: a reported itemized figure that is missing or 0.
   */
  noCoverage?: string;
  /** One-line notes on how the figures were put together. */
  notes?: ReactNode;
}) {
  return (
    <section aria-labelledby="reported">
      <Title order={3} id="reported" mb="sm">
        Reported to the FEC
      </Title>
      {reported === null ? (
        <Stack gap="xs">
          <Text c="dimmed">{missing}</Text>
          {notes}
        </Stack>
      ) : (
        <Stack gap="sm">
          <Text c="dimmed" size="sm">
            Reporting period {period(reported)} · source <Code>{reported.source_file}</Code>
          </Text>
          <SimpleGrid component="dl" cols={{ base: 2, sm: 4 }} spacing="md" m={0}>
            {FIGURES.map(({ label, measure }) => (
              <Figure key={measure} label={label} value={reportedMoney(reported[measure])} />
            ))}
          </SimpleGrid>
          <Box component="dl" m={0}>
            <Figure label="Itemized by fundlens" value={money(itemizedTotal)} />
          </Box>
          {coverage !== null ? (
            <Text size="sm">
              fundlens itemizes {percent(coverage)} of the itemized individual money this{" "}
              {filer} reported.{" "}
              <Anchor component={Link} to="/methodology">
                Methodology
              </Anchor>
            </Text>
          ) : (
            <NoCoverage reason={noCoverage} reported={reported} cycle={cycle} filer={filer} />
          )}
          {notes}
        </Stack>
      )}
    </section>
  );
}

export default ReportedPanel;
