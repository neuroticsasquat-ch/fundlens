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
| Payees and organizations | Grouped by normalized name, never resolved with Splink, no industry coding. | ADR-0011: the hard cases are corporate structure, not spelling, and industry coding is a project of its own. Payees: ADR-0012. |
| Public dataset | Every silver table this project adds joins the dataset snapshot (§8). | The resolved dataset is the product (v1 §1). |
| Files read | The file catalogue (§3) is the only list of what fundlens reads. Every file on FEC's bulk-data page is in it or in §3's not-read table with a reason. | So "every FEC dollar" can be checked against FEC's own page. |
| Older builds | A live build transformed before one of this project's tables existed may lack it: gold and the snapshot read that cycle as having no rows of the table. A silver model always writes its partition, empty for a cycle before its source's first cycle. The tables are the backfill-pending tables (`CONTEXT.md`), listed in `BACKFILL_PENDING` in `fundlens/paths.py` (NEU-2352); a silver ticket adds its table there. When no build of a load has one, its `silver.<table>` view is empty, typed from the table's committed dataset schema (`docs/dataset/schema/<table>.json`). NEU-2180's backfill rebuilds every cycle and then empties the list. | `load` rebuilds gold from every cycle's live build and the snapshot copies every one, and both refuse a build that lacks a table they read (v1 §3.4, §9), so without this the first new gold input breaks the weekly run. Rejected: writing a table into a published build in place, which changes a published build as nothing does today; a full backfill per milestone, which is four backfills. |

## 3. File catalogue

Bulk files are catalogued only in `fundlens.fec.files`: a file outside the file catalogue is neither downloaded nor read. v1 put six files in it (`cm`, `cn`, `ccl`, `indiv`, `pas2`, `oth`; v1 §4), which this project reads as v1 does. It adds the ten below.

- **Formats.** `zip`: a pipe-delimited text file with no header row, zipped, its columns named by a vendored header. `csv`: comma-delimited with a header row, not zipped. A CSV's header row must equal the entry's `columns` exactly, the same names in the same order; extract refuses a download that differs, and transform checks the bronze file again before reading it. FEC serves its CSVs in one dialect: the header row unquoted, every data field double-quoted (a blank one as `""`, read as NULL), LF line endings, no BOM. Bronze keeps either format as downloaded (ADR-0002); transform rewrites both as UTF-8 without NUL bytes under `scratch/` before reading them. NEU-2138 adds the `format` field and the CSV reader.
- **URL shapes**, each below `FEC_BULK_URL` (`https://www.fec.gov/files/bulk-downloads`), given by the entry's `url_pattern` (`{yyyy}` and `{yy}` its only placeholders; a zip without one is at `{yyyy}/<name>{yy}.zip`). Three:
  1. Per cycle, in the cycle's directory: `<yyyy>/<name><yy>.zip` and `<yyyy>/<name>_<yyyy>.csv`.
  2. Per cycle, in an undated directory: `data.fec.gov/leadership<yyyy>.csv`.
  3. One undated file for every cycle: `data.fec.gov/lobbyist.csv`.
- **FEC rewrites some historical CSVs daily.** `committee_summary_2008.csv` carried that day's `Last-Modified` on 2026-11-18; `leadership2010.csv` carried 2 January 2025. The change check is `Last-Modified` and size, as for zips, so re-extracting a historical cycle downloads those CSVs again and writes a new dated bronze object. The weekly run extracts only the current cycle.
- **First cycles are the page's.** Both tables below record FEC's bulk-data page, <https://www.fec.gov/data/browse-data/?tab=bulk-data>, as read on **2026-11-18**: the files it links, the URL each link has, and the earliest two-year range it links for each. FEC labels a file by its range (`2009–2010`); the first cycle is the range's even year. No file's contents were read for this section.

### 3.1 Read by this project

| File | On FEC's page as | Format | URL pattern | First cycle | Milestone | Catalogued by |
|---|---|---|---|---|---|---|
| `weball` | Candidate summary | zip | `<yyyy>/weball<yy>.zip` | 1980 | M1 | NEU-2142 |
| `webk` | PAC summary | zip | `<yyyy>/webk<yy>.zip` | 1996 | M1 | NEU-2142 |
| `committee_summary` | Committee summary | csv | `<yyyy>/committee_summary_<yyyy>.csv` | 2008 | M1 | NEU-2142 |
| `oppexp` | Operating expenditures | zip | `<yyyy>/oppexp<yy>.zip` | 2004 | M2 | NEU-2151 |
| `ie_24_48` | Independent expenditures (24- and 48-Hour Reports) | csv | `<yyyy>/independent_expenditure_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `ElectioneeringComm` | Electioneering communications | csv | `<yyyy>/ElectioneeringComm_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `CommunicationCosts` | Communication costs | csv | `<yyyy>/CommunicationCosts_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `leadership` | Leadership PACs and sponsors | csv | `data.fec.gov/leadership<yyyy>.csv` | 2010 | M4 | NEU-2174 |
| `lobbyist` | Lobbyist/registrant committees | csv | `data.fec.gov/lobbyist.csv` | undated: one file, labelled 2007–2026 | M4 | NEU-2174 |
| `lobbyist_bundle` | Lobbyist bundled filings | csv | `data.fec.gov/lobbyist_bundle.csv` | undated: one file, labelled 2009–2026 | M4 | NEU-2174 |

- The page links every file above for each cycle from its first to 2026, with no gap.
- `weball` and `webk` have no header file on FEC's site: the page links one for `oppexp` and for each of v1's six, and `data_dictionaries/<file>_header_file.csv` was a 404 for both on 2026-11-05 (`docs/measurements/summary-files-2024.md`, its header-sources row). Their column lists are vendored from FEC's file descriptions (NEU-2142).
- Every `oppexp` line, in every cycle, ends with a `|` after its last column, so it splits into 26 fields, the last empty: the entry is catalogued with `trailing_delimiter`, and `register_bulk` reads such a line under its 25 columns unchanged. The zip's one member is `oppexp.txt` in every cycle, and its dates are `MM/DD/YYYY`. Every cycle 2004 to 2026 was read through `register_bulk` on 2026-11-21 with no cast failing (`docs/specs/NEU-2151-oppexp-catalogue-extract-fixture.md` §5).
- The 24/48-hour file is catalogued as `ie_24_48`, not under FEC's name: a file's DuckDB view is named for its entry, and silver's `independent_expenditure` table would be refused beside a view of that name in every cycle's transform (DuckDB 2.0.0, tried 2026-11-24). Its `url_pattern` still writes FEC's name. `ie_24_48` is its view, its bronze folder, its `--file`, its `gold.meta.source_dates` key and its rows' `source_file` (`docs/specs/NEU-2164-outside-spending-csvs-catalogue-fixture.md` §1.1).
- Every cycle of the three outside-spending files, 2010 to 2026, was read through `register_bulk` on 2026-11-24 with no cast failing (`docs/specs/NEU-2164-outside-spending-csvs-catalogue-fixture.md` §5). The 24/48-hour file's header row is lower case. Dates are `DD-MON-YY` in `ie_24_48` and `ElectioneeringComm`, `YYYYMMDD` in `CommunicationCosts`. `CommunicationCosts` carries the itemized files' transaction key, so its view reads a repeated row once.
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

The rules below were written by NEU-2141 (`docs/specs/NEU-2141-reported-totals-spec-section.md`, which holds each decision's rejected alternatives and Appendix A, the checks made for it). "Q" and "Decision" numbers are NEU-2140's measurement's (`docs/measurements/summary-files-2024.md`). A rule that rests on no measurement says "asserted, not measured" and names the ticket that checks it.

### 4.1 Silver `reported_total`

Key `(cycle, committee_id)`. Columns, in order: `cycle, source, jurisdiction, source_file, committee_id, period_start, period_end`, then the 23 measures below. `source` is `fec` and `jurisdiction` `US`, as every silver table's (v1 §4).

Each measure is the file's figure as filed, `DECIMAL(14,2)`: a blank is NULL, a filed 0 is 0, and nothing is netted, corrected or derived from another measure except where the table says so. `INDV_CONTB = INDV_ITEM_CONTB + INDV_UNITEM_CONTB` fails for 166 committees in 2024, filers' arithmetic mostly (Q4c), so all three are stored as filed and no check enforces the identity. A reporting period is stored as filed too, even reversed: C00807263 files `CVG_START_DT` 20241004 and `CVG_END_DT` 20240131 in `committee_summary_2024.csv` (read 2026-11-19), so no check orders `period_start` against `period_end` (NEU-2395). Dates are `DATE`: `committee_summary` writes `YYYYMMDD`, the zips `MM/DD/YYYY`. `period_start` and `period_end` are the committee's **reporting period** (`CONTEXT.md`).

| Column | `committee_summary` (2008–) | `webk` (1996–2006; a blank measure's fill from 2008) | `weball` (`candidate_reported_total`, §4.2) |
|---|---|---|---|
| `period_start` | `CVG_START_DT` | — | — |
| `period_end` | `CVG_END_DT` | `CVG_END_DT` | `CVG_END_DT` |
| `receipts` | `TTL_RECEIPTS` | `TTL_RECEIPTS` | `TTL_RECEIPTS` |
| `disbursements` | `TTL_DISB` | `TTL_DISB` | `TTL_DISB` |
| `cash_on_hand_start` | `COH_BOP` | `COH_BOP` | `COH_BOP` |
| `cash_on_hand_end` | `COH_COP` | `COH_COP` | `COH_COP` |
| `debts_owed_by` | `DEBTS_OWED_BY_CMTE` | `DEBTS_OWED_BY` | `DEBTS_OWED_BY` |
| `debts_owed_to` | `DEBTS_OWED_TO_CMTE` | — | — |
| `individual_itemized` | `INDV_ITEM_CONTB` | — | — |
| `individual_unitemized` | `INDV_UNITEM_CONTB` | — | — |
| `individual_total` | `INDV_CONTB` | `INDV_CONTRIB` | `TTL_INDIV_CONTRIB` |
| `individual_refunds` | `INDV_REF` | `INDV_REFUNDS` | `INDIV_REFUNDS` |
| `party_contributions` | `PTY_CMTE_CONTB` | — | `POL_PTY_CONTRIB` |
| `other_committee_contributions` | `OTH_CMTE_CONTB` | `OTHER_POL_CMTE_CONTRIB` | `OTHER_POL_CMTE_CONTRIB` |
| `candidate_contributions` | `CAND_CNTB` | `CAND_CONTRIB` | `CAND_CONTRIB` |
| `candidate_loans` | `CAND_LOAN` | `CAND_LOANS` | `CAND_LOANS` |
| `other_loans` | `OTH_LOANS`; where that is blank, `TTL_LOANS` less `CAND_LOAN` (a blank as 0) | `TTL_LOANS_RECEIVED` less `CAND_LOANS` | `OTHER_LOANS` |
| `candidate_loan_repayments` | `CAND_LOAN_REPYMNT` | `CAND_LOAN_REPAY` | `CAND_LOAN_REPAY` |
| `other_loan_repayments` | `OTH_LOAN_REPYMTS` | `LOAN_REPAY` | `OTHER_LOAN_REPAY` |
| `transfers_in` | `TRANF_FROM_OTHER_AUTH_CMTE` | `TRANS_FROM_AFF` | `TRANS_FROM_AUTH` |
| `transfers_out` | `TRANF_TO_OTHER_AUTH_CMTE` | `TRANF_TO_AFF` | `TRANS_TO_AUTH` |
| `independent_expenditures` | `INDT_EXP` | `IND_EXP` | — |
| `party_coordinated` | `COORD_EXP_BY_PTY_CMTE` | `PTY_COORD_EXP` | — |
| `operating_expenditures` | `OP_EXP + TTL_OP_EXP` (a blank as 0; NULL when both are blank) | — | — |
| `federal_funds` | `FED_FUNDS` | — | — |

- **What the mapping rests on.** `individual_total` holds itemized plus unitemized money in all three files (Decision 3; Q4). `committee_summary` and `webk` agree within $1 on receipts for 9,843 of 9,845 shared committees, and on debts, other committees' contributions, transfers in and refunds for every one (Q2a). The column names are `committee_summary_2024.csv`'s own header row, read 2026-11-18, and the zips' are FEC's file descriptions (the measurement's header-sources row). The loan, repayment and operating-expenditure rows rest on NEU-2141's Appendix A: `TTL_LOANS = CAND_LOAN + OTH_LOANS` at 911 of 912 candidate committees with loans, while other committees, whose Form 3X has one loans line, leave `OTH_LOANS` blank (103 of 109); `TTL_LOAN_REPYMTS` is the two repayment figures added at 586 of 588, and is not stored; Form 3 and 3P filers fill `OP_EXP` and Form 3X filers `TTL_OP_EXP`, and 78 committees fill both with different figures in 2024, the largest campaigns turned PACs, each column holding a different form's reports (the two together inside `TTL_DISB` at every one). **Asserted, not measured:** that `webk`'s `LOAN_REPAY` leaves out candidate loan repayments, and its `IND_EXP` and `PTY_COORD_EXP` against `committee_summary`'s; NEU-2143 compares each on 2024's shared committees and amends this table if one differs.
- **Rows, 2008 on.** One row per `CMTE_ID` of `committee_summary` that is a committee of the cycle in silver `committee`. The file repeats a committee once per linked candidate (65 committees, 136 rows in 2024, Q1), and now and then lists a committee twice over different periods: `C00830356` in 2026, once from 2025-01-01 and once from 2026-07-15, both to 2026-10-15 (NEU-2454). The transform keeps the row covering the cycle to date, the earliest `CVG_START_DT` and then the latest `CVG_END_DT`, and fails if the committee's rows over that period differ in anything but `CAND_ID` and `Link_Image`. Each measure is `committee_summary`'s, except that a Form 5 filer (type I) or Form 7 filer (type C) takes each measure its row leaves blank from `webk`, where `webk` holds the committee: a Form 5 filer's `committee_summary` row carries only `INDT_EXP`, and a Form 7 filer's only a communication-cost figure this table does not hold (204 and 68 committees in 2024, Q2f2; NEU-2141 Appendix A). No other committee's blank is filled (NEU-2143): a Form 3X committee's blank candidate-contribution and candidate-loan lines are lines its form lacks, which `webk` gives as 0, and filling them would make nearly every PAC's row `committee_summary+webk`. `source_file` is `committee_summary+webk` when any measure came from `webk`, else `committee_summary`. A committee only in `webk` gets no row: the 2,248 committees only in `webk24` carry no money but one bad Form 5 record (Q1). 2024: 13,995 committees, 13,994 of them silver committees (Q1i).
- **Rows, 1996–2006.** One row per `webk` committee in silver `committee`, `source_file` `webk`. House and Senate campaign committees have none: `webk04` holds 54 candidate committees (Q8).
- **Rows, 1980–1994.** None. The model still writes its partition, empty (§2, older builds).
- A row whose every measure is blank is kept: FEC lists the committee and reports nothing.
- **Not held:** FEC's `FED_CAND_CMTE_CONTB` (Form 3X line 23), which reconciles with neither the gross nor the net 24Ks (Decision 8), `OTHER_RECEIPTS`, and Form 7's `TTL_COMMUNICATION_COST`, which M3 does not hold either (§6.2). Adding a measure later is an additive dataset change.

### 4.2 Silver `candidate_reported_total`

Key `(cycle, candidate_id)`. Columns as `reported_total`'s with `candidate_id` in place of `committee_id`. Written from `weball`, the mapping's last column, for 1980–2006: one row per `CAND_ID` that is a candidate of the cycle in silver `candidate`, `source_file` `weball`. A measure `weball` lacks is NULL: `period_start`, `debts_owed_to`, the itemized and unitemized split, `independent_expenditures`, `party_coordinated`, `operating_expenditures`, `federal_funds`. From 2008 the partition is empty: candidate figures are summed from `reported_total` (§4.3), so the dataset never holds a 2008+ candidate figure the site contradicts.

`weball`'s rows are not additive across candidates: it lists a committee's money under each candidate id linked to it (248 rows in 2024, $789.4M, Q3h3). Before 2008 that stands as filed. A candidate alias has no gold row (v1 §7.1), so its repeat is in no race; a person's ids for two different races each keep their row.

`webl` and `candidate_summary` are not read (§3.2).

### 4.3 Candidate figures

- **2008 on: the sum of the candidate's credited committees' `reported_total` rows** (Decision 1). The credited committees are those `04_contribution.sql`'s `linked` rule gives the candidate (v1 §4): linked P or A, or the committee `candidate.principal_committee_id` names; a committee linked to two candidates is the principal link's, then the lower `candidate_id`'s; a candidate alias is credited none. Each committee has one candidate, so the figures add up across candidates as FEC's candidate files do not. Against `candidate_summary.Total_Receipt` the sum is within 1% for 2,235 of 2,255 candidates (99.11%; 99.95% of those with receipts), every mismatch explained (Q3g, Q3h).
- A measure is the sum over the credited committees that have it, NULL when none does. `reported_period_start` is the earliest, `reported_period_end` the latest.
- **Transfers between a candidate's own committees are not netted out**: each is in one committee's disbursements and another's receipts. FEC does not net them either: `weball` equals the committees' sum exactly for all 2,118 House and Senate candidates with a credited committee (Q2g, Q2h).
- **A handoff's committee is the second candidate's alone** (`fec/handoffs.csv`'s `to_candidate_id`), whole, in the cycle of the handoff: a cycle-to-date row cannot be split at `handoff_date`. In 2024 `C00703975`'s $1,175,189,365 of receipts is Harris's, and Biden has no credited committee, so his reported fields, `itemized_total` and `coverage` are NULL beside $73,961,689 of itemized individual money (Q3k, Q3n). FEC's files list the row under both. Rejected: both candidates (the race counts $1.175B twice), neither (the largest campaign of 2024 shows no cash on hand), and apportioning by itemized share (fundlens's estimate, not FEC's figure).
- **A campaign turned PAC counts whole.** A committee credited through `principal_committee_id` alone, which `ccl` no longer designates P or A, adds its whole cycle-to-date row, what it raised after converting included: ten candidates in 2024, $523.3M, $495.9M of it Trump's NEVER SURRENDER (`C00828541`) and $23.2M Kunce's Heartland Patriots (Q3h). Itemized money follows the same rule with no date cut, so coverage compares like with like. `candidate_cycle.reported_includes_converted_committee` is true for such a candidate, so a page can say why its figure differs from FEC's, which credits these committees to no one.
- **Before 2008:** the candidate's `candidate_reported_total` row as filed. The flag is false.

### 4.4 Gold fields

The `reported_*` fields and `coverage` are NULL where there is no reported row, or the cycle's file lacks the measure, never 0. `itemized_total` is fundlens's own figure, and has its own rule below.

| Table | Added |
|---|---|
| `committee_cycle` | `reported_<measure>` for each of the 23 measures; `reported_period_start`, `reported_period_end`, `reported_source_file`; `itemized_total`; `coverage` |
| `candidate_cycle` | The same, by §4.3, and `reported_includes_converted_committee`. `reported_source_file` is `committee_summary` from 2008 and `weball` before |
| `race_candidate` | `reported_receipts`, `reported_disbursements`, `reported_cash_on_hand_end`, `reported_debts_owed_by`, `coverage`: the candidate's `candidate_cycle` values |
| `race` | `reported_cash_on_hand`: the sum of its candidates' `reported_cash_on_hand_end`, NULL when none has one |

- **`itemized_total`** (`CONTEXT.md`). A committee's is `total_individual + total_from_organizations − total_refunds` (v1 §7.1; NEU-2265), never NULL: individuals' and organizations' money on line 11(a)(i), gross of refunds, which is what `INDV_ITEM_CONTB` counts. A candidate's is the sum of its credited committees' (§4.3), NULL when it has none. It is a comparison figure: it is in no race total and no top list, and `total_individual` is unchanged. It is the one candidate figure that includes organization money; it reads `committee_cycle`, not `organization_receipt`, so ADR-0011's "only gold readers" stands.
- **`coverage`** (`CONTEXT.md`) = `itemized_total ÷ reported_individual_itemized`, a ratio (0.9412), not a percentage, stored as computed.
  - The numerator is individual plus organization money (Decision 4): within 1% of FEC's itemized figure at 5,114 committees against 4,440 for individual money alone, and at super PACs 802 against 386 (Q5g). Those counts were taken net of refunds; the numerator is gross because `INDV_ITEM_CONTB` is (NEU-2265: VIVEK 2024 reads −2.06% net, −0.17% gross). On the gross basis, on 2024's first published build with reported totals (`20261119T212247Z`): within 1% at 6,525 of 8,721 committees with a coverage, and at super PACs 893 of 1,035; 131 over 1% (`docs/runbooks/reported-totals-run.md`, Log 2026-11-20).
  - NULL when `reported_individual_itemized` is NULL or 0; so NULL before 2008, whose files have no itemized figure (Q8), and for Form 4 and Form 5 filers.
  - NULL at a conduit (`committee.is_conduit`): ActBlue's and WinRed's `INDV_ITEM_CONTB` ($3.76B and $1.61B in 2024) include the earmarks fundlens counts at the recipient (ADR-0004; Q5m).
  - It can exceed 1. Where a filer put counted money on a line the bulk file does not show, fundlens is over (71 committees, $10,791,881, after NEU-2276; Q6 after NEU-2276); where FEC adds a superseded filing to its amendment, FEC is over (NEU-2196). Shown as it is. Rejected: capping at 1 (presents unmatched money as matched), and NULL above 1.01 (a committee flips between a figure and nothing as filings are amended).
  - A candidate's is summed over its credited committees on both sides: their `itemized_total`s over their reported itemized figures, so Harris's spans the whole of `C00703975`. Candidate committees take ORG-typed gifts (812 within 1% of FEC with them, 728 without, Q5g).
- A hybrid PAC's `total_individual` and `total_from_organizations` hold its contribution account alone (v1 §7.1), which is what its `INDV_ITEM_CONTB` counts, so its coverage needs no special rule.

### 4.5 Reconciliation

Gold `reconciliation (committee_id, cycle, measure, fundlens, reported, ratio)`, key `(committee_id, cycle, measure)`: the committees where fundlens's figure exceeds FEC's reported one by more than 1%. Built by every load, published, and **never failing the build**: FEC's figures lag amendments, and a filer's line choice is not fundlens's to fix.

- M1 writes one measure, `individual_itemized`: `fundlens` is `itemized_total`, `reported` is `reported_individual_itemized`, `ratio` is `fundlens ÷ reported`. The `measure` column is there for later milestones.
- A committee is listed when `reported` is not NULL, it is not a conduit, and `fundlens − reported > 0.01 × reported`. A reported 0 beside fundlens money is listed with `ratio` NULL: a 0 is a figure FEC gives. A blank reported figure is not listed.
- No dollar floor, as the measurement's excess list had none. Over only: a shortfall is coverage below 1.
- 2008 on, since no earlier file has the measure.
- The measurement's list, on the net basis and before its bugs were fixed, was 725 committees and $1.94B (Q6); NEU-2192 to NEU-2199 and NEU-2276 took the diagnosed causes out, leaving 71 unexplained. On 2024's first published build with reported totals (`20261119T212247Z`, gross basis), the table holds 163 rows and $55,349,367 over, 23 of them a reported 0. Of its top ten, seven are a filer's line choice (lines 12, 13 and 15) and three are filed: NEU-2400, NEU-2401, NEU-2402 (`docs/runbooks/reported-totals-run.md`, Log 2026-11-20).

### 4.6 Gift sizes

Gold `candidate_gift_size (candidate_id, cycle, bucket, amount, donors)`, key `(candidate_id, cycle, bucket)`.

| `bucket` | Holds | `donors` |
|---|---|---|
| `unitemized` | The candidate's `reported_individual_unitemized`, as filed | NULL |
| `200_or_less` | Donors whose gift size is $200 or less, those netting $0 or less among them | their count |
| `under_500` | over $200 and under $500 | their count |
| `under_1000` | $500 and under $1,000 | their count |
| `under_2000` | $1,000 and under $2,000 | their count |
| `2000_or_more` | $2,000 or more | their count |

- **Gift size** (`CONTEXT.md`) is a donor's net gifts to one candidate in the cycle: the sum, per `donor_id`, of the rows `candidate_cycle.total_individual` counts for that candidate (v1 §4: not self-funding, not other-lines money, refunds netting). A donor's aggregate decides the bucket: 20 gifts of $50 are one `under_2000` donor. `amount` is the bucket's donors' gift sizes added up.
- The five itemized buckets add up to `candidate_cycle.total_individual`, and a gold check fails the build if they do not. A candidate with a counted contribution has all five rows, a bucket with no donor at 0.
- The `unitemized` row exists only where the candidate has a reported unitemized figure: 2008 on. It is FEC's lump as filed, beside the itemized buckets, never added to one (the milestone's contract). A handoff's first candidate has none.
- A cycle loaded before `resolve` has no `donor_id`s and so no itemized bucket rows, as its `contributor_count` is NULL (v1 §7.1).
- Organization money is in no bucket: an organization is not a donor.
- Rejected: buckets by single gift (20 gifts of $50 are one $1,000 donor, not twenty $50 ones); the aggregate per committee, as FEC's itemization threshold is taken (one person in two buckets for one candidate); folding itemized donors at $200 or less into the unitemized bucket, as FEC's presidential `Contributions_by_Size.csv` does (**asserted, not measured**; §1 allows it as a check, never a source).

### 4.7 What each cycle range has

| | 2008– | 1996–2006 | 1980–1994 |
|---|---|---|---|
| Committee reported totals | every measure; Form 5 and Form 7 filers' from `webk` | `webk`'s measures; none for House and Senate campaign committees | none |
| Candidate reported totals | credited committees' sum | `weball`'s measures | `weball`'s measures |
| Missing measures | — | `period_start`, `debts_owed_to`, itemized and unitemized, `operating_expenditures`, `federal_funds`; and `party_contributions` (committees), `independent_expenditures` and `party_coordinated` (candidates) | as 1996–2006 |
| `coverage`, `reconciliation` | yes | NULL, no rows | NULL, no rows |
| Gift sizes | six buckets | five itemized | five itemized |

A page shows a missing figure as "not reported", never 0 (NEU-2146).

### 4.8 Dataset and older builds

`reported_total` and `candidate_reported_total` join the public dataset (§8): NEU-2143 adds both to `DATASET_TABLES`, `columns.yaml`, the schemas, the changelog, the README and `paths.BACKFILL_PENDING` in the PR that builds them. Their README entry says a reported total is never to be added to `contribution` amounts.

## 5. Spending (M2)

Where committees' money goes: `oppexp` operating expenditures (2004–) as silver `operating_expenditure`, a rule-based spending category, spending totals on committee and race pages, an itemized spending list, and payee pages.

**Shared contracts:**

- A sub-itemized payment counts once, at its parent, in every cycle: the parent counts whatever its memo code, and a sub-item never does. Every other `MEMO_CD = 'X'` row is not counted.
- Refunds and offsets net out: amounts are summed as filed.
- Payees are grouped by `payee_key`, the rule that makes an organization key (`organization_key`, ADR-0011), never resolved with Splink. A payee page lists who paid it, by cycle. A person, or a name that names nobody, has no page (ADR-0012).
- `spending_category` is one of a fixed list of 15, from a measured purpose-text rule, else from FEC's `CATEGORY` where the code is one filers use reliably, else `other`.
- Spending is never a contribution and never in any receipt total.

The rules below were written by NEU-2150 (`docs/specs/NEU-2150-spending-spec-section.md`, which holds each decision's rejected alternatives). "Q" and "Decision" numbers are NEU-2149's measurement's (`docs/measurements/oppexp-2024.md`). A rule that rests on no measurement says "asserted, not measured" and names the ticket that checks it.

### 5.1 Silver `operating_expenditure`

`sql/silver/12_operating_expenditure.sql` (NEU-2152), from `oppexp`. Key `(cycle, source, source_record_id)`. `source` is `fec` and `jurisdiction` `US`, as every silver table's (v1 §4).

Columns, in order:

| Column | From | Notes |
|---|---|---|
| `cycle`, `source`, `source_record_id`, `jurisdiction` | `SUB_ID` | Unique in the file (Q1a) |
| `committee_id` | `CMTE_ID` | The committee that paid |
| `candidate_id` | — | Nullable. `04_contribution.sql`'s credit rule applied to `committee_id` and `date` (v1 §4; project spec §4.3): linked P or A, or the committee `candidate.principal_committee_id` names; a handoff's committee by the row's date; a candidate alias is credited none |
| `payee_name` | `NAME` | As reported |
| `payee_key` | — | `organization_key(NAME)`, evaluated once per distinct name. NULL only for a row with no name (91 counted rows, $34,042, Q9c) |
| `payee_city`, `payee_state`, `payee_zip` | `CITY`, `STATE`, `ZIP_CODE` | As reported |
| `payee_is_person` | — | §5.4 |
| `amount` | `TRANSACTION_AMT` | `DECIMAL(14,2)`, as filed, negative amounts included (§5.2) |
| `date` | `TRANSACTION_DT` | `DATE` from `MM/DD/YYYY`. A spender's impossible year is kept as filed (years 1201 to 9201 appear in every cycle, Q2) |
| `purpose` | `PURPOSE` | As reported |
| `fec_category` | `CATEGORY` | FEC's code as a three-character string: one written without its leading zeros (`1`, `01`) is the code it pads to. Any other value is kept as filed |
| `spending_category`, `category_source` | — | §5.3 (`transform.spending`, NEU-2153), evaluated once per distinct (`fec_category`, `PURPOSE`) pair |
| `election_code` | `TRANSACTION_PGI` | |
| `report_type`, `amendment_indicator` | `RPT_TP`, `AMNDT_IND` | |
| `memo_code`, `memo_text` | `MEMO_CD`, `MEMO_TEXT` | |
| `entity_type` | `ENTITY_TP` | As filed, blank as NULL |
| `tran_id`, `back_ref_tran_id` | `TRAN_ID`, `BACK_REF_TRAN_ID` | |
| `parent_source_record_id` | — | Nullable. The `source_record_id` of the row on the same committee and filing whose `TRAN_ID` is this row's `BACK_REF_TRAN_ID`, other than the row itself: a row naming its own `TRAN_ID` is no sub-item (4 rows in 2024, the measurement's setup). Set, the row is a sub-item (`CONTEXT.md`). Where a filing holds that `TRAN_ID` on two rows, the lower `SUB_ID` (none does in 2024 once repeated rows are read once, Q5d) |
| `image_num`, `file_num` | `IMAGE_NUM`, `FILE_NUM` | |
| `is_in_kind` | — | §5.4 |
| `counted` | — | §5.2 |

Not held: `RPT_YR`, `LINE_NUM`, `FORM_TP_CD`, `SCHED_TP_CD`, `CATEGORY_DESC`. The file holds three lines and nothing else, Form 3 line 17, Form 3P line 23 and Form 3X line 21(b), plus 47 rows on a line written `21` (Q1d). Adding a column later is an additive dataset change.

**Rows.** Every `oppexp` row whose committee is a committee of the cycle in silver `committee`, except:

- A **repeated row** (`CONTEXT.md`) is read once: `register_bulk` drops the copies, since `oppexp` has all four `TRANSACTION_KEY` columns. 2,943 rows, $3,238,816, on 11 filings in 2024; the raw filings hold each transaction once (Q5).
- A row on a **superseded filing** is dropped, as `contribution` drops it: `FILE_NUM` in `04_contribution.sql`'s `superseded_filing` set, the receipt side's, alone (Decision 2). 47 filings in 2024, 26 of them with `oppexp` rows, $15,117,610 of counted spending (Q6). The model must run where that set is in scope, or build it from the same three statements. A payment-side rule would add 23 filings and $124,469, of which 10 filings and $105,184 are a different report repeating payments, not an amendment; neither it nor its same-report variant (13 filings, $19,286) is adopted (Q6e, Q6e2).
- A row whose filer `cm` lacks is dropped, as `independent_expenditure`'s is: 3 filers, 18 rows, $121,715,789 in 2024, $121.2M of it one filer's four rows paid to itself (Q1h, Q9b).

No row is dropped as an overlap: no `oppexp` row shares a `SUB_ID`, or a filing, `TRAN_ID` and amount, with `pas2`, `oth` or `indiv`, and none is a silver `committee_transfer` or `independent_expenditure` row (Q7, Decision 3). There is no paper row to treat differently: no cycle has more than 4 rows without a `TRAN_ID` (Q4c).

Every sub-item and every memo row is kept, with `counted` false, so the itemized list can show a card bill's charges without counting them twice. Rejected: dropping them, and a second table for them.

**2024 on this contract.** The measurement counted 1,550,230 rows and $9,715,514,602 (R4, every filer). Of those, 5 rows and $121,230,310 are at filers `cm` lacks (Q8a, Q11e). So silver's 2024 partition should count **1,550,225 rows and $9,594,284,292**. This spec derived both by subtraction; NEU-2152's definition of done is within 1% of them.

**Checks** (NEU-2152): `silver_operating_expenditure_key.sql` (key unique); `..._committee.sql` (committee in `committee`); `..._counted_once.sql` (no row with `parent_source_record_id` set is counted); `..._no_contribution.sql` (no `source_record_id` is in `contribution`, `committee_transfer`, `organization_receipt` or `independent_expenditure`; the measurement found none, Q7).

**Memory.** The table holds 0.68 GiB in DuckDB for 2024, and nothing once written. The transform writes it first and drops each table once written (`WRITTEN_FIRST` in `transform/runner.py`, NEU-2152), so it is gone before `contribution`'s write, the transform's peak (Q1, Decision 7). The peak is not the sum of the tables. Build `20261121T211606Z` peaked at 27.44 GiB in that write, 12.56 GiB under the container's 40 GiB. DuckDB spilled 0.21 GiB during it, and about 1.7 GiB of the process sat outside DuckDB as it began: memory the allocator kept from earlier queries and writes. The same code's peak moves 2 GiB between runs. So a new silver table is measured by DuckDB's own figure across its model in the transform's `memory after <step>` lines, not by the run's peak (NEU-2408, `docs/capacity.md`).

### 5.2 What counts

`counted` is the one flag every total reads:

1. A row with `parent_source_record_id` set, a **sub-item**, is not counted. This includes a row that is both a sub-item and a parent, the middle of a chain: chains are 8 rows, $10,804, in 2024, and none of a chain counts but its top parent (Q3f).
2. Otherwise, a row that some sub-item names as its parent is counted, **whatever its memo code**. 30 parents are memo rows in 2024, $164,432 (Q3m). This is the one exception to "memo rows are not counted".
3. Otherwise, a row is counted when `MEMO_CD` is not `X`. That covers an ordinary payment, and a row with `BACK_REF_TRAN_ID` filled whose parent is not in the file (7,284 in 2024, 5,552 of them naming a receipt on their filing: in-kind outlays, §5.4; Q3a, Q7c).

This is the measurement's R2, "parent always" (Decision 1), applied in every cycle FEC publishes the file for.

- **Why the parent.** 80,249 parents carry 670,054 sub-items in 2024. A parent is fully itemized when its sub-items add up to it within $1.00. Fully itemized parents hold $250,483,113 of the $524,208,828 parents carry, 47.78%: under the 50% bar NEU-2149's spec set for counting sub-items instead (Q3j). Card bills are what does not add up: 28.27% of card parents' dollars are fully itemized, against 71.25% of other parents' (Q3b).
- **One rule for every cycle.** The bar is met in ten of the twelve cycles, from 51.09% (2022) to 84.68% (2008), and fails in 2016 (47.73%) and 2024 (Q2c). It is not applied per cycle: a payee's totals would be built by different rules from one cycle to the next, and the current cycle could change rules as filings arrive.
- **What it costs.** No sub-item reaches a payee: $503.0M in 2024, $250.5M of it under fully itemized parents. Card issuers keep $192,903,671 of card bills that are not fully itemized (Q3j). A payee's total is what committees reported paying that name directly.
- **Against FEC's own rule** (non-memo rows), parent always differs by $194,596 in 2024 (Q3l, Q3m).
- **Sign: as filed** (Decision 4). A negative row subtracts, and nothing is negated or dropped for its purpose. Negative rows net −$191.5M of 2024's counted spending, $109.1M of it super PACs moving a payment to Schedule E, which then counts once, in `independent_expenditure`. Counting every amount positive would add $383.1M, and dropping the negatives $191.5M (Q10g). This is the contract's "refunds and offsets net out".
- **Against FEC's reported figure.** At the 9,909 committees with a reported figure above $0, counted spending is $9,594,311,329 against $9,916,558,902 reported: the median committee is at 98.76%, and 63 are more than 1% over, by $1.09M (Q11). Itemized spending sits below the reported figure by design: payments of $200 or less in a year are unitemized. Parties are at 83.83%: the file has no row on Form 3X line 21(a), their shared federal and nonfederal spending (Q1d, Q11b).

### 5.3 Spending category

Every row has one `spending_category` (`CONTEXT.md`), counted or not, from this list:

| Slug | Holds |
|---|---|
| `media` | Paid advertising in broadcast, cable, satellite, radio, print and out of home, its production and placement; an ad or "media" buy whose medium is unnamed |
| `digital` | Online advertising, text and email messaging, websites and hosting, digital organizing and consulting, campaign data and voter-file services |
| `mail` | Direct mail and printed material: design, printing, postage and lettershop, whether it persuades voters or asks them for money |
| `fundraising` | The cost of raising money: fundraising consultants and commissions, online fundraising, list rental and acquisition, telemarketing, merchandise, a fundraising event's costs where the purpose names fundraising |
| `payroll` | Pay to staff and its costs: salary, payroll taxes and withholding, benefits, payroll processors |
| `consulting` | General, political, strategic, management and communications consulting whose purpose names no other category |
| `field` | Voter contact in person and by phone: canvassing, field and relational organizing, voter registration, paid calls to voters |
| `polling_research` | Polling, surveys and focus groups, and opposition and policy research |
| `travel` | Air and ground travel, lodging, mileage, meals while travelling |
| `events` | Putting on an event: venue, production and staging, audio-visual, catering, advance |
| `administrative` | Running an office: rent, utilities, software, equipment, supplies, insurance other than staff's, taxes other than payroll's, security |
| `legal_compliance` | Legal services, compliance, accounting and FEC reporting |
| `transfers_fees` | Money passed on (transfers, contributions, donations, refunds, loan repayments) and fees charged per payment processed: merchant, card-processing, conduit and bank fees |
| `credit_card` | A card bill, counted as the bill: what it bought is itemized, if at all, only in sub-items |
| `other` | Anything else, and a purpose that names nothing bought (`SEE MEMO`, `OPERATING EXPENDITURE`) |

The milestone's 11 became 15 by the 2% bar NEU-2149's spec set: `mail` (7.39% of the labelled set's dollars), `field` (2.62%), `polling_research` (2.62%) and `credit_card` (2.38%) (Q8f). The definitions and the eleven tie-breaks (T1 to T11) are the measurement's Q8; the classifier follows them.

**Precedence**, first that applies:

1. **The purpose rule** (NEU-2153): an ordered list of patterns over the purpose, upper-cased, trimmed and with runs of whitespace made one space; the first match wins. `category_source = 'purpose_rule'`.
2. **A trusted FEC code**: 002 `travel`, 004 `media`, 005 `polling_research`, 011 `transfers_fees`, 102 `media`, 106 `polling_research`. `category_source = 'fec'`.
3. `other`, with `category_source = 'unclassified'`.

- **Why the purpose first.** `CATEGORY` is filled on 28.94% of counted rows and 16.20% of counted dollars (Q8a), and code 001 is a catch-all: filers write it on payroll ($121.1M), media ($65.8M), digital, mail, fundraising, consulting and legal work alike, so the labels agree with it on 3.57% of its $511,096,243 (Q8g, Q8h). The six trusted codes agree with the labels on 84.98% to 100% of their dollars. Even 004 cannot tell `digital` from `media`, which the purpose can.
- **Codes not trusted**, read by purpose alone: 001 (3.57%), 003 (64.58%), 006 (74.95%), 007 (51.75%), 101, 104 (6.82%), 107 (16.58%), and 008, 009, 010, 012, 103 and 105, which have too few labelled dollars to judge (Q8g). Trusting another code is a measured change.
- `fec_category` keeps FEC's code whatever the precedence did with it. FEC's 19 codes and what each means are the measurement's Decision 5 table.
- The test set is `tests/fixtures/spending/purpose_labels_2024.csv`: 200 purposes holding 76.75% of counted dollars, 35 of them judgement calls with reasons. The rule (`fundlens.transform.spending`, NEU-2153) classifies all 200 as labelled, 100% of their dollars against a 90% bar; `tests/unit/test_spending.py` asserts the score and lists any miss. The rules were written with the set in view, so that is a training score: the check on the purposes nobody labelled is the share left `unclassified`, which every transform logs. On FEC's 2024 file, read with §5.2's counting rule outside the pipeline (NEU-2153, 2026-11-21; repeated rows and superseded filings not dropped), it is 3.79% of counted dollars, $363.9M, against the 10% bar; the trusted codes decide 0.11%. Most of it names nothing bought: in-kind outlays ($53.3M on `IN-KIND CONTRIBUTION` alone) and crypto received ($63.5M on three rows), `SEE MEMO` and its variants, and bare `REIMBURSEMENT`.
- A purpose that names nothing bought (`SEE …` at its start, `IN-KIND` anywhere, crypto `NOT LIQUIDATED`, `OPERATING EXPENDITURE`) stops the rule unmatched, so a trusted code still decides it. A purpose naming an in-kind outlay is `other` whatever else it names (T11), unless a trusted code decides it; an in-kind outlay by structure alone (§5.4) takes its purpose's category, since it keeps its category.

**Method note** (for the methodology page). Every operating expenditure gets one of fifteen spending categories. FEC's own category code is blank on most spending and, where filled, its commonest code is a catch-all filers put on payroll, ads and legal bills alike, so fundlens reads the purpose the filer wrote instead: an ordered list of word patterns, tried first to last on the purpose in capitals, the first that matches deciding. The order settles what a purpose naming two things is: what the money was for beats the channel it went through ("digital fundraising" is fundraising), a named kind of consulting is that kind ("media consulting" is media), and pay, per-payment fees and card bills are recognized before anything else. Where the purpose says nothing about what was bought, FEC's code decides if it is one of the six codes that agree with hand-labelled purposes on about 85% or more of their dollars (travel, advertising, polling, contributions, and the presidential media and polling codes); otherwise the payment is "other". The rules were checked against 200 hand-labelled purposes holding three quarters of 2024's spending, and classify all of them as labelled; under 4% of 2024's counted dollars end up "other" for want of a rule or a trusted code. A card bill is its own category: what the card bought is listed under it, if the filer itemized it, and not counted again. Each payment's `category_source` says which of the three decided it.

### 5.4 Payees

- **Payee key** (`CONTEXT.md`, ADR-0012). `payee_key = organization_key(payee_name)`, the function organizations use: `normalize_employer`, falling back on the cleaned name. Exact grouping, no linkage, across committees and cycles. 105,313 raw names become 98,975 keys in 2024; the top 100 keys hold 52.37% of counted dollars and the top 1,000 hold 80.26% (Q9a). Read by eye, the top 100 hold no wrong merge and three split firms (`AX MEDIA` and `AXMEDIA`; `TEAM DIRECT` and `TEAMDIRECT`; `MISSIONWIRED`, `ANNE LEWIS STRATEGIES` and `ANNE LEWIS STRATEGIES LLC DBA MISSIONWIRED`, and a fourth key, `MISSION WIRED`, outside the top 100), each joined by an alias in `resolve/aliases.yaml`, filed as a Bug from NEU-2160's payee review (Q9b). That review's scan of the top 1,000 keys with spaces removed found nine more firms written with and without a space (`ONMESSAGE`, `WINRED`, `AB DATA`…) and five whose legal name, trade name and DBA spelling are separate keys (`IMPACT RESEARCH` is also `ALG POLLING`). NEU-2463 aliases all fourteen; `WINRED` and `WINRED TECHNICAL SERVICES` stay two firms.
- **Payee rows.** The rows payee figures read: `counted`, `payee_key` not NULL, `is_in_kind` false. "Payee dollars" below are their net amount.
- **A person** (`payee_is_person`, per row): `entity_type` is `IND` or `CAN`; or it is blank, the row has a name, and `is_organization_name` (v1 §4, NEU-2132) does not call the name an organization. 37,072 keys and $547.3M are `IND` in 2024 (Q9f). `ENTITY_TP` is filled on 99.98% of dollars from 2020 and blank on 9.6–29.5% in 2006–2018 (Q2d). **Asserted, not measured:** that the classifier, measured on `indiv`'s names, reads payee names as well; NEU-2180's backfill measures it on a 2006–2018 cycle before publishing one.
- **A key with no page.** A payee key has no `payee` row, no `payee_id` and no search entity when more than half of its payee dollars, over every cycle in gold, are on person rows, or when it is listed in `fec/payee_no_page.csv`. Its rows are counted and listed on the committee that paid them like any other. The list is vendored and hand-kept, one `payee_key` per row with a `reason`, seeded from Q9e's sixteen candidates (`UNITEMIZED …`, `PAYROLL`, `PETTY CASH`, `CASH`, `ATM`, `CASH WITHDRAWAL` and their variants: about $270,000 in 2024), each read before it is listed: `VARIOUS PRESSURES` may be a firm. NEU-2155 creates it; NEU-2160's review adds to it.
- **An in-kind outlay** (`CONTEXT.md`; `is_in_kind`): a row with `BACK_REF_TRAN_ID` filled and no parent in the file, or a row whose purpose, upper-cased, names a gift received: it matches `IN[- ]?KIND` but not `IN[- ]?KIND CONTRIBUTIONS? MADE` or `\bFOR\b.*\bIN[- ]?KIND CONTRIBUTIONS\b` (an in-kind contribution the committee made, or pays ahead for), or it names crypto received (`\b(BITCOINS?|ETHER(EUM)?|USDC|RIPPLE|CRYPTO\w*)\b.*\bRECEIVED\b`, `RECEIVED,? (NOT )?LIQUIDATED`, `NOT LIQUIDATED`; NEU-2464). It keeps its `counted` and its category, and is in no payee figure: its payee is the gift's giver. 5,552 of 2024's 7,284 parentless sub-items ($18,833,378) name a receipt on their own filing, mostly `indiv` 15 and 10 and `oth` 15Z and 18G (Q7c); the other 1,732 ($1,327,593) are flagged on the same structure. A row whose `BACK_REF_TRAN_ID` is its own `TRAN_ID` names nothing, so it is no in-kind outlay, as the measurement counted those rows (NEU-2152). On ordinary rows, 'IN-KIND CONTRIBUTION' is 458 rows and $53.3M, and two single rows hold $23.0M in bitcoin and $15.5M in USDC (the labelled set). On 2024's first published build with spending (`20261122T205402Z`), the structural rule flags 6,973 counted rows ($19,625,238) and the pattern alone 14,454 ($139,958,524). Of the pattern's 20 largest rows, 16 are gifts and 3 are payments the committee made ("IN-KIND CONTRIBUTION MADE", an advance "FOR FUTURE INDEPENDENT EXPENDITURES & IN-KIND CONTRIBUTIONS": $1,339,000); one is unclear. A purpose avoiding the words is rare: at most 1,000 payee rows and $27,585,850 (0.29% of payee dollars) read as a gift received. But the 20 largest of them are all crypto received ('24,999,995 USDC RECEIVED, NOT LIQUIDATED' first), which the pattern misses. NEU-2464 widened it both ways, to the rule above (`docs/runbooks/spending-run.md`, Log 2026-11-22). The payment exclusion asks for `IN-KIND CONTRIBUTIONS`, plural, after `FOR`, so a gift's purpose naming what it was for stays a gift (`MEALS FOR VOLUNTEERS - IN-KIND`, `MEALS FOR VOLUNTEERS - IN-KIND CONTRIBUTION`), at the cost of a singular payment wording (`PAYMENT FOR IN-KIND CONTRIBUTION TO …`) still read as a gift; none is among the review's rows. `IN-KIND: GOTV ADVERTISING`, the unclear row, stays a gift.
- **A card issuer is a payee like any other.** `AMERICAN EXPRESS` is 2024's third-largest key, $195.2M from 632 committees (Q9b). Its total is bills, not purchases, and the methodology page says so.
- **A conduit as payee.** ActBlue is paid $136.0M and WinRed $115.8M, nearly all fees per contribution processed, `transfers_fees` (Q10a, Q10b). They are payees by name, as any committee that appears as one is (four of the top 100 keys): no link to a committee page.
- **`payee_id`**: the first 16 hexadecimal characters, lower case, of the SHA-256 of `payee_key` (UTF-8). It is a page's address and nothing else. It changes when the key does (ADR-0012).

### 5.5 Gold

Adds to v1 §7.1. Every amount is net: counted rows' amounts added as filed.

| Table | Added or new | Built by |
|---|---|---|
| `committee_cycle` | `total_operating_expenditures`: the committee's counted rows, in-kind outlays included | NEU-2154 |
| `committee_spending_category` | `(committee_id, cycle, category, amount)`, key the first three: the committee's counted rows by `spending_category`. A category with no counted row has no row; one netting to $0 or less is kept, so the rows add up to `total_operating_expenditures` | NEU-2154 |
| `committee_top_payee` | `(committee_id, cycle, rank ≤ 100, payee_key, payee_id, name, amount)`: payee rows grouped by key, ranked by amount then key; a key netting to $0 or less is left out. `name` is the key's reported spelling with the most payee dollars in the cycle, chosen as `committee_top_organization.name` is. `payee_id` is NULL for a key with no page (§5.4) | NEU-2154 |
| `candidate_cycle` | `total_operating_expenditures`: counted rows by silver's `candidate_id` | NEU-2154 |
| `race_candidate` | `total_operating_expenditures`: the candidate's `candidate_cycle` value | NEU-2154 |
| `race` | `total_operating_expenditures`: the sum over its candidates | NEU-2154 |
| `payee` | `(payee_id, payee_key, display_name, city, state, total_all_cycles, first_cycle, last_cycle)`, key `payee_id`, `payee_key` unique: one row per key with a page and at least one payee row. Each display column is chosen on its own by most payee dollars over every cycle, as `donor`'s are (v1 §6.7) | NEU-2155 |
| `payee_cycle` | `(payee_id, cycle, total, committee_count)`, key the first two | NEU-2155 |
| `payee_top_payer` | `(payee_id, cycle, rank ≤ 100, committee_id, candidate_id, amount)`: the committees that paid the payee most in the cycle, ranked by amount then `committee_id`; one netting to $0 or less is left out. `candidate_id` is the rows' silver `candidate_id`, the one with more of the amount where a handoff gives two, NULL when none | NEU-2155 |
| `search_entity` | `kind = 'payee'`: `id` is `payee_id`, `name` is `display_name`, `aliases` the key's other reported spellings, most payee dollars first, `weight` is `total_all_cycles` | NEU-2155 |

- **NULL, never 0, where there is no counted row.** `total_operating_expenditures` is NULL for a committee or candidate with no counted row in the cycle, and for a race none of whose candidates has one. So a cycle before 2004, and one whose live build lacks the table (§2, older builds), reads as "not available", not as nothing spent (NEU-2158 shows it so). A committee whose counted rows net to $0 has 0.
- **The handoff.** `candidate_cycle` follows silver's dated credit: of `C00703975`'s 2024 spending, what is dated before 2024-07-21 is Biden's and the rest Harris's. `reported_operating_expenditures` is whole Harris's (§4.3), so the two are not comparable for either candidate, and no ratio of them is stored. `04_contribution.sql`'s rule, as written, credits an undated row to the candidate the committee was handed to, Harris; NEU-2152's fixture holds silver to it. `oppexp` has no undated row in 2024 (Q1a).
- **A campaign turned PAC** counts whole, as its itemized receipts do (§4.3).
- Spending is in no receipt total, no `cycle.total_amount`, no donor figure and no top-donor, top-organization or top-committee list.
- The three split firms and a firm paid under a person's name are known gaps, not bugs of the gold tickets.
- **Checks** (gold): a committee's `committee_spending_category` rows add up to its `total_operating_expenditures`; every `committee_top_payee` and `payee_top_payer` amount equals its silver sum; ranks are contiguous (`gold_rank_contiguous.sql`); `payee_id` is unique and `payee_key` is unique in `payee`; no `payee` row's key is in `fec/payee_no_page.csv`.

### 5.6 Reconciliation

Adds a second `measure` to §4.5's table: `operating_expenditures`. `fundlens` is `committee_cycle.total_operating_expenditures`, `reported` is `reported_operating_expenditures`, `ratio` is `fundlens ÷ reported`. A committee is listed by §4.5's rule: `reported` not NULL and `fundlens − reported > 0.01 × reported`; a reported 0 beside counted spending is listed with `ratio` NULL; no dollar floor; over only. Conduits are not left out: the exclusion is the receipt measure's. 2008 on, since no earlier file has the measure (§4.7). Never failing the build. Built by NEU-2154.

On the measurement's figures, 2024 would list 63 committees over by $1.09M, and 12 with a reported $0 beside counted money: Q11c's 16 less the 4 with no reported figure at all, which are not listed (Q11a, Q11c, Q11e). No shortfall is listed: itemized spending sits below the reported figure by design (§5.2).

### 5.7 What each cycle range has

| | 2020– | 2006–2018 | 2004 | 1980–2002 |
|---|---|---|---|---|
| `operating_expenditure` | yes | yes | yes | an empty partition (§2) |
| Counting rules (§5.2) | as written | as written | as written | — |
| A person by `ENTITY_TP` | filled on 99.98% of dollars | blank on 9.6–29.5% of dollars: the name classifier decides | blank on 2.6% | — |
| `reconciliation` measure | yes | from 2008 | no | — |

Every cycle has the same three lines, the same parent and sub-item links (92–99% of rows with `BACK_REF_TRAN_ID` have their parent in the file) and no paper rows (Q2, Q4c). Memo dollars are 21.22% of 2004's file against 5–8% later; its parents are fully itemized for 79.71% of their dollars, so its memo rows mostly restate their parents (Q2b, Q2c). Senate campaigns filed on paper until 2018 and their operating expenditures are not in the file at all (Q4): a gap in FEC's bulk data, §9's to recover.

### 5.8 Dataset and older builds

`operating_expenditure` joins the public dataset (§8): NEU-2152 adds it to `DATASET_TABLES`, `columns.yaml`, the schema, the changelog, the README and `paths.BACKFILL_PENDING` in the PR that builds it. Its README entry says: sum only rows where `counted` is true; a sub-item is shown under its parent and never added to it; `payee_key` is a normalized name, not an id (ADR-0012); and spending is never to be added to `contribution` amounts. `spending_category` and `category_source` are NULL in a build made before NEU-2153.

## 6. Outside spending (M3)

Every kind of spending on a race by someone other than the campaign: independent expenditures by committees and non-committee spenders, with the 24/48-hour file's late and missing reports (2010–), electioneering communications (2010–), corporations' and unions' communication costs (2010–) and party coordinated expenditures, shown by kind on race and candidate pages. Builds on v1 §4's `independent_expenditure` (NEU-2057) and its pages (NEU-2058).

**Shared contracts:**

- `outside_spending_kind` ∈ {`independent_expenditure`, `electioneering_communication`, `communication_cost`, `party_coordinated`}, the names gold and the API use. Support or oppose where the source gives it: an electioneering communication has none, and a party coordinated expenditure is always in support. Silver's `independent_expenditure.kind` keeps v1's values (`ie`, `communication_cost`, `coordinated`).
- `pas2` is the source for independent expenditures, by committees and by non-committee spenders alike, and for communication costs and party coordinated expenditures. The 24/48-hour file adds two things only, never by matching rows: the rows of a spender `pas2` holds no independent expenditure for, behind the hoax screen; and the rows of a spender with a track record (§6.3) dated after its last periodic report, until a periodic report covers them. A row on a filing an amendment replaced is never read.
- An electioneering communication naming several candidates is split equally among them (FEC's `CALCULATED_CANDIDATE_SHARE`, as filed). Every row counts but a disbursement's copies; the file cannot show an amendment, so none is applied.
- A spender is a row of `committee`, whatever it is. Spending by anyone `cm` lacks is counted nowhere.
- Outside spending is never a contribution and never in a candidate's receipts.

The rules below were written by NEU-2163 (`docs/specs/NEU-2163-outside-spending-spec-section.md`, which holds each decision's rejected alternatives). "Q" and "Decision" numbers are NEU-2162's measurement's (`docs/measurements/outside-spending-2024.md`). A rule that rests on no measurement says "asserted, not measured" and names the ticket that checks it.

### 6.1 The four kinds and their sources

| Kind (gold, API) | Silver | Source | Side | 2024 |
|---|---|---|---|---|
| `independent_expenditure` | `independent_expenditure`, `kind = 'ie'` | `pas2` 24A and 24E; the 24/48-hour file by §6.3 | `S` or `O` | 73,841 rows, $4,422,382,849 from `pas2` (Q4); $1,001,297 added (Q6) |
| `communication_cost` | `independent_expenditure`, `kind = 'communication_cost'` | `pas2` 24F and 24N; `CommunicationCosts` for two columns | `S` or `O` | 799 rows, $7,157,987 (Q8) |
| `party_coordinated` | `independent_expenditure`, `kind = 'coordinated'` | `pas2` 24C | always `S` | 812 rows, $89,161,724 (Q10) |
| `electioneering_communication` | `electioneering_communication` | `ElectioneeringComm` | none | 67 rows, $9,442,374 (Q9) |

- **A spender** (`CONTEXT.md`) is whoever made the spending, held in `committee_id` in both tables and always a committee of the cycle in silver `committee`. A **non-committee spender** is one whose `committee.type` is `I` (a Form 5 filer), `C` (a Form 7 filer) or `E` (a Form 9 filer). It is derived from `committee`, never stored on a row.
- **Non-committee spenders are in `pas2`.** 153 Form 5 filers hold $84,903,413 of 2024's counted independent expenditures, and `pas2` matches a spender's reported figure within 1% for 142 of 199 (Q2d, Q2f; Decision 1). Every electioneering spender of 2024 is type `E` and every communication-cost spender type `C` (Q9a, Q8).
- **A spender `cm` lacks is counted nowhere**, in either table. In 2024's 24/48-hour file that is 8 spenders: seven hoax filers ($33,921,014,570) and Casey Family Farms' one Form 5 line ($64,107) (Q2b).
- **`pas2` holds an independent expenditure once**, from the periodic report: no counted row is on a 24- or 48-hour report, and none is on a filing the 24/48-hour file holds (Q4). So v1's totals count nothing twice.
- **No kind overlaps another.** The one overlap in 2024 is $1,451: two electioneering rows a spender's affiliate also filed as independent expenditures (Q11; Decision 8). No rule is applied.
- **The candidate a row names**, in every kind, is v1 §4's: the id the row gives, or the id it is an alias of, when it is a candidate of the cycle; a handoff's first candidate, on a row dated on or after the handoff or undated, is its second. `fec/ie_candidate_corrections.csv` is keyed by `SUB_ID`, so it applies to `pas2` rows alone. `race_id` is that candidate's race. A row naming no candidate of the cycle is kept with both NULL, and counts in its spender's total alone.

### 6.2 Silver `independent_expenditure`

`sql/silver/10_independent_expenditure.sql`, v1's model (NEU-2057), extended by NEU-2165 and NEU-2167. Key `(cycle, source, source_record_id)`, unchanged. v1's twelve columns keep their order and meaning; six are appended. `source_record_id` is text for every row, a `pas2` row's its `SUB_ID`'s digits, since a 24/48-hour row has no `SUB_ID` (NEU-2165, decided 2026-11-24): a retyping, the dataset's one breaking change of this section (§6.7). Rejected: a synthetic negative integer for a 24/48-hour row, which keeps the type and loses the key's meaning.

| Column | `pas2` rows | 24/48-hour rows (§6.3) | Added by |
|---|---|---|---|
| `cycle`, `source`, `jurisdiction` | as v1 | the same | — |
| `source_record_id` | `SUB_ID` | `<file_num>:<tran_id>` | NEU-2165 |
| `committee_id` | `CMTE_ID` | `spe_id` | NEU-2165 |
| `candidate_id`, `race_id` | §6.1's rule on `CAND_ID`, corrections applied | §6.1's rule on `cand_id` | NEU-2165 |
| `support_oppose` | by type, as v1 | `sup_opp` when it is `S` or `O`, else NULL | NEU-2165 |
| `amount` | `TRANSACTION_AMT`, whole dollars | `exp_amo`, with its cents | NEU-2165 |
| `date` | `TRANSACTION_DT` | `exp_date`, or `dissem_dt` where it is blank | NEU-2165 |
| `transaction_type` | as filed | NULL: the file has none | NEU-2165 |
| `kind` | by type, as v1 | `ie` | NEU-2165 |
| `source_file` | `pas2` | `ie_24_48` | NEU-2165 |
| `payee_name` | `NAME` | `pay` | NEU-2165 |
| `purpose` | NULL: `pas2` has none | `pur` | NEU-2165 |
| `dissemination_date` | NULL | `dissem_dt` | NEU-2165 |
| `communication_type`, `communication_class` | `COMMUNICATION_TP` and `COMMUNICATION_CLASS` of the `CommunicationCosts` row with the same `SUB_ID`, for a `communication_cost` row; else NULL | NULL | NEU-2167 |

- **`pas2` rows are v1's, unchanged**: the same rows, amounts, candidates and kinds. Memo lines stay dropped (282 coordinated lines, $1,414,204, in 2024, Q10b; no 24F or 24N line is a memo line, Q8).
- **Amounts.** `pas2` writes whole dollars (Q4h); the 24/48-hour file carries cents. Each is kept as its file gives it, a negative one included.
- **Dates.** 25,780 of 2024's 24/48-hour rows have no `exp_date` and 14,141 no `dissem_dt`; none lacks both (Q1). A spender's impossible year is kept as filed: dissemination dates run from 2004 to 2042.
- **A row with no side.** One added row of 2024 ($85) has a blank `sup_opp` (Q6d). It is in its spender's total and in no candidate's or race's figure, since those are by side.
- **Communication costs.** Every row of the CSV is a `pas2` 24F or 24N row under the same `SUB_ID`, filer, filing, `TRAN_ID` and candidate, in every cycle 2010–2026 but one 2022 row, and the amounts are equal once the CSV's cents are dropped (Q8c, Q8l, Q12g; Decision 5). `pas2` holds 20 rows the CSV lacks ($59,480, none naming a candidate): they count, with both new columns NULL. A CSV row with no `pas2` row adds nothing. `COMMUNICATION_TP` is `DM` (direct mail) on $6.19M of 2024 and `COMMUNICATION_CLASS` `M` on $7.05M; both are kept as filed. The CSV's `PURPOSE` is never filled (Q1), so `purpose` stays NULL. Form 7's reported total is `committee_summary`'s `TTL_COMMUNICATION_COST` (65 of FEC's 68 type-`C` rows of 2024 above $0; `docs/specs/NEU-2164-outside-spending-csvs-catalogue-fixture.md` §5), which `reported_total` does not hold (§4.1), so no spender's sum is checked against it (NEU-2167). Holding it in `reported_total` is an additive change. Measured by NEU-2167 on a hand transform of 2024 on the VM (build `20261124T201924Z`, FEC's files of 2026-11-24): **799 rows, $7,157,987.00**, 779 of them with a type and class from the CSV, unchanged from NEU-2166's build `20261124T190842Z` of the same files.
- **Party coordinated expenditures.** `pas2`'s 24C rows as v1 holds them, credited to the candidate named. 43 of 2024's 47 spenders are party committees (`cm` type `Y`), and each party committee matches its `reported_total.party_coordinated` within 1% but four that report $20,650 and file $3,000 (Q10). Three spenders are no party: a House campaign ($85,250), a union PAC ($3,000) and a Democratic club ($1,287). They count as filed (Decision 7). $89,034,392 names a candidate and $88,084,906 reaches a race (Q10h). Measured by NEU-2167 on a hand transform of 2024 on the VM (build `20261124T201924Z`, FEC's files of 2026-11-24): **812 rows, $89,161,724.00**, unchanged from NEU-2166's build `20261124T190842Z` of the same files.

**Checks.** v1's five stand (`silver_independent_expenditure_key`, `_candidate`, `_correction`, `_handoff`, `_not_money`), the side-and-type check applying to `pas2` rows alone. NEU-2165 adds `silver_independent_expenditure_no_double.sql`, which fails the build on a 24/48-hour row that:

- is on a filing another row of the file names in `prev_file_num`;
- is at a spender with a counted `pas2` independent expenditure in the cycle, unless it is dated after the spender's `period_end`;
- is at a spender that has neither a counted `pas2` independent expenditure in the cycle nor a reported figure above $0.

NEU-2167 adds `silver_independent_expenditure_communication.sql`: `communication_type` or `communication_class` is set only on a `communication_cost` row.

**Every transform logs** the communication costs' rows and dollars and how many the CSV gives a type, and the party coordinated expenditures' rows and dollars (NEU-2167): the figures §6.1's 2024 numbers are checked against.

**Memory.** Measured by NEU-2165 on a hand transform of 2026 on the VM (build `20261124T180255Z`, 2026-11-24): DuckDB held 13.39 GiB after `09_reported_total.sql` and 13.40 GiB after `10_independent_expenditure.sql`, so the model and its added rows cost about 0.01 GiB, and peak resident memory stayed at 16.84 GiB across it. The transform's peak is still `contribution`'s write (26.50 GiB resident in that run), which this model does not move, so `docs/capacity.md` has no entry for it. NEU-2167's join of `CommunicationCosts` costs no more: on 2024 (build `20261124T201924Z`) DuckDB held 19.43 GiB after `09_reported_total.sql` and 19.44 GiB after `10_independent_expenditure.sql`, peak resident 25.75 GiB across it.

### 6.3 What the 24/48-hour file adds

The **24/48-hour file** (`CONTEXT.md`; `ie_24_48` in the file catalogue, 2010–) holds spenders' 24- and 48-hour reports of independent expenditures: estimates, filed within a day or two, which a periodic report later restates in `pas2` under the same `TRAN_ID` mostly, and under another id, amount or candidate id often enough (Q5). It also holds **hoax filings** (`CONTEXT.md`): sixteen rows of $100M or more hold $44.9B of 2024's $49.7B (Q1j). So the file is never a source of its own. Silver reads it in this order:

1. **Amended filings are dropped: the filing chain** (Decision 2). A row whose `file_num` is named by another row's `prev_file_num` is not read. A chain of amendments needs no walking: each filing but the last is named by its successor. 2024: 61,426 rows kept, 12,023 dropped ($1,340,305,331) (Q3).
   - `prev_file_num` names a filing of the same spender in the file for 1,169 of 1,186 amendments; 17 ($2,539,495) name one the file lacks, and two `A1` filings name none. All are kept. One original is named by two amendments, both kept ($26,315 counted twice) (Q3).
   - What the chain drops and no amendment restates under the same `tran_id` is 1,140 rows, $29,711,780: 824 of them are in `pas2`, 706 under another `tran_id` (Q3n). The amendment renumbered them.
   - Rejected: the row on the highest `file_num` per spender and `tran_id`. NEU-2162's spec fell back on it when amendments carrying under half of their original's transaction ids crossed 1% of amended dollars (1.63%, Q3h). `tran_id` repeats across a spender's filings, so it drops $439,518,994 of distinct expenditures, and it keeps less than the chain in every cycle 2010–2026 (Q3j, Q12d).
2. **A row whose spender is no committee of the cycle in silver `committee` is dropped** (§6.1).
3. **Timeliness** (Decision 4). A row dated after its spender's `reported_total.period_end` is added when the spender has a **track record**: a counted `pas2` independent expenditure in the cycle, or `reported_total.independent_expenditures` above $0.
   - The row's date is §6.2's `date`. A spender with no `reported_total` row, or a NULL `period_end`, has no row added by this rule.
   - It lasts until a periodic report covers the rows: the next build after one arrives has a later `period_end`, and the spending is then `pas2`'s. A build reads `committee_summary` and `pas2` of the same extract.
   - 2026, read live on 2026-11-24: rows after `period_end` hold $1,287,474,092 from 512 spenders, nearly all from the last three weeks of October, and `pas2` already holds 0.46% of them, under NEU-2162's 1% bar; 69% and 87% of the rows dated on or before it are in `pas2` (Q7c, Q7e). Before the track record, the rule adds $1,281,571,904 on 2026 and $28,732 on 2024.
   - **What the track record leaves out**, measured by NEU-2165 on FEC's files of 2026-11-24: rows after their spender's `period_end`, the chain applied and the spender in `cm`, came to $1,287,175,625.72. Timeliness added $1,251,481,621.45 of it (14,831 rows, 412 spenders) and left out **$35,694,004.27, 2.77%**, at 95 spenders with neither a counted `pas2` independent expenditure nor a reported figure above $0. 62 of them are super PACs (`cm` type O) and 20 type V. Most have filed no periodic report with independent expenditures yet this cycle. The largest are The Edge Action Fund ($7,018,000), Buckeye Freedom PAC ($3,844,014), Alaska Values PAC ($3,754,011) and Common Sense for America PAC ($3,644,251). NEU-2165's ticket lists all 95. That is the screen's cost on a current cycle, accepted as the screen's cost below is; their spending is `pas2`'s once they file a periodic report. On 2024 the track record leaves out one spender: Conservative Fighter PAC, 2 rows, $25,278.89.
   - No dollar cap: a spender's last three weeks can dwarf its year to date. So a hoax filer that also reports a small real figure has a track record, and its rows after its period end are added unscreened: the transform's log line, which names the largest added row and its spender, is what catches one. Accepted (NEU-2165).
4. **By spender, behind the hoax screen** (Decision 3). A spender with no counted `pas2` independent expenditure in the cycle contributes its remaining rows, those dated on or before its `period_end` or undated, when both hold:
   - `reported_total.independent_expenditures` is above $0;
   - those rows add up to no more than ten times that figure.

   A spender whose `reported_total` row has a figure but a NULL `period_end` has no row added by timeliness, so all its rows are its remaining rows (NEU-2165).

   2024: 14 spenders, 100 rows, **$1,001,297**, against $996,357 they report; 13 are Form 5 filers (Earthjustice Action $293,577, FLIC Votes $207,175, Red Wine and Blue $134,695). $251,224 reaches a race and $750,073 names no candidate (Q6d–f).
   - Unscreened it adds $43,906,446,618, of which $43,905,445,320 is from 53 spenders reporting no independent expenditure (Q6c). No kept spender's rows exceed 4.9 times its reported figure, so the tenfold test drops nobody in 2024: it is there for a hoax filer who also reports a small real figure.
   - **What the screen costs.** A real spender that reports no independent expenditure is lost: Shield PAC ($1,225,000, dated 2023), Team Kennedy ($305,101), 19 committees with $3,185,809 in all, and Form 5 filers with no reported total (Q6a–b). Accepted.
   - The measurement compared all of a spender's rows with its reported figure; this rule compares those to `period_end`, the period the figure covers. On 2024 the two differ by at most timeliness's $28,732.
   - Web-form ids (`tran_id` beginning `WFT`) decide nothing: 85 committees and two Form 5 filers filed real lines on FEC's web form in 2024 (Q2c).
5. **Every other row is not read.** That includes every row, to its `period_end`, of a spender `pas2` holds an independent expenditure for.
   - Those rows are the same spending. After every rung of the measurement's ladder, $71,450,772 of them stay unmatched, 1.62% of counted dollars, and `pas2` keeps $212,480,816 of its own unmatched; spender by spender the two balance, the file higher by $40,549,211 in all, 0.92% (Q5p, Q5r). Added by row, 2024 would gain $68,376,504 with web-form ids aside, most of it counted already.
   - **What it costs.** Where the file holds more than `pas2` for such a spender, the difference is not added: the NRCC's $14.1M of late lines in 2024 (Q5r).
   - The ladder, its fourth rung included, is the measurement's evidence that the rows are the same. No pipeline rule matches a row to a row.

**2024 on this contract.** Rows with `source_file = 'ie_24_48'` should come to the 14 spenders' $1,001,297, plus whatever timeliness adds at other spenders, at most $28,732. NEU-2165's definition of done is within 1% of $1,001,297 for the by-spender rows, with each timeliness row listed. Measured by NEU-2165 on FEC's files of 2026-11-24, the merged models over `cm`, `pas2`, `committee_summary`, `webk` and `ie_24_48`:

- **By spender:** 65 rows, $997,843.85, 13 spenders, 0.34% under $1,001,297.
- **Timeliness:** 35 rows, $3,453.50, all FORFACT, LLC (`C90018771`), a Form 5 filer whose period ends 2024-09-30. Among them is the $85.29 row with no side (§6.2).
- **Together:** $1,001,297.35, 100 rows, 14 spenders: Q6's figure exactly. The measurement counted FORFACT's rows by spender. They fall after its period end, so timeliness adds them instead, as the rule above anticipates.
- **Largest added row:** $90,000.

**Every transform logs** the rows and dollars added by each of the two rules and the largest single added row with its spender, so a hoax filing that passes is seen in the run's log.

**Model order.** The rules read `reported_total`, which exists from 2008, so `09_reported_total.sql` runs before `10_independent_expenditure.sql` (NEU-2165 swapped the two; `reported_total` reads neither `independent_expenditure` nor any model after 08). The model leaves the temporary table `ie_24_48_added`, each added row with its rule, which the transform's log line reads.

### 6.4 Silver `electioneering_communication`

`sql/silver/13_electioneering_communication.sql` (NEU-2166), from `ElectioneeringComm` (2010–). Key `(cycle, source, source_record_id)`. `source` is `fec` and `jurisdiction` `US`.

Columns, in order:

| Column | From | Notes |
|---|---|---|
| `cycle`, `source`, `source_record_id`, `jurisdiction` | `SB_IMAGE_NUM` | `<SB_IMAGE_NUM>:<n>`, `n` the row's place among its image number's kept rows, ordered by every column as filed |
| `committee_id` | `COMMITTEE_ID` | The spender |
| `candidate_id`, `race_id` | `CANDIDATE_ID` | Nullable. §6.1's rule, the handoff by `date` |
| `amount` | `CALCULATED_CANDIDATE_SHARE` | `DECIMAL(14,2)`, as filed: the row's counted money |
| `disbursement_amount` | `REPORTED_DISBURSEMENT_AMOUNT` | The whole disbursement, repeated on each of its rows. Never summed |
| `candidate_count` | `NUMBER_OF_CANDIDATES` | |
| `date` | `DISBURSEMENT_DATE` | `DATE` from `DD-MON-YY` |
| `communication_date`, `public_distribution_date` | `COMMUNICATION_DATE`, `PUBLIC_DISBURSEMENT_DATE` | |
| `payee_name` | `PAYEE_NAME` | As reported |
| `description` | `DISBURSEMENT_DESCRIPTION` | As reported |
| `image_num` | `SB_IMAGE_NUM` | |

Not held: the candidate's and spender's names and the candidate's office, state and district (`candidate` and `committee` have them), and the payee's street, city and state. There is no `support_oppose`: the filing does not say. Adding a column later is an additive dataset change.

**Rows.** Every row whose spender is a committee of the cycle in silver `committee`, except a **disbursement's copies** (Decision 6). A disbursement is the rows equal on `COMMITTEE_ID`, `SB_IMAGE_NUM`, `PAYEE_NAME`, `DISBURSEMENT_DATE` and `REPORTED_DISBURSEMENT_AMOUNT`. Its rows beyond `NUMBER_OF_CANDIDATES`, in order of `CANDIDATE_ID` and then every column, are dropped. 2024: 69 rows become **67, $9,442,374**; the 2 dropped ($38,500) are second rows of two one-candidate disbursements, each naming the candidate its first row names (Q9f, Q9i).

- **The split is FEC's, as filed.** In 2024 every row's share times its candidate count is its disbursement's amount to the cent, and multi-candidate rows are 3.48% of dollars (Q9f, Q9g). 2010, 2012 and 2018 have 28, 16 and 10 rows whose split is off by over a cent (Q12f): the share stands as filed, and no check enforces the arithmetic.
- **A disbursement with fewer rows than candidates** keeps what it has: two of 2024's two-candidate disbursements have one row each, $11,932 short of their amounts (Q9f).
- **No candidate.** 24 rows of 2024 ($2,179,759) name none: trade groups' and nonprofits' ads about an issue. One names an id `cn` lacks (`P60012143`, $32,000) (Q9e). Each is kept with candidate and race NULL, in its spender's total alone. Blank-candidate rows begin in 2016 (Q12f). So 2024's rows reaching a candidate and a race come to $7,230,615: $9,442,374 less those two figures. Measured by NEU-2166: $7,230,615.02.
- **No amendment rule.** The file has no filing number and no amendment indicator. The Form 9s support one rule, that a row restated by an amendment of the same report is one payment and a repeat across two reports is two, and the file cannot apply it (Q9p). So a restatement is counted twice: $33,750 in 2024, 0.36% (Issue One Action's `1849492` amending `1816711`), and about $73,000 in 2010. Rejected: keeping the highest image number among rows equal on spender, payee, date, amount and candidate, which is exact in 2024 and drops $3,101,798 of 2010's $71,692,553, most of it separate real reports (Q9q).
- A row whose spender `cm` lacks is dropped (none in 2024: all 25 spenders are type `E`, Q9a).
- **Three answers NEU-2166 gave**, each for a case no cycle 2010–2026 is known to hold: no `NUMBER_OF_CANDIDATES` is blank and every filled date parses as `%d-%b-%y` (`docs/specs/NEU-2164-outside-spending-csvs-catalogue-fixture.md` §5). A disbursement is told by `DISBURSEMENT_DATE` parsed, the date silver holds, so the copies check groups exactly as the model does. A disbursement whose count is blank or below 1 has no copies known and keeps every row; a count of 0 was not measured, only each cycle's largest. "Ordered by every column as filed" puts a blank cell after a filled one, as DuckDB orders a NULL.

**Every transform logs** the table's rows and dollars, the dollars reaching a race and the disbursements' copies dropped (a row of a spender of the cycle the table does not hold), the figures this section's 2024 numbers are checked against.

**Checks** (NEU-2166): `silver_electioneering_communication_key.sql` (key unique); `..._committee.sql` (spender in `committee`); `..._candidate.sql` (a candidate is the cycle's, is no alias and is no handoff's first candidate on or after the handoff; a race is its candidate's); `..._copies.sql` (no disbursement has more rows than its `candidate_count`).

NEU-2166's definition of done is within 1% of 67 rows and $9,442,374. Measured by NEU-2166 on a hand transform of 2024 on the VM (build `20261124T190842Z`, FEC's files of 2026-11-24): **67 rows, $9,442,373.94**, $7,230,615.02 of it reaching a race, and the 2 copies dropped. DuckDB held 20.12 GiB before the model and after it, so the model costs nothing measurable and `docs/capacity.md` has no entry for it.

### 6.5 Gold

Adds to v1 §7.1. Every amount is net: rows' amounts added as filed. Built by NEU-2168.

| Table | Added or new |
|---|---|
| `candidate_cycle` | `communication_cost_support`, `communication_cost_oppose`: `communication_cost` rows naming the candidate, by side. `party_coordinated`: `coordinated` rows naming the candidate. `electioneering`: `electioneering_communication.amount` naming the candidate. `ie_support` and `ie_oppose` keep v1's definition and now include the 24/48-hour rows |
| `race_candidate` | The same four, and v1's two: the candidate's `candidate_cycle` values |
| `race` | The same four, each the sum over its candidates, and `outside_spending_total`: `ie_support + ie_oppose + communication_cost_support + communication_cost_oppose + party_coordinated + electioneering`, a NULL `electioneering` as 0 |
| `committee_cycle` | `communication_cost_total`, `party_coordinated_total`, `electioneering_total`: the spender's rows of each kind, both sides, those naming no candidate of the cycle included, as `ie_total` is. `outside_spending_total`: the four added up |
| `race_top_spender` | `(race_id, rank ≤ 100, committee_id, name, candidate_id, kind, support_oppose, amount)`, key `(race_id, rank)`: one row per spender, candidate, kind and side with a row on the race, ranked by amount, then `committee_id`, `candidate_id`, `kind`, `support_oppose`. A line netting to $0 or less is left out. `kind` is one of the contract's four names. `support_oppose` is NULL for an electioneering communication. `name` is the spender's, as `race_top_committee.name` is |

- **0 and NULL.** The `pas2`-sourced fields are 0 where there is no row, never NULL, as `ie_support` and `ie_oppose` are. `electioneering` and `electioneering_total` are NULL where there is no row: a cycle before 2010 has no file, and a build may lack the table (§2, older builds), so "none" must not read as "$0". Both `outside_spending_total`s are never NULL.
- **No total on a candidate.** Money for a candidate and money against them point opposite ways, and an electioneering communication points neither. A race's total is how much was spent on the race by anyone but its candidates' committees.
- **A row with no side** (§6.2) is in `ie_total` and in no candidate, race or top-spender figure.
- **A non-committee spender** is told by `committee.type` (`I`, `C`, `E`). Every spender has a `committee` row and so a page; NEU-2169 returns the flag and NEU-2170 shows the badge.
- **`race_top_committee`'s definition stands.** Its `ie` rows remain a spender's independent expenditures on the race, for and against summed, and now include the 24/48-hour rows; a row with no side is left out (NEU-2165), so they still add up to the race's `ie_support` plus `ie_oppose`. NEU-2170 decides which list a page shows.
- **The handoff** follows silver's dated rule in every kind: spending naming Biden on or after 2024-07-21 is Harris's.
- Outside spending is in no receipt total, no `cycle.total_amount`, no donor figure, no `total_operating_expenditures` and no top-donor, top-organization or top-payee list.
- **Checks** (gold): a race's six columns add up to its `outside_spending_total`; each of a race's columns equals the sum over its `race_candidate` rows; a committee's four totals add up to its `outside_spending_total`; every `race_top_spender` amount equals its silver sum; ranks are contiguous (`gold_rank_contiguous.sql`); no receipt or spending total moves on the fixture.
- **The API and pages** (NEU-2169, NEU-2170) read these fields. The itemized independent-expenditure route (v1 §7.2) scans `kind = 'ie'`, so it lists the 24/48-hour rows; NEU-2165 made its cursor carry a text key, compared as text, and its `support_oppose` and `transaction_type` nullable, and the committee page's table shows a dash for a row with no side. NEU-2169 adds `source_file`, `payee_name` and `purpose` to its rows, and a page marks a 24/48-hour row as an estimate from a 24- or 48-hour report.

**The five races.** NEU-2171 compares gold with the measurement's Q13: Ohio, Pennsylvania, Montana, Michigan and Wisconsin, per candidate and kind. Q13's "added" column is the screened by-spender rule's, and its electioneering column counts every row of the file. The two copies this contract drops ($38,500) name House candidates, so no Senate figure differs for them. This contract can differ from Q13 only by timeliness, at most $28,732 across 2024, and NEU-2171 explains any other gap.

### 6.6 What each cycle range has

| | 2020– | 2010–2018 | 1980–2008 |
|---|---|---|---|
| Independent expenditures, communication costs, party coordinated expenditures from `pas2` | yes | yes | yes |
| 24/48-hour rows (§6.3) | yes | yes | none: no file |
| Hoax filings in the file | $1.74B (2020) to $38.5B (2026) at spenders `cm` lacks | under $133,000 a cycle | — |
| `communication_type`, `communication_class` | yes | yes | NULL: no CSV |
| `electioneering_communication` | yes | yes; blank candidates from 2016; splits off by a cent in 2010, 2012, 2018 | an empty partition (§2) |
| `reported_total` for the screen | yes | yes | — |

No cycle breaks a 2024 rule as written (Q12; Decision 9). The screen and the track record apply in every cycle, not from 2020 alone: one rule, and a hoax filing can be filed for any cycle. The chain drops more in 2022 ($13.3B, hoax filings amended by hoax filings) and 2020 ($1.21B) (Q12d). Every CSV header equals 2024's in every cycle, and no cell of any cycle fails a cast under the catalogue's types: Q12b's 12 and 1 in 2016 and 2018 are blank `exp_amo` cells, NULL as any blank is (`docs/specs/NEU-2164-outside-spending-csvs-catalogue-fixture.md` §5). 2026's coordinated expenditures are four times 2024's ($351,217,482) with the cycle not over (Q12h). (`file_num`, `tran_id`) is unique in every cycle's 24/48-hour file, 2010 to 2026, as read on 2026-11-24 (the same spec's §5); the key check still fails a build where it is not.

### 6.7 Dataset and older builds

- `electioneering_communication` joins the public dataset (§8): NEU-2166 adds it to `DATASET_TABLES`, `columns.yaml`, the schema, the changelog, the README and `paths.BACKFILL_PENDING` in the PR that builds it. Its README entry says: sum `amount`, never `disbursement_amount`; a row has no side; a restated report may be counted twice (§6.4); and outside spending is never to be added to `contribution` amounts.
- `independent_expenditure`'s six columns are additive changes, each with a `CHANGELOG.md` entry and a `columns.yaml` description by the ticket that adds it (NEU-2165, NEU-2167). `source_record_id`'s retyping from an integer to text (§6.2) is a breaking change, in NEU-2165's entry: a cycle built before it holds integers until NEU-2180's backfill, and the gold loader's `union_by_name` reads the two as text. Its table description stops saying every row is from `pas2`. Its README entry says: tell the kinds apart by `kind`; a row with `source_file = 'ie_24_48'` is a 24- or 48-hour report's estimate, and leaves the table when a periodic report restates it, so its `source_record_id` is not stable from one snapshot to the next.
- The table is in every build, so it is no backfill-pending table. A cycle built before a column existed has no such column and reads it as NULL, as `organization_receipt.is_returned_cost` was handled (changelog, 2026-11-20). Gold reads none of the six. NEU-2180's backfill rebuilds every cycle with them.

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
- The **silver ticket** that builds the table adds it to the dataset in the same PR: `DATASET_TABLES` in `publish/dataset.py`, its column descriptions in `docs/dataset/columns.yaml`, `schema/<table>.json` by `task dataset:schema`, a `docs/dataset/CHANGELOG.md` entry, the README where it lists tables, and `paths.BACKFILL_PENDING`. `tests/integration/test_dataset.py` already fails on a missing description or a stale schema. So a table is public from its first build. Rejected: the milestone's runbook ticket or one ticket at the project's end, both of which leave built tables unpublished for weeks.
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
