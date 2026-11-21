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
| `independent_expenditure` | Independent expenditures (24- and 48-Hour Reports) | csv | `<yyyy>/independent_expenditure_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `ElectioneeringComm` | Electioneering communications | csv | `<yyyy>/ElectioneeringComm_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `CommunicationCosts` | Communication costs | csv | `<yyyy>/CommunicationCosts_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `leadership` | Leadership PACs and sponsors | csv | `data.fec.gov/leadership<yyyy>.csv` | 2010 | M4 | NEU-2174 |
| `lobbyist` | Lobbyist/registrant committees | csv | `data.fec.gov/lobbyist.csv` | undated: one file, labelled 2007–2026 | M4 | NEU-2174 |
| `lobbyist_bundle` | Lobbyist bundled filings | csv | `data.fec.gov/lobbyist_bundle.csv` | undated: one file, labelled 2009–2026 | M4 | NEU-2174 |

- The page links every file above for each cycle from its first to 2026, with no gap.
- `weball` and `webk` have no header file on FEC's site: the page links one for `oppexp` and for each of v1's six, and `data_dictionaries/<file>_header_file.csv` was a 404 for both on 2026-11-05 (`docs/measurements/summary-files-2024.md`, its header-sources row). Their column lists are vendored from FEC's file descriptions (NEU-2142).
- Every `oppexp` line, in every cycle, ends with a `|` after its last column, so it splits into 26 fields, the last empty: the entry is catalogued with `trailing_delimiter`, and `register_bulk` reads such a line under its 25 columns unchanged. The zip's one member is `oppexp.txt` in every cycle, and its dates are `MM/DD/YYYY`. Every cycle 2004 to 2026 was read through `register_bulk` on 2026-11-21 with no cast failing (`docs/specs/NEU-2151-oppexp-catalogue-extract-fixture.md` §5).
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
- **Rows, 2008 on.** One row per `CMTE_ID` of `committee_summary` that is a committee of the cycle in silver `committee`. The file repeats a committee once per linked candidate (65 committees, 136 rows in 2024, Q1): the transform keeps one and fails if a committee's rows differ in anything but `CAND_ID` and `Link_Image`. Each measure is `committee_summary`'s, except that a Form 5 filer (type I) or Form 7 filer (type C) takes each measure its row leaves blank from `webk`, where `webk` holds the committee: a Form 5 filer's `committee_summary` row carries only `INDT_EXP`, and a Form 7 filer's only a communication-cost figure this table does not hold (204 and 68 committees in 2024, Q2f2; NEU-2141 Appendix A). No other committee's blank is filled (NEU-2143): a Form 3X committee's blank candidate-contribution and candidate-loan lines are lines its form lacks, which `webk` gives as 0, and filling them would make nearly every PAC's row `committee_summary+webk`. `source_file` is `committee_summary+webk` when any measure came from `webk`, else `committee_summary`. A committee only in `webk` gets no row: the 2,248 committees only in `webk24` carry no money but one bad Form 5 record (Q1). 2024: 13,995 committees, 13,994 of them silver committees (Q1i).
- **Rows, 1996–2006.** One row per `webk` committee in silver `committee`, `source_file` `webk`. House and Senate campaign committees have none: `webk04` holds 54 candidate committees (Q8).
- **Rows, 1980–1994.** None. The model still writes its partition, empty (§2, older builds).
- A row whose every measure is blank is kept: FEC lists the committee and reports nothing.
- **Not held:** FEC's `FED_CAND_CMTE_CONTB` (Form 3X line 23), which reconciles with neither the gross nor the net 24Ks (Decision 8), `OTHER_RECEIPTS`, and Form 7's `TTL_COMMUNICATION_COST`, which is M3's (§6). Adding a measure later is an additive dataset change.

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
| `date` | `TRANSACTION_DT` | `DATE` from `MM/DD/YYYY`. A filer's impossible year is kept as filed (years 1201 to 9201 appear in every cycle, Q2) |
| `purpose` | `PURPOSE` | As reported |
| `fec_category` | `CATEGORY` | FEC's code as a three-character string: one written without its leading zeros (`1`, `01`) is the code it pads to. Any other value is kept as filed |
| `spending_category`, `category_source` | — | §5.3. NULL until NEU-2153 |
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

**Memory.** The table holds about 0.87 GiB for 2024, which puts the transform's peak at about 27.35 GiB under the 29.80 GiB limit. NEU-2152 writes the table and drops it before `contribution`'s write, the transform's peak, if it can (Q1, Decision 7).

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
- The test set is `tests/fixtures/spending/purpose_labels_2024.csv`: 200 purposes holding 76.75% of counted dollars, 35 of them judgement calls with reasons. **Asserted, not measured:** that the purpose rule and the six codes leave under 10% of counted dollars `unclassified`; NEU-2153's definition of done measures it.
- NEU-2153 adds its method note for the methodology page here.

### 5.4 Payees

- **Payee key** (`CONTEXT.md`, ADR-0012). `payee_key = organization_key(payee_name)`, the function organizations use: `normalize_employer`, falling back on the cleaned name. Exact grouping, no linkage, across committees and cycles. 105,313 raw names become 98,975 keys in 2024; the top 100 keys hold 52.37% of counted dollars and the top 1,000 hold 80.26% (Q9a). Read by eye, the top 100 hold no wrong merge and three split firms (`AX MEDIA` and `AXMEDIA`; `TEAM DIRECT` and `TEAMDIRECT`; `MISSIONWIRED`, `ANNE LEWIS STRATEGIES` and `ANNE LEWIS STRATEGIES LLC DBA MISSIONWIRED`), each joined by an alias in `resolve/aliases.yaml`, filed as a Bug from NEU-2160's payee review (Q9b).
- **Payee rows.** The rows payee figures read: `counted`, `payee_key` not NULL, `is_in_kind` false. "Payee dollars" below are their net amount.
- **A person** (`payee_is_person`, per row): `entity_type` is `IND` or `CAN`; or it is blank, the row has a name, and `is_organization_name` (v1 §4, NEU-2132) does not call the name an organization. 37,072 keys and $547.3M are `IND` in 2024 (Q9f). `ENTITY_TP` is filled on 99.98% of dollars from 2020 and blank on 9.6–29.5% in 2006–2018 (Q2d). **Asserted, not measured:** that the classifier, measured on `indiv`'s names, reads payee names as well; NEU-2180's backfill measures it on a 2006–2018 cycle before publishing one.
- **A key with no page.** A payee key has no `payee` row, no `payee_id` and no search entity when more than half of its payee dollars, over every cycle in gold, are on person rows, or when it is listed in `fec/payee_no_page.csv`. Its rows are counted and listed on the committee that paid them like any other. The list is vendored and hand-kept, one `payee_key` per row with a `reason`, seeded from Q9e's sixteen candidates (`UNITEMIZED …`, `PAYROLL`, `PETTY CASH`, `CASH`, `ATM`, `CASH WITHDRAWAL` and their variants: about $270,000 in 2024), each read before it is listed: `VARIOUS PRESSURES` may be a firm. NEU-2155 creates it; NEU-2160's review adds to it.
- **An in-kind outlay** (`CONTEXT.md`; `is_in_kind`): a row with `BACK_REF_TRAN_ID` filled and no parent in the file, or a row whose purpose, upper-cased, matches `IN[- ]?KIND`. It keeps its `counted` and its category, and is in no payee figure: its payee is the gift's giver. 5,552 of 2024's 7,284 parentless sub-items ($18,833,378) name a receipt on their own filing, mostly `indiv` 15 and 10 and `oth` 15Z and 18G (Q7c); the other 1,732 ($1,327,593) are flagged on the same structure. On ordinary rows, 'IN-KIND CONTRIBUTION' is 458 rows and $53.3M, and two single rows hold $23.0M in bitcoin and $15.5M in USDC (the labelled set). **Asserted, not measured:** the pattern's precision, and that a purpose avoiding the words ('24,999,995 USDC RECEIVED, NOT LIQUIDATED') is rare; NEU-2160's payee review checks both.
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
- **The handoff.** `candidate_cycle` follows silver's dated credit: of `C00703975`'s 2024 spending, what is dated before 2024-07-21 is Biden's and the rest Harris's. `reported_operating_expenditures` is whole Harris's (§4.3), so the two are not comparable for either candidate, and no ratio of them is stored. **Asserted, not measured:** how `04_contribution.sql`'s rule credits an undated row; `oppexp` has none in 2024 (Q1a), and NEU-2152 follows the rule as written.
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
