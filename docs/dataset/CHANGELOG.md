# Changelog

Every change to the dataset's tables or columns, newest first: a table or column added, dropped,
renamed or retyped, or a column whose meaning changed. Each entry is dated by the change's merge
and reaches the bucket with the next snapshot. Each table's schema is at `schema/<table>.json`.

## 2026-11-24 — `independent_expenditure.communication_type` and `communication_class` added

Two columns, an additive change: a communication cost's (`kind = 'communication_cost'`) type and
class, as filed on the FEC's communication costs file, joined to the `pas2` row of the same
`SUB_ID`. That file adds no rows and no money: every communication cost is still `pas2`'s, its
amount and side included. Both are null on every other kind, on a communication cost that file
lacks, and before 2010. A cycle built before the change has neither column: read both as null.

## 2026-11-24 — `electioneering_communication` added

One table, an additive change: `electioneering_communication`, every electioneering
communication from 2010 on, one row per candidate a disbursement names, from the FEC's
electioneering communications file, as `schema/electioneering_communication.json` describes it.
Sum `amount`, each candidate's share, never `disbursement_amount`. A row has no side, and a report
a later one restates may be counted twice. A cycle built before the table existed has no files of
it until the backfill rebuilds it: read a table's cycles from `manifest.json`.

## 2026-11-24 — `independent_expenditure` adds the 24/48-hour file's rows and four columns

Rows, four columns and one retyping:

- **Rows.** From 2010, the table also holds independent expenditures from the FEC's 24/48-hour
  file that no periodic report holds yet: a spender's estimates dated after its last periodic
  report, and the spending of a spender with no `pas2` independent expenditure that reports
  some, screened against what it reports. Each is `kind = 'ie'`. Such a row leaves the table once
  a periodic report restates it.
- **`source_record_id` is text** (a breaking change): a `pas2` row's is its `SUB_ID`'s digits, as
  before but as a string, and a 24/48-hour row's is `<file_num>:<tran_id>`. A cycle built before
  the change still holds integers until the backfill rebuilds it: read the column as text.
- **Four columns added**, an additive change: `source_file` (`pas2` or `ie_24_48`), `payee_name`,
  `purpose` and `dissemination_date`. `support_oppose` is null on a 24/48-hour row whose filer
  gave no side, and `transaction_type` on every 24/48-hour row. A cycle built before the change
  has none of the four columns: read `source_file` as `pas2` and the rest as null.

## 2026-11-24 — `operating_expenditure.is_in_kind` reads crypto received and in-kind gifts made

One column's meaning, a change to its values only: `is_in_kind` is now also true for
cryptocurrency a committee was given and reported as spending naming the giver
(`… USDC RECEIVED, NOT LIQUIDATED`), and no longer true for a payment for an in-kind contribution
the committee made or pays ahead for (`IN-KIND CONTRIBUTION MADE: POLLING`, `ADVANCE PAYMENT FOR
… IN-KIND CONTRIBUTIONS`). `counted` does not change. A cycle built before the change keeps the
old values until the backfill rebuilds it.

## 2026-11-21 — `operating_expenditure.spending_category` and `category_source` filled

Two columns' meaning, a change to their values only: `spending_category` now holds what each
payment bought, one of fifteen categories, read from the purpose the filer wrote, else from the
FEC's category code where it is one of the six filers use reliably, else `other`;
`category_source` says which (`purpose_rule`, `fec`, `unclassified`). A cycle built before the
change has both null until the backfill rebuilds it.

## 2026-11-21 — `operating_expenditure` added

One table, an additive change: `operating_expenditure`, every payment a committee itemized from
2004 on, from the FEC's operating expenditures file, as `schema/operating_expenditure.json`
describes it. Sum only rows where `counted` is true. `spending_category` and `category_source`
are null until a later change fills them. A cycle built before the table existed has no files of
it until the backfill rebuilds it: read a table's cycles from `manifest.json`.

## 2026-11-20 — `organization_receipt.is_returned_cost` added

One column, an additive change: `organization_receipt.is_returned_cost`, true when a receipt's
memo names a cost coming back to the committee (a tax, vendor or expense refund, rebate or
reimbursement), not a gift. Such a row's `fec_line` is now `15 other receipts`, and its
`is_other_line` true, where its type had put it on `11(a)(i)`; a non-contribution account's keeps
its line. The same rule moves a `contribution` row so. A cycle built before the change has no such column: read it as false.

## 2026-11-18 — `reported_total` and `candidate_reported_total` added

Two tables, an additive change: `reported_total`, each committee's reported totals per cycle
from the FEC's summary files (`committee_summary` from 2008, `webk` 1996–2006), and
`candidate_reported_total`, each candidate's before 2008 from `weball`, as
`schema/reported_total.json` and `schema/candidate_reported_total.json` describe them. A cycle
built before they existed has no files of them until the backfill rebuilds it: read a table's
cycles from `manifest.json`.

## 2026-11-18 — v1

The first public schema: `contribution`, `contributor`, `donor`, `crosswalk`, `committee`,
`candidate`, `candidate_committee_link`, `race`, `committee_transfer`, `organization_receipt` and
`independent_expenditure`, as `schema/` describes them.
