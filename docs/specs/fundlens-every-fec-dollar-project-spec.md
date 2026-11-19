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

Each measure is the file's figure as filed, `DECIMAL(14,2)`: a blank is NULL, a filed 0 is 0, and nothing is netted, corrected or derived from another measure except where the table says so. `INDV_CONTB = INDV_ITEM_CONTB + INDV_UNITEM_CONTB` fails for 166 committees in 2024, filers' arithmetic mostly (Q4c), so all three are stored as filed and no check enforces the identity. Dates are `DATE`: `committee_summary` writes `YYYYMMDD`, the zips `MM/DD/YYYY`. `period_start` and `period_end` are the committee's **reporting period** (`CONTEXT.md`).

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
  - The numerator is individual plus organization money (Decision 4): within 1% of FEC's itemized figure at 5,114 committees against 4,440 for individual money alone, and at super PACs 802 against 386 (Q5g). Those counts were taken net of refunds; the numerator is gross because `INDV_ITEM_CONTB` is (NEU-2265: VIVEK 2024 reads −2.06% net, −0.17% gross). **Asserted, not measured:** the counts on the gross basis; NEU-2147's runbook records them.
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
- The measurement's list, on the net basis and before its bugs were fixed, was 725 committees and $1.94B (Q6); NEU-2192 to NEU-2199 and NEU-2276 took the diagnosed causes out, leaving 71 unexplained. **Asserted, not measured:** the table's row count on a current build; NEU-2147's runbook records it and dispositions its top ten.

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
