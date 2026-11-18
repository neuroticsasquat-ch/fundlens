# fundlens: every FEC dollar — project spec

Linear initiative: fundlens (I-16). Project: P-NEU-107. Team: NEU. Glossary: `CONTEXT.md` at the repo root. Decisions and their rationale: `docs/adr/`. Original brief: `docs/campaign-finance-handover.md` (its Phase B).
This spec is the shared reference for every ticket in the project, read with the v1 spec (`fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md`, "v1 §n" below). v1's §3 (architecture), §5 (pipeline) and §10–§12 (infrastructure, local development, testing) govern this project unchanged. This document adds to v1's §4 (silver), §7 (gold and API) and §9 (public dataset), and says where. A ticket needs its own `/planit` spec only where this document is silent.

## 1. Purpose

v1 tracks itemized money *into* committees: individuals' contributions, committee-to-committee money, independent expenditures from `pas2`, and organization receipts. This project adds the rest of what FEC publishes in bulk, so that fundlens accounts for every dollar FEC can show: what each committee reports it raised, spent, holds and owes; where its money went; every kind of outside spending on a race; and the leadership PACs and lobbyist bundlers around a candidate. It is the handover's Phase B ("whatever else is needed for complete federal coverage").

**Non-goals**, each with its reason:

- FEC's Postgres dump files: they duplicate the bulk files.
- The Form 1 and Form 2 filer lists and the false and fictitious filings list: they hold no money.
- The unofficial Senate electronic filings, 2008–2018: their money is already in `indiv`.
- The national parties' nonfederal accounts before 2002 ("soft money"): not among FEC's bulk files.
- Election results, Lobbying Disclosure Act data, state data.
- The Presidential map exports (`<yyyy>_overall_summary.csv`, `Contributions_by_Size.csv`, `Contributions_by_3Zip.csv`): FEC's own summaries of presidential candidates' reported figures and of their contributions by size and by place: aggregates of what the files fundlens reads already hold, in `contribution` and, from M1, the summary files. NEU-2141 may cite `Contributions_by_Size.csv` as a check on its gift-size buckets; it is never a source.
- `webl` and `candidate_summary`: they repeat figures the files fundlens reads already hold (§3's not-read table).

Paper-filed and electronically filed `.fec` reports are not a non-goal: §9.

## 2. Decisions

The first four were locked on 2026-11-02, the last two on 2026-11-18. v1 §2 stands for everything else.

| Area | Decision | Reason |
|---|---|---|
| Project boundary | A separate project from v1. M3.5 Organization money stayed in v1. | v1 ships on its own scope and Done line; M3.5 fixed a v1 bug ahead of v1's backfill. Rejected: amending the v1 spec, which would blur what v1 ships. |
| Lobbyist files | FEC's lobbyist bundling and lobbyist/registrant PAC files are in scope. | v1's "lobbying data" non-goal means Lobbying Disclosure Act data, not FEC disclosures. |
| Payees and organizations | Grouped by normalized name, never resolved with Splink, no industry coding. | ADR-0011: the hard cases are corporate structure, not spelling, and industry coding is a project of its own. The payee ADR (NEU-2150) will be 0012. |
| Public dataset | Every silver table this project adds joins the dataset snapshot (§8). | The resolved dataset is the product (v1 §1). |
| Files read | The file catalogue (§3) is the only list of what fundlens reads. Every file on FEC's bulk-data page is in it or in §3's not-read table with a reason. | So "every FEC dollar" can be checked against FEC's own page. |
| Older builds | A live build transformed before one of this project's tables existed may lack it: gold and the snapshot read that cycle as having no rows of the table. A silver model always writes its partition, empty for a cycle before its source's first cycle. NEU-2352 builds the list of tables a live build may lack; NEU-2180's backfill rebuilds every cycle and then empties the list. | `load` rebuilds gold from every cycle's live build and the snapshot copies every one, and both refuse a build that lacks a table they read (v1 §3.4, §9), so without this the first new gold input breaks the weekly run. Rejected: writing a table into a published build in place, which changes a published build as nothing does today; a full backfill per milestone, which is four backfills. |

## 3. File catalogue

Bulk files are catalogued only in `fundlens.fec.files`: a file outside the file catalogue is neither downloaded nor read. v1 put six files in it (`cm`, `cn`, `ccl`, `indiv`, `pas2`, `oth`; v1 §4), which this project reads as v1 does. It adds the ten below.

- **Formats.** `zip`: a pipe-delimited text file with no header row, zipped, its columns named by a vendored header. `csv`: comma-delimited with a header row, not zipped. Bronze keeps either as downloaded (ADR-0002). NEU-2138 adds the `format` field and the CSV reader.
- **URL shapes**, each below `FEC_BULK_URL` (`https://www.fec.gov/files/bulk-downloads`). Three, where NEU-2138's ticket text names two (per cycle and undated), so its URL template per file must cover all of them:
  1. Per cycle, in the cycle's directory: `<yyyy>/<name><yy>.zip` and `<yyyy>/<name>_<yyyy>.csv`.
  2. Per cycle, in an undated directory: `data.fec.gov/leadership<yyyy>.csv`.
  3. One undated file for every cycle: `data.fec.gov/lobbyist.csv`.
- **First cycles are the page's.** Both tables below record FEC's bulk-data page, <https://www.fec.gov/data/browse-data/?tab=bulk-data>, as read on **2026-11-18**: the files it links, the URL each link has, and the earliest two-year range it links for each. FEC labels a file by its range (`2009–2010`); the first cycle is the range's even year. No file's contents were read for this section.

### 3.1 Read by this project

| File | On FEC's page as | Format | URL pattern | First cycle | Milestone | Catalogued by |
|---|---|---|---|---|---|---|
| `weball` | Candidate summary | zip | `<yyyy>/weball<yy>.zip` | 1980 | M1 | NEU-2142 |
| `webk` | PAC summary | zip | `<yyyy>/webk<yy>.zip` | 1996 | M1 | NEU-2142 |
| `committee_summary` | Committee summary | csv | `<yyyy>/committee_summary_<yyyy>.csv` | 2008 | M1 | NEU-2142 |
| `oppexp` | Operating expenditures | zip | `<yyyy>/oppexp<yy>.zip` | 2004 | M2 | NEU-2151 |
| `independent_expenditure` | Independent expenditures (24- and 48-Hour Reports) | csv | `<yyyy>/independent_expenditure_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `ElectioneeringComm` | Electioneering communications | csv | `<yyyy>/ElectioneeringComm_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `CommunicationCosts` | Communication costs | csv | `<yyyy>/CommunicationCosts_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `leadership` | Leadership PACs and sponsors | csv | `data.fec.gov/leadership<yyyy>.csv` | 2010 | M4 | NEU-2174 |
| `lobbyist` | Lobbyist/registrant committees | csv | `data.fec.gov/lobbyist.csv` | undated: one file, labelled 2007–2026 | M4 | NEU-2174 |
| `lobbyist_bundle` | Lobbyist bundled filings | csv | `data.fec.gov/lobbyist_bundle.csv` | undated: one file, labelled 2009–2026 | M4 | NEU-2174 |

- The page links every file above for each cycle from its first to 2026, with no gap.
- `weball` and `webk` have no header file on FEC's site: the page links one for `oppexp` and for each of v1's six, and `data_dictionaries/<file>_header_file.csv` was a 404 for both on 2026-11-05 (`docs/measurements/summary-files-2024.md`, its header-sources row). Their column lists are vendored from FEC's file descriptions (NEU-2142).
- `ElectioneeringComm` starts in 2010, not 2008 as the Linear tickets said until this spec was written: the page links nine files, 2010 to 2026, and `2008/ElectioneeringComm_2008.csv` was a 404 on 2026-11-18.
- `leadership` is linked for even years only. Whether a file exists for an odd year, and which cycles' rows each of the two undated files holds, is NEU-2173's to measure. This section states only what the page shows.

### 3.2 On FEC's page and not read

| File | On FEC's page as | Linked for | Why not |
|---|---|---|---|
| `webl` | House/Senate current campaigns | 1996– | `weball`'s rows, identical on every measure in 2024 and in 2004 (`docs/measurements/summary-files-2024.md` Q1, Q3, Q8; Decision 6) |
| `candidate_summary` | All candidates | 2008– | The sum of `committee_summary`'s own rows for a candidate's principal and authorized committees; candidate figures are summed from the committees fundlens credits to the candidate instead (the same measurement, Decisions 1 and 6) |
| `<yyyy>_overall_summary.csv`, `Contributions_by_Size.csv`, `Contributions_by_3Zip.csv` under `Presidential_Map/<yyyy>/` | Presidential candidate map exports | 2008, 2012, 2016, 2020, 2024 | FEC's aggregates of what the read files already hold (§1) |
| `Form2Filer` | New statements of candidacy (Form 2) | 2008– | No money |
| `Form1Filer` | New statements of organization (Form 1) | 2010– | No money |
| `FalseFictitiousFilings.csv` | False and fictitious filings | one file, labelled 2016–2026 | No money |
| Postgres dump files | Postgres database dump files | one listing, "1975 to present" | Schedules A, B and E and committee history again: they duplicate the bulk files |
| Senate filings at `docquery.fec.gov/senate/` | Senate unofficial electronic filings | 2008–2018 | Already in `indiv` |
| Daily `.fec` archives under `electronic/` | Electronically filed reports (.fec) | by day | §9: NEU-2181 decides |
| Daily `.fec` archives under `paper/` | Paper filed reports (.fec) | by day | §9: NEU-2181 decides |

The page has 26 download entries, each under its own label: v1's six, §3.1's ten and the ten rows above. A file FEC adds to the page later goes in one of the two tables, by the ticket that notices it.

## 4. Reported totals (M1)

FEC's own summary figures for every candidate and committee: total receipts and disbursements, cash on hand, debts, loans and unitemized (under $200) money, beside fundlens's itemized totals, with a coverage figure and a reconciliation check.

**Shared contracts** (the milestone's first, on the file catalogue and CSV files, is §3):

- Reported totals are FEC's figures, kept as filed, never summed with itemized money: a page shows "reported" and "itemized by fundlens" side by side, and `coverage = itemized / reported`.
- Source precedence per cycle, as NEU-2140 measured it (`docs/measurements/summary-files-2024.md`, Decisions 1, 2 and 6, which hold the figures). 2008–: committee figures are `committee_summary`'s, one row per committee, with `webk` only for a measure it leaves blank (Form 5 and Form 7 filers); candidate figures are the sum of the committees fundlens credits to the candidate. 1996–2006: `webk` for committees, `weball` for candidates. 1980–1994: `weball` only, with no committee-grain file. `webl` and `candidate_summary` are not read (§3.2).
- Unitemized individual money is a committee-level lump, never attributed to a donor.

**Filled by** NEU-2141, from that measurement: `reported_total`'s columns, the gold fields, coverage and the gift-size buckets.

## 5. Spending (M2)

Where committees' money goes: `oppexp` operating expenditures (2004–) as silver `operating_expenditure`, a rule-based spending category, spending totals on committee and race pages, an itemized spending list, and payee pages.

**Shared contracts:**

- A sub-itemized payment (credit card, reimbursement: `BACK_REF_TRAN_ID` to a parent) counts once: the parent or its children, never both, as NEU-2149's measurement decides. `MEMO_CD = 'X'` rows are not counted.
- Refunds and offsets net out, as receipts' refunds do in v1 (NEU-2073).
- Payees are grouped by `payee_key`, the normalizer organizations use (`normalize_employer`, ADR-0011), never resolved with Splink. A payee page lists who paid it, by cycle. The payee ADR will be 0012.
- `spending_category` is one of a fixed list (media, digital, fundraising, payroll, consulting, travel, events, administrative, legal/compliance, transfers/fees, other), from FEC's `CATEGORY` when filled, else a measured purpose-text rule.
- Spending is never a contribution and never in any receipt total.

**Filled by** NEU-2150, from NEU-2149's measurement.

## 6. Outside spending (M3)

Every kind of spending on a race by someone other than the campaign: independent expenditures from spenders that are not committees (the 24/48-hour file, 2010–), electioneering communications (2010–), corporations' and unions' communication costs (2010–) and party coordinated expenditures, shown by kind on race and candidate pages. Builds on v1 §4's `independent_expenditure` (NEU-2057) and its pages (NEU-2058).

**Shared contracts:**

- `outside_spending_kind` ∈ {`independent_expenditure`, `electioneering_communication`, `communication_cost`, `party_coordinated`}; support or oppose where the source gives it (electioneering communications have none).
- `pas2` stays authoritative for committees' independent expenditures. The 24/48-hour file adds only what `pas2` lacks: spenders not in `cm`, and pre-period-report timeliness only if NEU-2162's measurement shows no double count. Amended 24/48-hour rows are deduplicated to the latest amendment.
- An electioneering communication naming several candidates is split equally among them (FEC's `CALCULATED_CANDIDATE_SHARE`).
- Outside spending is never a contribution and never in a candidate's receipts.

**Filled by** NEU-2163, from NEU-2162's measurement.

## 7. Leadership PACs and lobbyist bundling (M4)

The money around a member: the leadership PAC each sponsors (`leadership`), PACs run by lobbyists or registrants (`lobbyist`), and contributions lobbyists bundled to campaigns, parties and leadership PACs (`lobbyist_bundle`, Form 3L).

**Shared contracts:**

- A leadership PAC's money stays the PAC's: linking it to its sponsor adds a link on the candidate's page, never a dollar to the candidate's totals.
- Bundled contributions are already counted as the individuals' gifts in `contribution`. A bundled total is shown as context and is never added to a receipt total.

The milestone ends with NEU-2180's backfill of every table this project adds, for every cycle FEC publishes its source for, which also empties §2's older-builds list.

**Filled by** NEU-2173, with its own measurement.

## 8. Public dataset

Adds to v1 §9, whose layout, manifest and license stand.

- Every silver table this project adds joins the dataset under `v1/`, as an additive change: a new table directory, a `CHANGELOG.md` entry, no `v2/`.
- The milestone's **spec ticket** (NEU-2141, NEU-2150, NEU-2163, NEU-2173) adds the table to v1 §9's table list.
- The **silver ticket** that builds the table adds it to the dataset in the same PR: `DATASET_TABLES` in `publish/dataset.py`, its column descriptions in `docs/dataset/columns.yaml`, `schema/<table>.json` by `task dataset:schema`, a `docs/dataset/CHANGELOG.md` entry, the README where it lists tables, and NEU-2352's list of tables a live build may lack. `tests/integration/test_dataset.py` already fails on a missing description or a stale schema. So a table is public from its first build. Rejected: the milestone's runbook ticket or one ticket at the project's end, both of which leave built tables unpublished for weeks.
- Until NEU-2180's backfill, a snapshot's manifest lists a new table with only the cycles whose live build has it (§2, older builds).
- A table that is context and in no total (M4's bundled contributions) is still published; its README entry says what it must not be added to.

## 9. Raw filings (M5)

A stub. NEU-2181's spike decides whether and how to ingest FEC's daily `.fec` filings for what no bulk file carries: Schedule C loans and Schedule D debts in detail, the contributors Form 5 spenders and Form 9 electioneering sponsors disclose, and Form 3L's named bundlers. It also decides whether paper-filed reports are part of that: Senate campaigns filed on paper until 2018, and nobody has measured what the paper archive holds that the bulk files lack. NEU-2206 (recovering the itemized receipts the bulk files omit) follows it.

**Filled by** NEU-2181's outcome.

## 10. Milestones (outline; detail in Linear)

1. **M1 Reported totals** — the project spec, CSV extraction, `weball`, `webk` and `committee_summary`, silver `reported_total`, coverage and reconciliation, gift-size buckets, the older-builds list (NEU-2352).
2. **M2 Spending** — `oppexp`, silver `operating_expenditure`, spending categories, committee and race spending, the itemized spending list, payee pages.
3. **M3 All outside spending** — the 24/48-hour file, electioneering communications, communication costs and party coordinated expenditures, by kind on race and candidate pages.
4. **M4 Leadership PACs and lobbyist bundling** — `leadership`, `lobbyist` and `lobbyist_bundle`; then the backfill of every new table for every cycle.
5. **M5 Raw electronic filings (spike)** — NEU-2181 only; work tickets follow its decision.
