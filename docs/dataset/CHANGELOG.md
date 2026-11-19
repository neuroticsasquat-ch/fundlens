# Changelog

Every change to the dataset's tables or columns, newest first: a table or column added, dropped,
renamed or retyped, or a column whose meaning changed. Each entry is dated by the change's merge
and reaches the bucket with the next snapshot. Each table's schema is at `schema/<table>.json`.

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
