# NEU-2173 — Measure `leadership`, `lobbyist` and `lobbyist_bundle`, and write spec §7

**Ticket:** [NEU-2173](https://linear.app/neuroticsasquatch/issue/NEU-2173) · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Milestone:** M4 Leadership PACs and lobbyist bundling · **Parent story:** NEU-2172
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §7 (a stub this ticket fills, holding the milestone's two **Shared contracts**), §2 (older builds), §3.1 (the three files, catalogued by NEU-2174), §4.1 (`reported_total`), §4.3 (the credit rule), §8 (public dataset) · **v1 spec:** §4 (`committee`, `candidate`, aliases), §7.1, §9 · **Glossary:** `CONTEXT.md` · **ADRs:** 0002 (a cycle rebuilds from its own bronze)
**Blocked by:** NEU-2137 (Done). **Blocks:** NEU-2174, and through it NEU-2175 to NEU-2179. **Related:** NEU-2138 (CSV files and undated files, shipped), NEU-2149 and NEU-2162 (the measurements whose shape and setup this one reuses), NEU-2180 (the backfill, which needs this ticket's sponsor list for every cycle), NEU-2181 (M5: Form 3L's named bundlers).

Planned 2026-11-25. `/implementit NEU-2173` produces **one PR** in two stages with a **checkpoint** between them (§5): first `docs/measurements/leadership-lobbyist-2024.md` and `src/fundlens/fec/leadership_sponsors.csv`, from a read-only run in prod's `pipeline` container; then, after the user has settled the decisions the measurement leaves open, project spec §7, the other spec edits of §7 below and the Linear corrections of §8. Nothing under `sql/`, `frontend/` or `tests/` changes, and nothing reads the CSV until NEU-2175.

## 1. What and why

M4 links a member to their leadership PAC, flags the PACs lobbyists and registrants run, and shows what lobbyists bundled for a recipient. Seven tickets build that from a contract nobody has written, over three files nobody had opened. This ticket opens them, measures how they key to `cm` and `cn`, and writes the contract.

The ticket and its siblings predate any reading of the files. Read on 2026-11-25 (§3), they differ from the files in these places:

1. **`leadership` names its sponsor, and gives no candidate id.** `Sponsor_Name` is text (`CLYBURN, JAMES E`), blank on 288 of 2024's 833 rows. The ticket's `leadership_sponsor_candidate_id` has to be matched, not read.
2. **`leadership` has one row per committee.** No PAC has two sponsor rows in 2024. It also carries cash, receipts and disbursements, which `reported_total` may already hold.
3. **`lobbyist.csv` is one row per filing, not per committee:** 14,186 rows for 2,774 committees, filed 2009 to 2026, `Is_Lobbyist` either `Y` or blank. It is not "per cycle"; a cycle's flag has to be derived from dates.
4. **`lobbyist_bundle.csv` names no lobbyist and no bundler.** A row is one Form 3L report at a recipient committee with two totals. The ticket's grain "per lobbyist, recipient and covered period", and NEU-2176's `committee_top_bundler`, fall away. Named bundlers are M5's (project spec §9).
5. **Amendments in the bundling file are extra rows with no indicator:** 89 committee-and-period keys sit on 200 rows.
6. **Silver `committee.designation` already holds `cm`'s code**, where FEC writes `D` for a leadership PAC and `B` for a lobbyist/registrant PAC. The flags the ticket wants from the files may be in every build already.

### 1.1 Decisions pinned (grilled 2026-11-25)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Sponsor link | **A name rule, then a hand list.** `Sponsor_Name` is matched to the cycle's silver `candidate` by a normalized-name rule (Q4). `src/fundlens/fec/leadership_sponsors.csv` settles what the rule misses, gets wrong or finds twice, as `ie_candidate_corrections.csv` does for independent expenditures. OpenFEC's `sponsor_candidate_ids` is the check on the rule, never a pipeline source. | The file is FEC's only bulk statement of a sponsor. Rejected: the rule alone (some members' pages lack their PAC); OpenFEC as the source (not a bulk file: breaks project spec §2's "files read", and puts an API key and rate limits in the pipeline); the name as text with no link (S4's Done line cannot be met). |
| Blank sponsors | **A correction maps a name the file gives; it never names a sponsor where the file is blank.** A blank stays a leadership PAC with no sponsor (`CONTEXT.md`, Sponsor). | The list's truth would live outside the bulk files and grow by hundreds of rows a cycle. Q5 still counts the blanks OpenFEC names a sponsor for; over 10% of them is reported at the checkpoint as a finding, not acted on. Rejected: filling blanks from FEC's committee page; filling only the largest PACs' (an arbitrary line). |
| Which candidates a name may match | **The cycle's own `candidate` table; the list for the rest.** Silver matches within the cycle (its `cn` lists sitting senators not up, and anyone still registered). A sponsor absent from it keeps the name, and gets an id only if the list gives one. Gold shows the link whenever it has a candidate page for the id, in any cycle. | Each cycle still rebuilds from its own bronze (ADR-0002). Rejected: no list rows for absentees (retired leaders' PACs stay unlinked); matching across all cycles in gold (a common name matches another decade's candidate, and the public silver table would carry no id). |
| Flag source | **`cm`'s designation, at a 99% bar.** If a file's committees and `cm`'s `D` (or `B`) committees agree at 99% or more both ways, in 2024 and in every profiled cycle, the flag is `committee.designation`. `leadership` is then read for the sponsor alone, and `lobbyist.csv` moves to project spec §3.2's not-read table, so NEU-2174 catalogues two files. Below the bar, the file is the flag's source and the document says what differs (Q2, Q7). | One source for a fact `cm` may already state, and a flag for cycles before 2010. Rejected: the files always (no flag before 2010, a second source for one fact); either source (a disagreement is hidden, not explained). |
| Bundled total | **The greater of the two, per half-year.** For a committee and half-year: the larger of its semi-annual figure and the sum of that half's covered-period figures; a cycle's total is its four halves added (`CONTEXT.md`, Bundling report). Q10 prints all three totals. | A lobbyist over the threshold for a quarter is over it for the half, so the two figures never add; the larger covers a filer who leaves one blank. Rejected: semi-annual only (a committee that fills only the period figure shows nothing); covered periods only (misses a lobbyist who crossed the threshold only over six months: DCCC's first half of 2024 is about $5.5M by month against $6.62M semi-annual); deciding after measuring. |
| The bundling table | **Silver `bundling_report`, one row per Form 3L report as filed.** Amended reports are kept and flagged superseded; both filed amounts are kept; an `amount` column holds what the row adds to the total under the rule above, so a reader sums one column. | The file holds reports, not gifts. Rejected: the tickets' `bundled_contribution` (a reader expects one row per contribution and tries to join donors); a derived row per committee and half-year (the reports and amendments behind a figure are not in the dataset, so no total can be checked against FEC's filings). |
| The sponsor's home | **Silver `leadership_pac`, one row per leadership PAC of the file and cycle:** the sponsor's name as filed and the matched candidate id. | The user's choice. It leaves `committee` untouched and the model self-contained, at the cost of one more public table and one more backfill-pending table. Rejected: `sponsor_name` and `sponsor_candidate_id` columns on `committee` (this spec's recommendation: no join, no pending table); the ticket's long `committee_attribute` (mixed types in one column, a pivot on every read). |
| Glossary | **Sponsor means a leadership PAC's, and nothing else.** `CONTEXT.md` gained **Leadership PAC**, **Sponsor**, **Lobbyist/registrant PAC**, **Bundled contributions** and **Bundling report** in this session (uncommitted, shipping in this PR). Spender's entry still bars "sponsor" for an electioneering communication's spender. | FEC's column and Form 1 say sponsor. Rejected: "leader" (nobody's word, and most sponsors hold no post); no term (the word enters the dataset undefined). |
| The list's scope | **Every cycle 2010 to 2026, committed in this PR.** `leadership_sponsors.csv` has `cycle, committee_id, sponsor_name, candidate_id, source`, key `(cycle, committee_id)`; a row overrides the rule. `source` cites FEC's committee page or a filing. | The list must exist before NEU-2180's backfill, and this ticket has the files and the check open. Rejected: 2024 here and the rest in NEU-2175 (silver's PR grows a research task) or in a new ticket. |
| §7's remaining decisions | **A checkpoint after measuring** (§5). Still one ticket and one PR. | Every M1 to M3 measurement overturned something its ticket assumed. Rejected: bars only, with no stop (a surprise gets a rule first seen in the diff); two PRs (the split the ticket rejected for files this small). |
| Where the queries run | **Prod's `pipeline` container**, read-only, over each cycle's live-build silver, as NEU-2149 and NEU-2162 ran. | Dev bronze is the seeded fixture. Rejected: this worktree's container with files from FEC (aliases and `reported_total` re-derived outside the live builds may drift from them). |

Defaults this spec pins, confirmed in one question and not grilled singly:

- **The name rule adopted** is the loosest rung of Q4's ladder whose matches agree with OpenFEC's sponsor ids at **99% or better** in 2024 and in every profiled cycle.
- **A Form 3L amendment:** among rows of one committee with the same coverage start and end, the latest `Receipt_Date` is kept, then the higher image number in `Link_Image`; the others are superseded. Adopted unless Q9 finds kept rows of one committee whose periods overlap (other than a period inside its own half-year) holding over 1% of the file's dollars; then Q9 says what they are and the checkpoint decides.
- **A report's cycle** is its `Coverage_End_Date`'s. A half-year is January to June or July to December of that date.
- **`leadership`'s `Cash_on_Hand`, `Total_Receipt`, `Total_Disbursement` and `Coverage_End_Date` are not held** if they equal `reported_total`'s figures within $1 at 99% of committees both have (Q3).
- **Cycles:** 2024 in full; one profile row per cycle 2010 to 2026 for `leadership`; the two undated files whole, split by cycle.

## 2. Definitions used in the document

- **Leadership PAC, sponsor, lobbyist/registrant PAC, bundled contributions, bundling report:** `CONTEXT.md`'s. **Recipient:** the committee a bundling report is filed by. Never "bundler" for a committee, and never "sponsor" for a spender.
- **Covered period:** a row's `Coverage_Start_Date` to `Coverage_End_Date`, a month, a quarter or a pre- or post-election stretch. **Period amount:** `Quarterly_Contribution`, which monthly filers fill too. **Semi-annual amount:** `Semi_Annual_Contribution`. Not "reporting period": that is `reported_total`'s term.
- **Kept report:** a row the amendment default keeps. **Half-year figure:** the semi-annual amount on the kept report with the latest coverage end in the half that carries one above $0.
- **Name, normalized:** upper case, punctuation and suffixes (`JR`, `SR`, `II`…) removed, runs of spaces made one. **Candidate, for matching:** a row of the cycle's silver `candidate`, resolved through `alias_of`.
- **Amounts** are `TRY_CAST(… AS DECIMAL(14,2))` inside each query and **dates** `try_strptime(…, '%d-%b-%y')`, failures counted, so a bad cell is a figure, not a read error.

## 3. Preconditions

- Live builds' silver `committee`, `candidate`, `candidate_committee_link` and `reported_total` for every even cycle 2010 to 2026, and gold `committee_cycle` for 2024. The document records each cycle's `build_id`.
- No pipeline step running (the Sunday 03:00 UTC scheduled run, or a runbook in progress), and **no merge to `main` while the run is in progress** (`docs/runbooks/weekly.md`, Facts).
- **An api.data.gov key from the user**, for Q5 and Q12: `DEMO_KEY` allows 50 requests a day, enough for 2024 alone. It is exported as `FEC_API_KEY` in the shell that runs the scripts, sent in the `X-Api-Key` header, and never written to a script, the document, a URL or a commit.
- The files are fetched into the work dir with their `Last-Modified` recorded, **not catalogued and not in bronze** (that is NEU-2174).

Read on 2026-11-25 from HTTP headers and from each file streamed through `awk` (a rough count: every figure here is restated by Q1 in DuckDB):

| | |
|---|---|
| `leadership2024.csv` | 120,104 bytes, `Last-Modified` 2026-11-25. 8 columns: `Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt`. 833 rows, 833 committees. `Sponsor_Name` blank on 288; one name is on three rows and several on two. `Coverage_End_Date` is `DD-MON-YY`, `31-DEC-24` on 722 rows and blank on 19 |
| Other years | `leadership2026.csv` 133,894 bytes; `leadership2010.csv` 61,357 bytes, `Last-Modified` 2 January 2025. `leadership2023.csv` and `leadership2008.csv` are 404s: even years only, from 2010, as project spec §3.1 has it |
| `lobbyist.csv` | 2,046,415 bytes. 5 columns: `Link_Image, Committee_Name, Committee_Id, Date_Filed, Is_Lobbyist`. 14,186 rows, 2,774 committees, 1,931 of them on more than one row (one on over 15). `Is_Lobbyist` is `Y` on 12,570 rows and blank on 1,616. `Date_Filed` runs 2009 to 2026: 1,649 rows in 2009, 617 to 1,154 a year after |
| `lobbyist_bundle.csv` | 347,542 bytes. 11 columns: `Committee_Id, Committee_Name, Link_Image, Committee_Election_State, Committee_Election_District, Report_Type, Receipt_Date, Coverage_Start_Date, Coverage_End_Date, Quarterly_Contribution, Semi_Annual_Contribution`. 1,929 rows, 433 committees. Both amounts are 0 on 417 rows; the period amount is above 0 on 1,260 and the semi-annual on 771. They sum to $307,126,557 and $294,264,771. 34 `Report_Type` strings, several for one report (`QUARTERLY YEAR END / SEMI-ANN`, `QUARTERLY SEMI-ANNUAL (YE)`). Coverage ends run 2009 to 2026 and are blank on 14 rows. 89 (committee, coverage start, coverage end) keys are on 200 rows: DCCC's June 2024 report is there twice, received 19 July 2024 ($73,500 and $6,621,807.50) and 23 October 2026 ($156,100 and $6,701,907.50) |
| All three | Every data field double-quoted, header unquoted, no line with a field count off its header: project spec §3's dialect. Each URL answers 302 to an S3 address, so the fetch follows redirects |

**Asserted, not measured**, each checked by the query named:

- That `cm`'s `CMTE_DSGN` `D` and `B` mean leadership PAC and lobbyist/registrant PAC in every cycle 2010 to 2026 (Q2, Q7, Q12).
- That `Sponsor_Name` is written as `cn` writes the candidate's name (Q4).
- That `GET https://api.open.fec.gov/v1/committees/?designation=D&cycle=<yyyy>&per_page=100` returns `sponsor_candidate_ids` on each result. If not, `/v1/committee/<id>/` is read for each named-sponsor PAC, and the document says so (Q5).
- That a lobbyist over Form 3L's threshold in a covered period is over it in the half-year, so a half's semi-annual amount is never below its period amounts added (Q10).
- That a blank `Is_Lobbyist` is a filing that left the box unticked (Q7).
- That bundled contributions are individuals' gifts already in `contribution`, the milestone's contract (Q11 tests what a total can: no row of the file names a gift).

## 4. The run

In prod's `pipeline` container on `music-box-dancer`. The setup script and each block are files under `~/measure-leadership-lobbyist-2024` on the VM, written there as files and never pasted. The user runs them in the Terminal panel. The document carries every block verbatim with its output, in the shape of `docs/measurements/outside-spending-2024.md`.

### 4.1 Setup script

`outside-spending-2024.md`'s setup with these changes (read its helpers again at the run's SHA): `work = scratch / "measure-leadership-lobbyist-2024"`; `fetch`, `view_csv`, `silver` and `show` as they stand; `openfec(path, **params)`, which pages a list endpoint with the key from the environment, caches each response under `work` and sleeps to stay under the key's hourly limit. `work` is deleted at the end and the document says so.

### 4.2 Queries and figures

Each is one or more SQL blocks, dated, followed by its result and a sentence or two of reading.

**Q1 — Shape.** Per file: bytes, lines, header as served, fields per line, dialect against project spec §3. Cells failing an amount or date cast. Keys: `Committee_Id` in `leadership`; (`Committee_Id`, `Date_Filed`, `Link_Image`) in `lobbyist`; (`Committee_Id`, coverage start, coverage end, `Receipt_Date`, `Link_Image`) in the bundling file; fully identical rows in each. `Is_Lobbyist` and `Report_Type` by value. This restates §3's table.

**Q2 — `leadership` against `cm` (2024).** The file's committees against silver `committee` with `designation = 'D'`: in both, file only, `cm` only, each by committee type and with its receipts. File-only committees' designations; rows joining no committee. The **decision line**: the 99% bar for 2024 (Q12 completes it).

**Q3 — `leadership`'s figures against `reported_total` (2024).** `Total_Receipt`, `Total_Disbursement`, `Cash_on_Hand` and `Coverage_End_Date` against `receipts`, `disbursements`, `cash_on_hand_end` and `period_end`: equal within $1, different, absent from one. The **decision line**: held or not, by §1.1's default.

**Q4 — Sponsors and the name rule (2024).** Named and blank PACs, with receipts. Names holding two people (`&`, ` AND `, `/`, `;`). Sponsors with several PACs. The ladder against the cycle's candidates: rung 1, the normalized name equal; rung 2, last name and first given name equal (the candidate-alias rule's key). Per rung: one candidate, several ids of one person (by `alias_of`, or the same name for another office), several people, none. Each matched sponsor as standing in a race of the cycle, in `candidate` with no race, or (unmatched) absent. Every unmatched and every several-way name listed.

**Q5 — The check (2024).** OpenFEC's `sponsor_candidate_ids` per leadership PAC. Per rung: the rule's id among OpenFEC's, not among them, OpenFEC has none. PACs OpenFEC gives two sponsors. Blank-sponsor PACs OpenFEC names a sponsor for, as a count and a share of the blanks. The **decision line**: the rung adopted by the 99% bar; the list rows 2024 needs, each with the evidence its `source` will cite; the blank finding against its 10% line.

**Q6 — Leadership PACs and the credit rule (2024).** Any leadership PAC that `04_contribution.sql`'s `linked` rule credits to a candidate (a `ccl` P or A link, or a `principal_committee_id`), with its receipts: the contract says a leadership PAC's money is no candidate's, and such a committee would break it. Whether that candidate is the sponsor.

**Q7 — `lobbyist.csv`.** Rows per committee; `Is_Lobbyist` by filing year; committees whose value changes over time, and in which order. Two per-cycle rules, for each cycle 2010 to 2026: (a) any `Y` filing dated on or before the cycle's last day; (b) the latest filing on or before that day is `Y`. Each against that cycle's `designation = 'B'`: in both, file only, `cm` only; file-only committees' designations and types (a leadership PAC that is also a registrant's has one code in `cm`). The **decision line**: the 99% bar; if met, `lobbyist.csv` is not read; if not, the per-cycle rule that agrees better, and what `cm` misses.

**Q8 — The bundling file's shape.** Rows and recipients by cycle. `Report_Type` grouped to monthly, quarterly, semi-annual, pre- or post-election, other. Covered-period length in days. Recipients by committee type and designation (campaigns, parties, leadership PACs), and those in no cycle's `committee`. Blank coverage dates: what the rows are. Periods crossing a 31 December.

**Q9 — Amendments.** Keys on more than one row: identical, differing in amount, differing in receipt date only. The default's kept and superseded rows and dollars. Ties on receipt date. Kept rows of one committee whose periods overlap, by kind, with dollars and 20 shown. Reports received after their cycle's last day, by how late: a historical cycle's bronze copy is as old as its last extract (NEU-2138), so these are what the backfill and a later re-extract change. The **decision line**: the default adopted, or handed to the checkpoint with its 1% bar's figure.

**Q10 — The total.** Per committee and half-year: the half-year figure, the period amounts added, the greater. Per cycle 2010 to 2026: the three totals, and recipients. Halves where the half-year figure is below the periods' sum (the asserted fact failing): count, dollars, 20 shown. Halves with period amounts and no half-year figure, and the reverse. 2024's 20 largest recipients. The **decision line**: the rule's total per cycle; 2024's is the figure NEU-2175's definition of done is within 1% of.

**Q11 — Bundled against counted money (2024).** Each recipient's bundled total beside gold `committee_cycle.total_individual` and its committee gifts. Recipients whose bundled total exceeds its individual total, listed: each is a recipient whose bundled money cannot all be individuals' counted gifts.

**Q12 — Every cycle's profile (2010–2026).** For each `leadership<yyyy>.csv`: bytes, `Last-Modified`, header equal to 2024's, rows, committees on two rows, blank sponsors, each rung's match rates, agreement with OpenFEC, agreement with `designation = 'D'`, and that cycle's list rows. The whole of `leadership_sponsors.csv` is built from this query's residue. A closing paragraph names each cycle where a 2024 rule cannot apply as written, for §7 and NEU-2180.

**Q13 — What NEU-2179 checks.** 2024's ten leadership PACs with the largest receipts that have a matched sponsor, with sponsor and id; five recipients' bundled totals under the rule, with the kept reports behind each.

### 4.3 The document and the list

`docs/measurements/leadership-lobbyist-2024.md`: a header table (run times, `main` SHA, container, DuckDB version, each cycle's live build, each file's URL, `Last-Modified`, size and download time, the OpenFEC calls made); **Headline**; **How to re-run** and the setup script; Q1–Q13; **Decisions** (flag source for each file; the name rule and the list; `leadership`'s figures; the lobbyist per-cycle rule if the file is read; the amendment rule; the bundled total; cycles where a rule does not apply), each with its bar applied; **For NEU-2174 to NEU-2180**, what each takes.

`src/fundlens/fec/leadership_sponsors.csv`: header `cycle,committee_id,sponsor_name,candidate_id,source`, one row per (cycle, committee) the adopted rule does not settle rightly, sorted by cycle and committee id. `candidate_id` may be any id fundlens holds a candidate for in some cycle. No row for a blank `Sponsor_Name`.

## 5. The checkpoint

When the document and the list are written and committed, `/implementit` **stops before writing §7** and puts these to the user, one `AskUserQuestion` at a time, each with the measured figures in the question:

1. Each decision line whose bar **failed**, with what the document found. A bar that was met is stated, not asked.
2. If `lobbyist.csv` is read: the per-cycle rule (Q7).
3. `leadership_pac`'s and `bundling_report`'s final columns, and how `amount` is placed on rows so that it sums to the greater-of total (this spec's starting point: a kept report adds its period amount, and the kept report carrying a half's figure also adds what that figure exceeds the half's period amounts by; a superseded report adds 0).
4. What happens to a bundling report with a blank coverage date, and to one whose recipient no cycle's `committee` holds.
5. Gold: where a sponsor link lives (gold `committee` and `candidate` are one row across cycles; a sponsor is per cycle), which flag a committee page shows when its designation changed between cycles, `committee_cycle.bundled_total`, and the leadership PAC's search entity.
6. The blank-sponsor finding, if Q5 put it over 10%.

The answers are recorded in §7 as decisions with their rejected alternatives, as NEU-2163's were.

## 6. Project spec §7, as it will be written

In §4 to §6's shape, every figure the measurement's, quoted with its question number:

- **Shared contracts**, as they stand, amended only where the checkpoint says so.
- **§7.1 Leadership PACs and lobbyist/registrant PACs:** each flag's source and what the files add.
- **§7.2 Silver `leadership_pac`:** key `(cycle, committee_id)`, columns, rows, checks.
- **§7.3 The sponsor:** the name rule, `leadership_sponsors.csv` and how a row is added, the in-cycle match, what a blank is.
- **§7.4 Silver `bundling_report`:** key, columns, the amendment rule, `amount`, checks (key unique; recipient in `committee`; `amount` sums to the half-year rule's total).
- **§7.5 The bundled total:** the rule, its figures per cycle, what it cannot show (no bundler, no donor).
- **§7.6 Gold:** the checkpoint's fields. No receipt total changes.
- **§7.7 What each cycle range has.**
- **§7.8 Dataset and older builds:** both tables join the dataset and `paths.BACKFILL_PENDING` in NEU-2175's PR; `bundling_report`'s README entry says its amounts are never to be added to `contribution` amounts.

## 7. The specs' other edits

- **Project spec §3.1:** the `leadership` note becomes what was measured (even years only, from 2010; which cycles' rows each undated file holds). If the bar moves `lobbyist.csv` out, its row moves to §3.2 with its reason, and the closing count of entries is corrected.
- **Project spec §8:** "M4's bundled contributions" becomes `bundling_report`.
- **v1 spec §9:** `leadership_pac` and `bundling_report` join the table list.
- **`CONTEXT.md`:** the five terms written at planning, adjusted only if the checkpoint changes a rule they state.

## 8. Linear text this spec supersedes

Corrected by `/implementit` after the checkpoint, in one pass, with the figures then known: NEU-2172 (bundled totals "matching `lobbyist_bundle.csv`" under the rule), NEU-2174 (two or three files; fixture rows as the files really are), NEU-2175 (`leadership_pac` and `bundling_report`; the sponsor matched by name and list; the amendment and half-year rules), NEU-2176 to NEU-2178 (no bundlers; the checkpoint's gold fields), NEU-2179 (Q13's ten and five). Each ticket's verified definition-of-done boxes are ticked; no status is changed.

## 9. Acceptance criteria

- [ ] `docs/measurements/leadership-lobbyist-2024.md` is merged: every figure dated, every query inline and runnable from the setup script, each file's URL and `Last-Modified` given, Q1–Q13 all present with results.
- [ ] Each of §3's six asserted facts is confirmed or corrected by the query it names.
- [ ] Each file's header, row grain, key and join rate to `committee` are stated, with the rows that join nothing.
- [ ] Both flag-source decision lines apply the 99% bar across 2010–2026.
- [ ] The name rule's match rate and its agreement with OpenFEC are given per rung and per cycle, and the adopted rung meets the 99% bar or the checkpoint decided otherwise.
- [ ] `src/fundlens/fec/leadership_sponsors.csv` is merged with a row for every (cycle, committee) 2010–2026 the rule does not settle, each with a `source`, and none for a blank sponsor.
- [ ] The bundled total is given per cycle under all three readings, with the halves where the half-year figure is below its periods' sum.
- [ ] The checkpoint was held before §7 was written, and §7 records each answer with its rejected alternative.
- [ ] Project spec §7 is merged with `leadership_pac`'s and `bundling_report`'s columns, the amendment and half-year rules and the gold fields; §3.1, §3.2, §8 and v1 §9 are edited as §7 above says; `CONTEXT.md` defines the five terms.
- [ ] NEU-2172 and NEU-2174 to NEU-2179 carry the corrected text.
- [ ] The work dir is removed on the VM; no bronze, silver, marker or gold object was written; no API key is in the PR.
- [ ] No change under `sql/`, `frontend/` or `tests/`, and none under `src/` but the one CSV.

## 10. Out of scope

- Cataloguing or extracting the files, fixtures, silver, gold, API and pages (NEU-2174 to NEU-2178), and the production run (NEU-2179).
- Named bundlers, and Form 3L's lobbyist rows: no bulk file has them (M5, NEU-2181).
- Lobbying Disclosure Act data.
- Naming a sponsor for a PAC the file names none for.
- Crediting any of a leadership PAC's money to its sponsor, or adding a bundled total to any receipt total (the milestone's contracts).
- A new ADR: none of these decisions is one a future reader could not find in §7.

## 11. Outcome (2026-11-25)

Measured 2026-11-25 (`docs/measurements/leadership-lobbyist-2024.md`, Q1–Q16) and checkpointed the same day. Project spec §7 holds every decision with its rejected alternative. Where the checkpoint departed from §1.1 above:

- **Blank sponsors are filled from the list.** OpenFEC names a sponsor for 73–86% of each cycle's blanks, the largest leadership PACs among them (Save America, Bluegrass, MC PAC), far over the 10% line (Q5f, Q12b).
- **The name rule takes one person only.** Rung 2's bar by id was met in 2024 alone, because OpenFEC gives current ids; read by person it holds (Q14). A name matching several ids goes to the list, since the in-race pick chose the wrong person (Q14b). `leadership_sponsors.csv` has 2,582 rows (Q16).
- **Leadership-PAC flag:** designation `D` or the file. The bar was missed in 2014, 2016 and 2026 by 4 to 11 committees (Q12c).
- **Lobbyist flag:** `lobbyist.csv`, latest Form 1 by the cycle's end. No rule met the bar against `B` (Q7f). It has its own silver table, `lobbyist_pac`, so `lobbyist.csv` stays in §3.1 and is catalogued.
- **Bundled total:** the greater of the half-year figure and the **innermost** reports' period amounts. Six-month reports nest beside their quarters, 9.16% of period dollars (Q9e). 2024: $57,262,231.
- **Gold:** every M4 field on `committee_cycle`, per cycle.
