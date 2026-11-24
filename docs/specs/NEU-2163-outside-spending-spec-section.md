# NEU-2163 — Spec §6 outside spending: sources and rules per kind, silver columns, gold fields; glossary

**Ticket:** [NEU-2163](https://linear.app/neuroticsasquatch/issue/NEU-2163) · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Milestone:** M3 All outside spending · **Parent story:** NEU-2161
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §6 (a stub this ticket fills), §2 (older builds), §3.1 (the three CSVs), §4.1 and §4.3 (`reported_total`, the credit rule), §8 (public dataset) · **v1 spec:** §4 (`independent_expenditure`, the alias, handoff and correction rules), §7.1 (`ie_support`, `ie_oppose`, `ie_total`, `race_top_committee`), §9 · **Glossary:** `CONTEXT.md` · **ADRs:** none new
**Blocked by:** NEU-2137 (Done), NEU-2162 (Done: `docs/measurements/outside-spending-2024.md`, "the measurement" below). **Blocks:** NEU-2165, NEU-2166, NEU-2167, and through them NEU-2168 to NEU-2171. **Related:** NEU-2164 (catalogue and extract), NEU-2057 and NEU-2058 (v1's model and pages).

Planned 2026-11-24. `/implementit NEU-2163` produces **one docs PR**: project spec §6 written out, the eight `CONTEXT.md` terms this planning session already wrote (uncommitted), one edit to the v1 spec (§9's table list), and the Linear text corrections of §5. Nothing under `sql/`, `src/`, `frontend/` or `tests/` changes. Every figure below is the measurement's, quoted with its question number, except where this spec says it derived one.

## 1. What and why

Eight tickets (NEU-2164 to NEU-2171) build outside spending from one contract that is not written down: project spec §6 holds only the milestone's four shared contracts. This ticket writes it.

The ticket text and the milestone's contracts predate the measurement, and differ from what this spec pins in these places:

1. The milestone has the 24/48-hour file add "spenders not in `cm`". That group is one real spender ($64,107) and seven hoax filers. Non-committee spenders are in `cm`, as Form 5 filers, and their spending is already in `pas2`.
2. Nobody knew the 24/48-hour file holds hoax filings: $43.9B in 2024. Every rule that reads the file is built around keeping them out.
3. The ticket gives `independent_expenditure` the columns `spender_id`, `spender_name` and `spender_is_committee`, and the electioneering table `sponsor_id` and `sponsor_name`. Every counted spender is a row of `committee`, so none is needed.
4. The ticket's `communication_cost` table falls away: every row of the CSV is a `pas2` row silver already holds.
5. The milestone and NEU-2166 deduplicate electioneering communications "after amendment". The file cannot tell an amendment's restatement from a second report.
6. NEU-2167 renames silver's `coordinated` to `party_coordinated`. The value is in the public dataset and stays.
7. The ticket's `race_top_spender` has no candidate, so its support/oppose says nothing in a race with two candidates.
8. NEU-2165's target is the measurement's "only in 24/48-hour" figure. The rule adopted adds by spender, and its figure is another.

### 1.1 Decisions pinned (grilled 2026-11-24)

The first five are the ones NEU-2162's comment on this ticket handed over.

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| 24/48-hour amendments | **The filing chain.** Every row on a filing that another row's `prev_file_num` names is dropped. | `tran_id` is not a key across a spender's filings: Senate Leadership Fund numbers a line `SE.1` on every new report (Q3l). Rejected: per transaction, the fallback NEU-2162's spec §1.1 pinned once partial amendments crossed its 1% bar (1.63%, Q3h), which drops $439,518,994 of distinct expenditures on filings nothing amends (Q3j); chain per transaction, which keeps a renumbered row beside its amendment's copy. |
| What the file adds | **By spender.** A spender with no counted `pas2` independent expenditure in the cycle contributes its rows; a spender with any contributes none, timeliness apart. Silver never matches a row to a row. | The unmatched rows at spenders `pas2` holds are 1.62% of counted dollars, over NEU-2162's 1% bar (Q5p), but they are the same spending under other ids, amounts and the other presidential candidate's id: per spender the file exceeds `pas2` by 0.92% (Q5r). Rejected: by row with the ladder ($68,376,504 added in 2024 with web-form ids aside, most of it a double count); nothing but timeliness (loses the Form 5 filers `pas2` is missing). |
| Rung 4 | **Accepted as the measurement's evidence, and no part of silver.** The ladder is how the measurement showed the rows are the same spending. No pipeline rule uses a rung. | The by-spender rule needs no match. |
| The hoax screen | **The measurement's.** A by-spender spender must report independent expenditures above $0 in `reported_total`, and its rows must total no more than ten times that figure. | Unscreened, the rule adds $43,906,446,618 in 2024, all but $4.8M of it hoax filings (Q6c). Every hoax filer reports none, and no kept spender's rows exceed 4.9 times its reported figure (Q6b). The tenfold leg drops nobody in 2024: it guards against a hoax filer who also reports a small real figure. Rejected: the reported figure alone (a spender reporting $500 could add a $9B line); web-form ids aside (rests on hoax filers always using the web form, and drops BIG SKY 55+'s real $503,222). **Cost, accepted:** real spenders that report no independent expenditure are lost: Shield PAC $1,225,000, Team Kennedy $305,101, 19 committees with $3,185,809 in all (Q6b). |
| Communication costs' amounts | **NEU-2162's "equal amounts" bar is read as equal once the CSV's cents are dropped, and silver's `amount` stays `pas2`'s.** | `pas2` writes whole dollars: every one of the 437 differing amounts is the CSV's truncated (Q8l–m). One amount source for every `pas2` row, and for cycles before 2010 that have no CSV. Rejected: the CSV's cents where it has the row (filed-exact from 2010, truncated before); not confirming the reading (the CSV becomes a second source for rows silver already holds). |
| Timeliness | **In, for a spender with a track record.** A spender's rows dated after its `reported_total.period_end` are added when it has a counted `pas2` independent expenditure in the cycle or reports independent expenditures above $0. No dollar cap. | The contract's condition is met: `pas2` already holds 0.46% of 2026's post-period rows, under the 1% bar (Q7e), and without the rule the current cycle misses the last three weeks before each election until December. The screen cannot guard these rows, because the reported figure does not cover them yet, so they are held to `pas2`'s own trust level instead. A spender's last three weeks can dwarf its year, so no multiple of its reported figure is safe. Rejected: any spender with a `period_end`, as measured (a committee that files one empty periodic report and then a web-form line puts its figure on a race page before an election); out. **Asserted, not measured:** what the track record leaves out of 2026's $1,281,571,904; NEU-2165 measures it. |
| Communication costs and party coordinated expenditures in silver | **They stay rows of `independent_expenditure`, `kind` values unchanged** (`ie`, `coordinated`, `communication_cost`). No `communication_cost` table. The CSV supplies `communication_type` and `communication_class` by `SUB_ID`. Gold and the API use the contract's four names. | They are `pas2` rows, and the table, the column and its values are in the public dataset. Rejected: renaming the values to the contract's (changes a published column's values, five SQL models and the API's itemized route, for a tidier word); the ticket's own table (removes published rows from a published table, and cycles before 2010 have the rows and no CSV). |
| Spender | **One word, one column.** A spender is whoever made outside spending of any kind. Both silver tables hold it in `committee_id`; a row whose spender `cm` lacks is dropped, as v1 drops it. A non-committee spender is one `cm` types `I`, `C` or `E`. | Form 5, Form 7 and Form 9 filers are all rows of silver and gold `committee`, and the screen needs a reported total, so no spender outside `cm` can be counted. Rejected: the measurement's three role words with the ticket's `spender_*` and `sponsor_*` columns (three words for one role in one gold list, and columns duplicating `committee`); non-committee meaning type `I` alone (an electioneering spender and a Form 7 union are no committees either). |
| Electioneering rows | **Every row counts but a disbursement's copies.** No amendment rule. | The file has no filing number. Its Form 9s show both an amendment's restatement (2024's two repeat groups, $33,750) and two real reports of one payee, date and amount (13 of 2010's 20 largest groups, Q9p). Rejected: the file key as well (exact in 2024, but drops $3,101,798 of 2010's $71,692,553, most of it real, Q9q); every row (counts two one-candidate disbursements twice, $38,500). **Known overcount, accepted:** a restatement stays, $33,750 in 2024 (0.36%) and about $73,000 in 2010. |
| Gold, per candidate and race | **Wide columns** beside v1's `ie_support` and `ie_oppose`: `communication_cost_support`, `communication_cost_oppose`, `party_coordinated`, `electioneering`. `outside_spending_total` on `race` and `committee_cycle` only. | Four kinds, fixed, read inline on every race load. A candidate gets no total: money for them and money against them point opposite ways. Rejected: a long table (v1's columns would duplicate two of its rows, and the API would pivot it on every load); a candidate total. |
| `race_top_spender` | **One row per spender, candidate, kind and side.** v1's `race_top_committee` is unchanged. | "Against, $80M" on a Senate race does not say whom. Rejected: the ticket's grain without the candidate; one row per spender (adds for to against, as `race_top_committee`'s `ie` rows already do). |
| Party coordinated expenditures | **The fourth kind of outside spending, and in `race.outside_spending_total`.** | Outside spending is defined by who pays: anyone but the candidates' own committees. The party pays for and reports the expenditure. Rejected: shown but outside the total (the total needs a footnote wherever a party spent); a term of its own beside a three-kind umbrella. |
| Glossary | **Eight terms**, written in this session: the ticket's four, plus **Spender**, **Non-committee spender**, **Hoax filing** and **24/48-hour file**; **Independent expenditure** reworded. | The catalogue names the 24/48-hour file `independent_expenditure`, the word for a silver table it only partly feeds, and tickets word a hoax filing three ways. |

**Pinned without a question each**, confirmed together at the end of the session. Say so in the PR.

| Decision | Pinned | Why |
|---|---|---|
| The tenfold test's rows | A spender's rows dated on or before its `period_end`, undated rows among them. Rows dated after it are the timeliness rule's. | Like for like: the reported figure covers the period to `period_end`. The measurement compared all of a spender's rows (Q6); in 2024 the two differ by at most the $28,732 timeliness adds (Q7e). |
| Keys | A 24/48-hour row's `source_record_id` is `<file_num>:<tran_id>`; an electioneering row's is `<SB_IMAGE_NUM>:<n>`. | Neither file has a `SUB_ID`. (`spe_id`, `file_num`, `tran_id`) is unique in 2024's 24/48-hour file (Q1); the electioneering file holds rows equal in every column (Q1), so its key needs an ordinal. |
| New columns on `independent_expenditure` | `source_file`, `payee_name`, `purpose`, `dissemination_date`, `communication_type`, `communication_class`. `payee_name` is filled from `pas2`'s `NAME` too. | The measurement read `pas2`'s `NAME` as the payee throughout (its setup). |
| An electioneering row's candidate | `independent_expenditure`'s rule: the alias, and the handoff by the disbursement's date. A blank id, or one that is no candidate of the cycle, leaves candidate and race NULL, and the row counts in its spender's total alone. | One rule for "the candidate a row names" across outside spending. |
| NULL and 0 in gold | The `pas2`-sourced fields are 0, never NULL, as `ie_support` and `ie_oppose` are. `electioneering` is NULL where there is no row. | `pas2` covers every cycle, so no row means none. No electioneering file exists before 2010, and an older build may lack the table (project spec §2), so no row must not read as "$0" (as §5.5's `total_operating_expenditures`). |
| ADR | None. | Every rule here is reversed by a rebuild, and §6 holds each one's reasons and rejected alternatives. Nothing is a public id or address, as ADR-0012's `payee_id` was. |
| Electioneering column names | The counted money is `amount` (FEC's `CALCULATED_CANDIDATE_SHARE`), beside `disbursement_amount` and `candidate_count`. The ticket had `candidate_share` and `reported_amount`. | Every silver table's counted money is `amount`, and the dataset README tells readers to sum it. |
| Reconciliation | No new `measure` in M3. | Not asked for by any M3 ticket. The measurement's comparisons stand as evidence (Q2f, Q10). |

## 2. The document: project spec §6

Replace §6's closing "**Filled by** NEU-2163 …" line with the subsections below. Keep the opening paragraph, with one change: "independent expenditures from spenders that are not committees (the 24/48-hour file, 2010–)" becomes "independent expenditures by committees and non-committee spenders, with the 24/48-hour file's late and missing reports (2010–)". Replace the four shared contracts with the amended five given first (the same text goes into the milestone, §5). Write each rule with its measurement citation, as given here ("Q" and "Decision" numbers are the measurement's). Where a rule rests on no measurement it says "asserted, not measured" and names the ticket that checks it.

**Shared contracts (amended):**

- `outside_spending_kind` ∈ {`independent_expenditure`, `electioneering_communication`, `communication_cost`, `party_coordinated`}, the names gold and the API use. Support or oppose where the source gives it: an electioneering communication has none, and a party coordinated expenditure is always in support. Silver's `independent_expenditure.kind` keeps v1's values (`ie`, `communication_cost`, `coordinated`).
- `pas2` is the source for independent expenditures, by committees and by non-committee spenders alike, and for communication costs and party coordinated expenditures. The 24/48-hour file adds two things only, never by matching rows: the rows of a spender `pas2` holds no independent expenditure for, behind the hoax screen; and the rows of a spender with a track record (§6.3) dated after its last periodic report, until a periodic report covers them. A row on a filing an amendment replaced is never read.
- An electioneering communication naming several candidates is split equally among them (FEC's `CALCULATED_CANDIDATE_SHARE`, as filed). Every row counts but a disbursement's copies; the file cannot show an amendment, so none is applied.
- A spender is a row of `committee`, whatever it is. Spending by anyone `cm` lacks is counted nowhere.
- Outside spending is never a contribution and never in a candidate's receipts.

The rules below were written by NEU-2163 (`docs/specs/NEU-2163-outside-spending-spec-section.md`, which holds each decision's rejected alternatives). "Q" and "Decision" numbers are NEU-2162's measurement's (`docs/measurements/outside-spending-2024.md`). A rule that rests on no measurement says "asserted, not measured" and names the ticket that checks it.

### §6.1 The four kinds and their sources

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

### §6.2 Silver `independent_expenditure`

`sql/silver/09_independent_expenditure.sql`, v1's model (NEU-2057), extended by NEU-2165 and NEU-2167. Key `(cycle, source, source_record_id)`, unchanged. v1's twelve columns keep their order and meaning; six are appended.

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
| `source_file` | `pas2` | `independent_expenditure` | NEU-2165 |
| `payee_name` | `NAME` | `pay` | NEU-2165 |
| `purpose` | NULL: `pas2` has none | `pur` | NEU-2165 |
| `dissemination_date` | NULL | `dissem_dt` | NEU-2165 |
| `communication_type`, `communication_class` | `COMMUNICATION_TP` and `COMMUNICATION_CLASS` of the `CommunicationCosts` row with the same `SUB_ID`, for a `communication_cost` row; else NULL | NULL | NEU-2167 |

- **`pas2` rows are v1's, unchanged**: the same rows, amounts, candidates and kinds. Memo lines stay dropped (282 coordinated lines, $1,414,204, in 2024, Q10b; no 24F or 24N line is a memo line, Q8).
- **Amounts.** `pas2` writes whole dollars (Q4h); the 24/48-hour file carries cents. Each is kept as its file gives it, a negative one included.
- **Dates.** 25,780 of 2024's 24/48-hour rows have no `exp_date` and 14,141 no `dissem_dt`; none lacks both (Q1). A spender's impossible year is kept as filed: dissemination dates run from 2004 to 2042.
- **A row with no side.** One added row of 2024 ($85) has a blank `sup_opp` (Q6d). It is in its spender's total and in no candidate's or race's figure, since those are by side.
- **Communication costs.** Every row of the CSV is a `pas2` 24F or 24N row under the same `SUB_ID`, filer, filing, `TRAN_ID` and candidate, in every cycle 2010–2026 but one 2022 row, and the amounts are equal once the CSV's cents are dropped (Q8c, Q8l, Q12g; Decision 5). `pas2` holds 20 rows the CSV lacks ($59,480, none naming a candidate): they count, with both new columns NULL. A CSV row with no `pas2` row adds nothing. `COMMUNICATION_TP` is `DM` (direct mail) on $6.19M of 2024 and `COMMUNICATION_CLASS` `M` on $7.05M; both are kept as filed. The CSV's `PURPOSE` is never filled (Q1), so `purpose` stays NULL. Form 7's reported total is in no file fundlens reads, so no spender's sum is checked (Q8).
- **Party coordinated expenditures.** `pas2`'s 24C rows as v1 holds them, credited to the candidate named. 43 of 2024's 47 spenders are party committees (`cm` type `Y`), and each party committee matches its `reported_total.party_coordinated` within 1% but four that report $20,650 and file $3,000 (Q10). Three spenders are no party: a House campaign ($85,250), a union PAC ($3,000) and a Democratic club ($1,287). They count as filed (Decision 7). $89,034,392 names a candidate and $88,084,906 reaches a race (Q10h).

**Checks.** v1's five stand (`silver_independent_expenditure_key`, `_candidate`, `_correction`, `_handoff`, `_not_money`), the side-and-type check applying to `pas2` rows alone. NEU-2165 adds `silver_independent_expenditure_no_double.sql`, which fails the build on a 24/48-hour row that:

- is on a filing another row of the file names in `prev_file_num`;
- is at a spender with a counted `pas2` independent expenditure in the cycle, unless it is dated after the spender's `period_end`;
- is at a spender that has neither a counted `pas2` independent expenditure in the cycle nor a reported figure above $0.

NEU-2167 adds `silver_independent_expenditure_communication.sql`: `communication_type` or `communication_class` is set only on a `communication_cost` row.

**Memory.** Asserted, not measured: the six columns and the added rows are small beside the table (73,841 `pas2` rows in 2024). NEU-2165 reads DuckDB's figure across the model in the transform's `memory after <step>` lines, as §5.1 asks of a new table (`docs/capacity.md`).

### §6.3 What the 24/48-hour file adds

The **24/48-hour file** (`CONTEXT.md`; `independent_expenditure` in the file catalogue, 2010–) holds spenders' 24- and 48-hour reports of independent expenditures: estimates, filed within a day or two, which a periodic report later restates in `pas2` under the same `TRAN_ID` mostly, and under another id, amount or candidate id often enough (Q5). It also holds **hoax filings** (`CONTEXT.md`): sixteen rows of $100M or more hold $44.9B of 2024's $49.7B (Q1j). So the file is never a source of its own. Silver reads it in this order:

1. **Amended filings are dropped: the filing chain** (Decision 2). A row whose `file_num` is named by another row's `prev_file_num` is not read. A chain of amendments needs no walking: each filing but the last is named by its successor. 2024: 61,426 rows kept, 12,023 dropped ($1,340,305,331) (Q3).
   - `prev_file_num` names a filing of the same spender in the file for 1,169 of 1,186 amendments; 17 ($2,539,495) name one the file lacks, and two `A1` filings name none. All are kept. One original is named by two amendments, both kept ($26,315 counted twice) (Q3).
   - What the chain drops and no amendment restates under the same `tran_id` is 1,140 rows, $29,711,780: 824 of them are in `pas2`, 706 under another `tran_id` (Q3n). The amendment renumbered them.
   - Rejected: the row on the highest `file_num` per spender and `tran_id`. NEU-2162's spec fell back on it when amendments carrying under half of their original's transaction ids crossed 1% of amended dollars (1.63%, Q3h). `tran_id` repeats across a spender's filings, so it drops $439,518,994 of distinct expenditures, and it keeps less than the chain in every cycle 2010–2026 (Q3j, Q12d).
2. **A row whose spender is no committee of the cycle in silver `committee` is dropped** (§6.1).
3. **Timeliness** (Decision 4). A row dated after its spender's `reported_total.period_end` is added when the spender has a **track record**: a counted `pas2` independent expenditure in the cycle, or `reported_total.independent_expenditures` above $0.
   - The row's date is §6.2's `date`. A spender with no `reported_total` row, or a NULL `period_end`, has no row added by this rule.
   - It lasts until a periodic report covers the rows: the next build after one arrives has a later `period_end`, and the spending is then `pas2`'s. A build reads `committee_summary` and `pas2` of the same extract.
   - 2026, read live on 2026-11-24: rows after `period_end` hold $1,287,474,092 from 512 spenders, nearly all from the last three weeks of October, and `pas2` already holds 0.46% of them, under NEU-2162's 1% bar; 69% and 87% of the rows dated on or before it are in `pas2` (Q7c, Q7e). Before the track record, the rule adds $1,281,571,904 on 2026 and $28,732 on 2024.
   - **Asserted, not measured:** what the track record leaves out of that $1,281,571,904. NEU-2165 measures it on 2026 and lists the spenders left out.
   - No dollar cap: a spender's last three weeks can dwarf its year to date.
4. **By spender, behind the hoax screen** (Decision 3). A spender with no counted `pas2` independent expenditure in the cycle contributes its remaining rows, those dated on or before its `period_end` or undated, when both hold:
   - `reported_total.independent_expenditures` is above $0;
   - those rows add up to no more than ten times that figure.

   2024: 14 spenders, 100 rows, **$1,001,297**, against $996,357 they report; 13 are Form 5 filers (Earthjustice Action $293,577, FLIC Votes $207,175, Red Wine and Blue $134,695). $251,224 reaches a race and $750,073 names no candidate (Q6d–f).
   - Unscreened it adds $43,906,446,618, of which $43,905,445,320 is from 53 spenders reporting no independent expenditure (Q6c). No kept spender's rows exceed 4.9 times its reported figure, so the tenfold test drops nobody in 2024: it is there for a hoax filer who also reports a small real figure.
   - **What the screen costs.** A real spender that reports no independent expenditure is lost: Shield PAC ($1,225,000, dated 2023), Team Kennedy ($305,101), 19 committees with $3,185,809 in all, and Form 5 filers with no reported total (Q6a–b). Accepted.
   - The measurement compared all of a spender's rows with its reported figure; this rule compares those to `period_end`, the period the figure covers. On 2024 the two differ by at most timeliness's $28,732.
   - Web-form ids (`tran_id` beginning `WFT`) decide nothing: 85 committees and two Form 5 filers filed real lines on FEC's web form in 2024 (Q2c).
5. **Every other row is not read.** That includes every row, to its `period_end`, of a spender `pas2` holds an independent expenditure for.
   - Those rows are the same spending. After every rung of the measurement's ladder, $71,450,772 of them stay unmatched, 1.62% of counted dollars, and `pas2` keeps $212,480,816 of its own unmatched; spender by spender the two balance, the file higher by $40,549,211 in all, 0.92% (Q5p, Q5r). Added by row, 2024 would gain $68,376,504 with web-form ids aside, most of it counted already.
   - **What it costs.** Where the file holds more than `pas2` for such a spender, the difference is not added: the NRCC's $14.1M of late lines in 2024 (Q5r).
   - The ladder, its fourth rung included, is the measurement's evidence that the rows are the same. No pipeline rule matches a row to a row.

**2024 on this contract.** Rows with `source_file = 'independent_expenditure'` should come to the 14 spenders' $1,001,297, plus whatever timeliness adds at other spenders, at most $28,732. NEU-2165's definition of done is within 1% of $1,001,297 for the by-spender rows, with each timeliness row listed.

**Every transform logs** the rows and dollars added by each of the two rules and the largest single added row with its spender, so a hoax filing that passes is seen in the run's log.

**Model order.** The rules read `reported_total`, which `10_reported_total.sql` builds after this model today, and which exists from 2008. NEU-2165 arranges the order.

### §6.4 Silver `electioneering_communication`

`sql/silver/NN_electioneering_communication.sql` (NEU-2166), from `ElectioneeringComm` (2010–). Key `(cycle, source, source_record_id)`. `source` is `fec` and `jurisdiction` `US`.

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
- **No candidate.** 24 rows of 2024 ($2,179,759) name none: trade groups' and nonprofits' ads about an issue. One names an id `cn` lacks (`P60012143`, $32,000) (Q9e). Each is kept with candidate and race NULL, in its spender's total alone. Blank-candidate rows begin in 2016 (Q12f). So 2024's rows reaching a candidate and a race come to $7,230,615: $9,442,374 less those two figures. Derived by subtraction, not measured; NEU-2166 confirms it.
- **No amendment rule.** The file has no filing number and no amendment indicator. The Form 9s support one rule, that a row restated by an amendment of the same report is one payment and a repeat across two reports is two, and the file cannot apply it (Q9p). So a restatement is counted twice: $33,750 in 2024, 0.36% (Issue One Action's `1849492` amending `1816711`), and about $73,000 in 2010. Rejected: keeping the highest image number among rows equal on spender, payee, date, amount and candidate, which is exact in 2024 and drops $3,101,798 of 2010's $71,692,553, most of it separate real reports (Q9q).
- A row whose spender `cm` lacks is dropped (none in 2024: all 25 spenders are type `E`, Q9a).

**Checks** (NEU-2166): `silver_electioneering_communication_key.sql` (key unique); `..._committee.sql` (spender in `committee`); `..._candidate.sql` (a candidate is the cycle's, is no alias and is no handoff's first candidate on or after the handoff; a race is its candidate's); `..._copies.sql` (no disbursement has more rows than its `candidate_count`).

NEU-2166's definition of done is within 1% of 67 rows and $9,442,374.

### §6.5 Gold

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
- **`race_top_committee` is unchanged.** Its `ie` rows remain a spender's independent expenditures on the race, for and against summed, and now include the 24/48-hour rows. NEU-2170 decides which list a page shows.
- **The handoff** follows silver's dated rule in every kind: spending naming Biden on or after 2024-07-21 is Harris's.
- Outside spending is in no receipt total, no `cycle.total_amount`, no donor figure, no `total_operating_expenditures` and no top-donor, top-organization or top-payee list.
- **Checks** (gold): a race's six columns add up to its `outside_spending_total`; each of a race's columns equals the sum over its `race_candidate` rows; a committee's four totals add up to its `outside_spending_total`; every `race_top_spender` amount equals its silver sum; ranks are contiguous (`gold_rank_contiguous.sql`); no receipt or spending total moves on the fixture.
- **The API and pages** (NEU-2169, NEU-2170) read these fields. The itemized independent-expenditure route (v1 §7.2) scans `kind = 'ie'`, so it lists the 24/48-hour rows without a change; NEU-2169 adds `source_file`, `payee_name` and `purpose` to its rows, and a page marks a 24/48-hour row as an estimate from a 24- or 48-hour report.

**The five races.** NEU-2171 compares gold with the measurement's Q13: Ohio, Pennsylvania, Montana, Michigan and Wisconsin, per candidate and kind. Q13's "added" column is the screened by-spender rule's, and its electioneering column counts every row of the file. The two copies this contract drops ($38,500) name House candidates, so no Senate figure differs for them. This contract can differ from Q13 only by timeliness, at most $28,732 across 2024, and NEU-2171 explains any other gap.

### §6.6 What each cycle range has

| | 2020– | 2010–2018 | 1980–2008 |
|---|---|---|---|
| Independent expenditures, communication costs, party coordinated expenditures from `pas2` | yes | yes | yes |
| 24/48-hour rows (§6.3) | yes | yes | none: no file |
| Hoax filings in the file | $1.74B (2020) to $38.5B (2026) at spenders `cm` lacks | under $133,000 a cycle | — |
| `communication_type`, `communication_class` | yes | yes | NULL: no CSV |
| `electioneering_communication` | yes | yes; blank candidates from 2016; splits off by a cent in 2010, 2012, 2018 | an empty partition (§2) |
| `reported_total` for the screen | yes | yes | — |

No cycle breaks a 2024 rule as written (Q12; Decision 9). The screen and the track record apply in every cycle, not from 2020 alone: one rule, and a hoax filing can be filed for any cycle. The chain drops more in 2022 ($13.3B, hoax filings amended by hoax filings) and 2020 ($1.21B) (Q12d). Every CSV header equals 2024's in every cycle, and only 2016 and 2018 have cells that fail a cast, 12 and 1 (Q12a, Q12b): NEU-2164 reads them as NULL. 2026's coordinated expenditures are four times 2024's ($351,217,482) with the cycle not over (Q12h). **Asserted, not measured:** that (`file_num`, `tran_id`) is unique in every cycle's 24/48-hour file, as it is in 2024's; the key check fails a build where it is not, and NEU-2180's backfill finds out.

### §6.7 Dataset and older builds

- `electioneering_communication` joins the public dataset (§8): NEU-2166 adds it to `DATASET_TABLES`, `columns.yaml`, the schema, the changelog, the README and `paths.BACKFILL_PENDING` in the PR that builds it. Its README entry says: sum `amount`, never `disbursement_amount`; a row has no side; a restated report may be counted twice (§6.4); and outside spending is never to be added to `contribution` amounts.
- `independent_expenditure`'s six columns are additive changes, each with a `CHANGELOG.md` entry and a `columns.yaml` description by the ticket that adds it (NEU-2165, NEU-2167). Its table description stops saying every row is from `pas2`. Its README entry says: tell the kinds apart by `kind`; a row with `source_file = 'independent_expenditure'` is a 24- or 48-hour report's estimate, and leaves the table when a periodic report restates it, so its `source_record_id` is not stable from one snapshot to the next.
- The table is in every build, so it is no backfill-pending table. A cycle built before a column existed has no such column and reads it as NULL, as `organization_receipt.is_returned_cost` was handled (changelog, 2026-11-20). Gold reads none of the six. NEU-2180's backfill rebuilds every cycle with them.

## 3. `CONTEXT.md`

Written in this session, uncommitted:

- Under **Money**, after Independent expenditure: **Outside spending**, **Electioneering communication**, **Communication cost**, **Party coordinated expenditure**, **Hoax filing**.
- **Independent expenditure** now opens "Money a spender spends … : one kind of outside spending", and its avoid list says why "outside money" is avoided.
- Under **Parties**, after Payee: **Spender**, **Non-committee spender**.
- Under **Data tiers**, after Undated file: **24/48-hour file**.

`/implementit` commits them as they stand and checks that §6's text uses them: "spender", never "sponsor" or "filer" for who spent; "outside spending", never "outside money"; "hoax filing", never "web-form hoax"; "24/48-hour file", never "the independent expenditure file". **Superseded filing** is a glossary term with its own rule (a receipt-side amendment told by its repeated gifts): §6 says "a filing an amendment replaced" or "an amended filing" for the 24/48-hour file's chain, never "superseded filing". The measurement's own words ("sponsor", "filer", "superseded", "absent") stay in the measurement.

## 4. The specs' other edits

- **v1 spec §9**, the layout block's table list: add `electioneering_communication` after `operating_expenditure`.
- **Project spec §6**'s opening paragraph: the one change §2 gives.
- **Project spec §8** already names NEU-2163 as M3's spec ticket. No edit.
- v1 §4's `independent_expenditure` row ("Amendments and the 24/48-hour reports are NEU-2162's and NEU-2165's") is NEU-2165's to amend when it builds. v1 §7.1's table rows are NEU-2168's, and v1 §7.2's NEU-2169's, as v1's gold and API tickets added theirs.
- Project spec §4.1's "Not held" still stands: Form 7's `TTL_COMMUNICATION_COST` is held nowhere.

## 5. Linear text this spec supersedes

`/implementit` patches each, changing only the named text, and appends to each "Amended 2026-11-24 by project spec §6 (NEU-2163)."

| Where | Text | Becomes |
|---|---|---|
| Milestone M3 All outside spending, shared contracts | The four bullets | §2's amended five |
| Milestone M3, description | "independent expenditures from spenders that are not committees (the 24/48-hour file, 2010–)" | "independent expenditures by committees and non-committee spenders, with the 24/48-hour file's late and missing reports (2010–)" |
| NEU-2161 | "but not spending by groups and individuals that are not committees" and the Evidence's reading of the 24/48-hour file | Non-committee spenders' independent expenditures are in `pas2` and on race pages already (153 Form 5 filers, $84.9M in 2024); what is missing is the 24/48-hour file's late and missing reports, electioneering communications, communication costs and party coordinated expenditures. Its "→ silver `communication_cost`" step becomes "→ communication costs' type and class". |
| NEU-2164 | "a non-committee spender's 24-hour IE, a committee's 48-hour IE that is also in the fixture `pas2`, an amended 24-hour row" | The fixture rows §6 needs: a Form 5 filer with a reported figure and no `pas2` row (added); one whose rows exceed ten times its reported figure, and a hoax filing at a spender `cm` lacks (not added); a committee's row dated after its `period_end` (added) and one before (not); a filing named by another's `prev_file_num` (dropped); a one-candidate electioneering disbursement on two rows; a two-candidate one with no candidate; a communication cost in both `pas2` and the CSV. The measurement's "For NEU-2163 to NEU-2171" lists real rows to model them on. |
| NEU-2165 | Title, and "which holds committees' expenditures only … they appear only in the 24/48-hour file" | Title: "Silver: the 24/48-hour file's late and missing independent expenditures into `independent_expenditure`". `pas2` holds non-committee spenders too; the file adds §6.3's two rules. |
| NEU-2165 | "with `source_file = 'independent_expenditure'`, `spender_is_committee`, payee, purpose and dissemination date" | §6.2's columns: `source_file`, `payee_name`, `purpose`, `dissemination_date`. No `spender_*` column. |
| NEU-2165 | "a 24/48-hour row matching a `pas2` row by spec §6's rule is never added" and the `no_double` check | No row is matched. `silver_independent_expenditure_no_double.sql` is §6.2's three conditions. |
| NEU-2165 | "match NEU-2162's 'only in 24/48-hour' figure within 1%" | Within 1% of $1,001,297 for the by-spender rows on 2024, each timeliness row listed (at most $28,732); and on 2026, what the track record leaves out of $1,281,571,904, listed by spender. |
| NEU-2166 | Title, "deduplicated by spec §6's rule", "`candidate_share`" | Title: "Silver `electioneering_communication` with per-candidate shares, a disbursement's copies dropped". §6.4's columns (`amount`, `disbursement_amount`, `candidate_count`, `committee_id`). No amendment rule. |
| NEU-2166 | "every `candidate_id` in `candidate` or the row counted in the unmatched report … per disbursement, shares sum to the reported amount within a cent" | §6.4's four checks. A row naming no candidate of the cycle is kept with a NULL candidate, as an independent expenditure is; the split is as filed and no check enforces it. The definition of done is 67 rows, $9,442,374, within 1%. |
| NEU-2167 | "either the `communication_cost` table … or … the `pas2` rows alone with the CSV's extra columns joined on" | The second: `communication_type` and `communication_class` by `SUB_ID`; `amount` stays `pas2`'s. |
| NEU-2167 | "v1's 24C rows confirmed as `kind = 'party_coordinated'`" | `kind` stays `coordinated`; gold names the kind `party_coordinated`. |
| NEU-2167 | "no communication cost counted from both sources; every row has a candidate or is in the unmatched report" | `silver_independent_expenditure_communication.sql` (§6.2). The definition of done is 799 rows, $7,157,987 and 812 rows, $89,161,724, each within 1% and unchanged from the build before. |
| NEU-2168 | "`outside_spending` by kind and support/oppose … and `electioneering_share`" | §6.5's four columns on `candidate_cycle`, `race_candidate` and `race`; three kind totals and `outside_spending_total` on `committee_cycle`. |
| NEU-2168 | "`race_top_spender`: top 25 spenders per race across kinds (spender id when a committee, name otherwise)" | §6.5's table: rank ≤ 100, one row per spender, candidate, kind and side; `committee_id` always set. |
| NEU-2168 | "the non-committee spender and the union are in `race_top_spender`" | Unchanged in meaning; both have a `committee_id`. |
| NEU-2169 | "`top_spenders` (rank, spender name, committee id when a committee, …)" and "the non-committee spender with a NULL committee id" | Each row has `committee_id`, `candidate_id` and `is_committee` (false for `committee.type` `I`, `C`, `E`). Itemized independent-expenditure rows gain `source_file`, `payee_name`, `purpose`. |
| NEU-2170 | "showing non-committee spenders as plain names with a 'not a committee' badge" and "a non-committee spender renders without a link" | Every spender links to its committee page; a non-committee spender carries the badge. Each top-spender row names its candidate. A 24/48-hour row is marked an estimate. Its "Not in scope: spender pages for non-committee spenders" goes: they have committee pages. |
| NEU-2171 | "the 10 largest non-committee spenders reviewed by hand against their FEC filings" | The 14 spenders the by-spender rule adds (Q6f), and the largest added row of the run's log, each read against its filing; the five races against Q13 with §6.5's two known differences. |

## 6. Acceptance criteria

- [ ] Project spec §6 holds §6.1–§6.7 as written in §2 above, under the amended opening paragraph and the amended shared contracts, with no "Filled by" line.
- [ ] Every rule in §6 that rests on the measurement cites its question or decision; each unmeasured one says "asserted, not measured" and names the ticket that checks it (the track record's cost on 2026, the 24/48-hour key in other cycles, the model's memory).
- [ ] §6.1's table gives each of the four kinds its silver home, source, side and 2024 figure.
- [ ] §6.2's table names a source, or NULL, for every column on both `pas2` and 24/48-hour rows, and §6.3 gives the five steps in order with the 2024 target of $1,001,297.
- [ ] §6.4 gives `electioneering_communication`'s columns, key, row rule and checks, and the 2024 target of 67 rows and $9,442,374.
- [ ] §6.5 gives every gold table's added columns, `race_top_spender`'s columns and key, the 0 and NULL rule and the gold checks.
- [ ] `CONTEXT.md` defines Outside spending, Electioneering communication, Communication cost, Party coordinated expenditure, Hoax filing, Spender, Non-committee spender and 24/48-hour file, each with an avoid list; Independent expenditure's entry names the spender and the umbrella.
- [ ] `grep -n -i -w "sponsor\|sponsors\|outside money\|web-form hoax\|superseded" docs/specs/fundlens-every-fec-dollar-project-spec.md` finds nothing in §6 (§4 and §5 use "superseded filing" in its glossary sense).
- [ ] v1 spec §9 lists `electioneering_communication`.
- [ ] The milestone's contracts and description, NEU-2161 and the eight descriptions of §5 are patched in Linear.
- [ ] The PR changes nothing under `sql/`, `src/`, `frontend/` or `tests/`.

## 7. Out of scope

- Any code: the catalogue (NEU-2164), silver (NEU-2165, NEU-2166, NEU-2167), gold (NEU-2168), API (NEU-2169), pages (NEU-2170), the run (NEU-2171).
- v1 §4's `independent_expenditure` row, v1 §7.1's table rows and v1 §7.2's endpoints (their tickets).
- A reconciliation `measure` for independent expenditures or party coordinated expenditures against `reported_total`; holding Form 7's reported communication cost.
- Recovering the real spenders the screen loses (Shield PAC, Team Kennedy), the money the 24/48-hour file holds beyond `pas2` for a spender `pas2` has (the NRCC's $14.1M), and the spender `cm` lacks ($64,107).
- Telling an amended electioneering report from a second report: it needs the Form 9s themselves (project spec §9, NEU-2181).
- The donors behind non-committee spenders (Form 5 and Form 9 schedules; M5, NEU-2181).
- A payee key, payee page or spending category for outside spending's payees: ADR-0012's payees are operating expenditures'.
- Removing `race_top_committee`'s `ie` rows, or renaming v1's `ie_support`, `ie_oppose` and `ie_total`.
- Measuring any cycle but 2024 in depth: Q12 is one profile row per cycle, and the track record's cost is NEU-2165's to measure on 2026.
