# NEU-2162 — Measure 2024 outside spending: `pas2` against the 24/48-hour file, non-committee spenders, electioneering communications, communication costs, amendments

**Ticket:** [NEU-2162](https://linear.app/neuroticsasquatch/issue/NEU-2162) · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Milestone:** M3 All outside spending · **Parent story:** NEU-2161
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §6 is a stub (its **Shared contracts**, filled by NEU-2163 from this measurement); §3.1 lists the three CSVs (first cycle 2010, catalogued by NEU-2164); §4.1 is `reported_total.independent_expenditures` and `party_coordinated`. v1 spec §4 (`independent_expenditure`, NEU-2057), §7.1 (`ie_support`, `ie_oppose`, `ie_total`) · **ADRs:** 0002 (R2 is the store of record)
**Blocks:** NEU-2163 (spec §6, glossary), and through it NEU-2165, NEU-2166 and NEU-2167 (silver). **Related:** NEU-2057 (the shipped `pas2` model, `sql/silver/09_independent_expenditure.sql`), NEU-2279 (`docs/measurements/ie-candidate-names-2024.md`, the first reading of the 24/48-hour file), NEU-2164 (catalogue and extract), NEU-2171 (the production run, which checks gold against this document's five races), NEU-2140 and NEU-2149 (the measurements whose shape and setup this one reuses).

Planned 2026-11-23. `/implementit NEU-2162` produces **one PR**: `docs/measurements/outside-spending-2024.md`, written from a run over SSH on `music-box-dancer` (§4), plus any Bug ticket §1.1 allows. No change to `sql/`, `src/` or `frontend/`.

**The run must happen before 3 December 2026** (§4.2 Q7): the 2026 timeliness window closes when post-general reports arrive.

## 1. What and why

Milestone M3 shows every kind of outside spending on a race. Four sources describe it and they overlap: `pas2` (committees' 24A/24E independent expenditures, 24C party coordinated expenditures, 24F/24N communication costs), `independent_expenditure_YYYY.csv` (the **24/48-hour file**), `ElectioneeringComm_YYYY.csv` and `CommunicationCosts_YYYY.csv`. How they overlap decides every counting rule NEU-2163 writes into spec §6, and nobody has measured it. A double count would put the same super PAC ad on a race page twice.

Three of the ticket's premises are already known to be off, from the code and from files read on 2026-11-23 (§3):

1. **Form 5 filers are in `cm` and in `pas2`.** `cm` types them `I` (204 with reported figures in 2024, `docs/measurements/summary-files-2024.md`). `09_independent_expenditure.sql` drops a row whose filer `cm` lacks and records "none in 2024", and NEU-2279 matched counted `pas2` rows to the `F57` lines of 251 Form 5 filings. So the milestone's "spenders not in `cm`" may be nearly empty, and the story's claim that non-committee spenders "appear only in the 24/48-hour file" is unproven.
2. **The two files share `TRAN_ID`, not amounts.** NEU-2279 found the 24/48-hour file holds the same transactions under the same `TRAN_ID` on a different filing, with the 24-hour report's estimated amounts, and a candidate id that differs from `pas2`'s on 2,713 rows ($284,808,027). The ticket's match "by filer, candidate, date and amount" would miss those.
3. **The electioneering file has no amendment column.** It carries `SB_IMAGE_NUM` and no `FILE_NUM`, `TRAN_ID` or amendment indicator, so "duplicates after amendment" cannot be read off a column.

This ticket measures the overlaps on 2024, takes one live reading of 2026 for timeliness, profiles every cycle FEC publishes the CSVs for, and writes the figures, the queries and the decisions into one document. It changes nothing in the pipeline.

### 1.1 Decisions this spec pins (grilled 2026-11-23)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Non-committee spender | **A spender `cm` types `I` (a Form 5 filer) or `cm` lacks.** Every spender figure is split three ways: `committee`, `type I`, `absent` (§2). | Absent from `cm` only, the contract's wording: if that group is near-empty the document says nothing about Form 5 filers, the story's point. By the filing's form, read from raw `.fec` files: about 1 GB of filings for a split `cm` already gives. |
| Match rule | **A ladder, `TRAN_ID` first** (Q5). Rung 1: same spender and `TRAN_ID`. Rung 2: same spender, candidate, date and amount. Rung 3: same spender, candidate and amount, dates within 7 days. Dollars at each rung; amount and candidate disagreement inside rung 1. "Only in 24/48-hour" is what no rung matches. | `TRAN_ID` only: a filer renumbering between its 24-hour and periodic reports inflates both "only in" figures. The ticket's key only: misses every corrected estimate and recoded candidate id. |
| What the 24/48-hour file adds | **By spender, with a bar.** A spender with no counted `pas2` independent expenditure in the cycle has all its latest-amendment 24/48-hour rows added; a spender with any gets none. Adopted if the unmatched 24/48-hour rows at spenders that are in `pas2` hold **under 1% of 2024's counted independent expenditure dollars**; otherwise the document says what those rows are and NEU-2163 decides. Both grains' dollars are printed either way. | By row: an estimate that was renumbered and corrected counts twice. No bar: the choice gets made after seeing which answer looks better. |
| Timeliness | **Live on 2026, plus 2024 by date** (Q7). The contract allows "pre-period-report timeliness" only if this ticket shows no double count, and 2024 cannot show it. | 2024 only: no live evidence of the gap. Not measured: the current cycle's race pages would lag the last three weeks before every election, undecided. |
| Timeliness bar (this spec's, not grilled) | A timeliness rule is stated only if, on 2026, the 24/48-hour rows dated after their spender's `reported_total.period_end` that **already match a `pas2` row hold under 1% of those rows' dollars**. Otherwise the document says timeliness is out. | No bar: "no double count" would be read off the result. |
| Cycles | **2024 in full; one structural profile per cycle 2010–2026** (Q12). Every rule, match and figure is 2024's. | 2024 only, as the ticket says: its electioneering file is 69 rows and its communication-costs file 779, about a ninth and an eighth of 2010's by size, and a break in an earlier cycle would stay unseen until NEU-2180's backfill. 2024 and 2010 in full: doubles the document where 2010 adds little. |
| Where the queries run | **Prod's `pipeline` container** on `music-box-dancer`, over SSH, as scripts reusing `fundlens.transform.runner` and the live builds' silver. Read-only. | The dev stack, as NEU-2279 ran: candidate and race attachment, aliases, the handoff and the 96 corrections would be re-derived outside silver, so the five races' figures might not be what gold later shows. |
| The files | The three CSVs for each cycle, and 2026's `pas2`, are **downloaded into the work dir** with their `Last-Modified` recorded, **not catalogued, not in bronze**. | Cataloguing them here: that is NEU-2164, which needs this document's reader notes first. |
| Amendments in the 24/48-hour file | **By filing chain** (Q3): a filing is superseded when a later filing names it in `prev_file_num`, followed transitively, and every row on a superseded filing is dropped. Adopted unless amendments are partial: if amendments carrying fewer than half of their original's transaction ids hold **over 1% of the dollars on amended filings**, the per-transaction rule (the row on the highest `file_num` per spender and `tran_id`) is adopted instead. Both are measured. | Per transaction as the default: a transaction the amendment removed stays counted. No default. |
| Electioneering amendments | **A file key, checked against Form 9s** (Q9). Rows repeating on sponsor, payee, disbursement date, amount and candidate under different image numbers are amendment candidates; every 2024 sponsor's raw Form 9 filings say which are restatements and which are two payments. 2010–2026 get the file-key count only. | File key only: two identical ad buys on a day read as an amendment. Form 9s for every cycle: several hundred rows in 2010 alone, some on paper. |
| Too few repeats in 2024 (this spec's, not grilled) | If 2024 holds fewer than 5 repeat groups, the Form 9s behind the 20 largest repeat groups of the profiled cycle with the most are read as well, so the rule rests on evidence. | Stating a dedup rule from nothing. |
| Communication costs | **`pas2` if the CSV adds no rows** (Q8). If at least 99% of the CSV's rows and dollars are `pas2` 24F/24N rows by `SUB_ID` with equal amounts, in 2024 and in every profiled cycle, the source is `pas2`, the CSV supplying communication type, class and purpose by `SUB_ID`. Otherwise the CSV is the source and the `pas2` rows are marked not counted. | The CSV always: a second table for the same rows, and cycles before 2010 have `pas2` rows and no CSV. No bar. |
| The five races | **The five 2024 regular Senate races with the most independent expenditure dollars in live gold** (`race.ie_support + race.ie_oppose`, `is_special` false). If the five do not between them hold every kind and a non-committee spender, the lowest is swapped for the largest race that supplies the missing one, and the document says so. | As they fall: the five may hold no electioneering communication, leaving NEU-2171 and NEU-2161's Done line without a checked race for the kind. Hand-picked: not re-runnable. |
| Defects found in v1 | **A Bug ticket for a live defect only.** A cause that makes a figure on fundlens.org wrong today gets one Bug ticket in the v1 project (P-NEU-105), labelled `Bug` and `repo:fundlens`, related to NEU-2162, assigned to the user, in the three-heading format, and named in the document beside its dollars. Anything about data not yet built is input to NEU-2163. The document states cause and dollars and diagnoses no further. | No tickets, as NEU-2149: a live double count would wait for someone to read the document. Asking per finding. |
| The `pas2` side | **Silver's rows.** "In `pas2`" means the live build's `independent_expenditure` rows: memo lines dropped, aliases, the handoff and `fec/ie_candidate_corrections.csv` applied. A 24/48-hour row matching only a `pas2` memo line is its own bucket, never "only in 24/48-hour". | Re-deriving the counted-row filter in the measurement: it would drift from silver. |
| Samples | **Whole population by SQL; samples picked by a stated rule and shown** (the 10 largest and 10 by `hash` order). | Deciding from a sample: NEU-2140 set the pattern. |
| Glossary and ADR | **None here.** NEU-2163 owns `CONTEXT.md`'s Outside spending, Electioneering communication, Communication cost and Party coordinated expenditure, and writes "non-committee spender" from this document's numbers. | Adding the term now: the measurement may show its "absent from `cm`" half is empty. |

## 2. Definitions used in the document

- **24/48-hour file:** `independent_expenditure_<yyyy>.csv`. **Spender:** who made an independent expenditure (`spe_id`; `CMTE_ID` in `pas2`). **Sponsor:** who paid for an electioneering communication (`COMMITTEE_ID`). **Filer:** who reported a communication cost (`CMTE_ID`). Never "outside money", "IE spend" or "super PAC money" (`CONTEXT.md`).
- **Spender group**, from the cycle's `cm`: `committee` (in `cm`, `CMTE_TP` not `I`), `type I` (in `cm`, `CMTE_TP = 'I'`), `absent` (not in `cm`). A **non-committee spender** is `type I` or `absent`. Sponsors and filers are grouped the same way, and each table also shows the id's first two characters (`C0`, `C3`, `C7`, `C9`).
- **Counted `pas2` row:** a row of the live build's silver `independent_expenditure` with `kind = 'ie'`. **Memo line:** a `pas2` 24A/24E row with `MEMO_CD = 'X'`, read from bronze.
- **Amount:** `TRY_CAST(… AS DECIMAL(14,2))` inside each query, so a cell that fails is counted, not a read error. **Dates:** the 24/48-hour and electioneering files write `DD-MON-YY`, the communication-costs file `YYYYMMDD` and `pas2` `MMDDYYYY`; each parsed with `try_strptime`, failures counted.
- **Candidate, for matching:** the id each file gives, resolved through silver `candidate.alias_of`, before the handoff and before any correction. **Candidate, for a figure:** as `09_independent_expenditure.sql` attaches it, the handoff by date included.
- **Latest-amendment rows:** the 24/48-hour rows Q3's adopted rule keeps.
- **Ladder** (Q5), applied to latest-amendment 24/48-hour rows against counted `pas2` rows of 2024. Rung 1 matches at the grain of (spender, `TRAN_ID`), each side summed, since either file may hold an id on several rows. Rungs 2 and 3 match what is left one row to one row, in `SUB_ID` and `file_num` order within a key. Rung 2 is tried on `exp_date` and then on `dissem_dt`, reported apart.
- **Repeat group** (electioneering): rows equal on `COMMITTEE_ID`, `PAYEE_NAME`, `DISBURSEMENT_DATE`, `REPORTED_DISBURSEMENT_AMOUNT` and `CANDIDATE_ID` with different `SB_IMAGE_NUM`.
- **Repeated row** and **superseded filing:** `CONTEXT.md`'s terms, v1's definitions.

## 3. Preconditions

- Bronze `cm` and `pas2` for every even cycle 2010–2026 in R2 (the backfill of 2026-11-17, `docs/runbooks/backfill.md` Log), and the live builds' silver `committee`, `candidate`, `independent_expenditure` and `reported_total` for 2024 and 2026. The document records each cycle's `build_id` and each file's download date.
- No pipeline step running (the Sunday 03:00 UTC scheduled run, or a runbook in progress), and **no merge to `main` while the run is in progress**: a merge recreates the stack and kills the `docker exec` (`docs/runbooks/weekly.md`, Facts).
- Free disk under `/data/fundlens/scratch` for one cycle's unpacked `pas2` at a time and the CSVs (under 300 MB for all nine cycles).

Read on 2026-11-23, from HTTP headers, each 2024 file's header row and, for the two small files, the whole file:

| | |
|---|---|
| `independent_expenditure_2024.csv` | 19,534,174 bytes, `Last-Modified` 2026-11-23. 23 columns, **lower case**: `cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt`. Its first data row has a blank `exp_date` and a spender name with a leading space |
| `ElectioneeringComm_2024.csv` | 18,370 bytes, 70 lines. 19 columns: `CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE`. 24 lines have a blank `CANDIDATE_ID`. Sponsor ids begin `C3`. Three Senate candidates are named: two in Ohio, one in Wisconsin |
| `CommunicationCosts_2024.csv` | 237,322 bytes, 780 lines. 25 columns: `CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE`. Every filer id begins `C7`; `TRANSACTION_TP` is 24F or 24N; `IMAGE_NUM` is a URL |
| Other cycles, bytes (24/48-hour, electioneering, communication costs) | 2010: 11.4M, 161K, 1.82M · 2012: 27.0M, 76K, 1.72M · 2016: 42.4M, 28K, 761K · 2020: 21.4M, 71K, 308K · 2022: 16.6M, 12K, 1.28M · 2026: 13.7M, 13K, 49K. 2014 and 2018 not looked at |
| Each URL | `https://www.fec.gov/files/bulk-downloads/<yyyy>/<name>_<yyyy>.csv`, which answers 302 to an S3 address: the fetch must follow redirects |

The ticket's `SPE_ID`, `TRA_ID` and `PREV_FILE_NUM` are `spe_id`, `tran_id` and `prev_file_num`. Project spec §3 says a CSV's header row must equal its catalogue entry's `columns` exactly; Q1 records each header as served, for NEU-2164.

**Asserted, not measured**, each checked by the query named:

- That the 24/48-hour file's `tran_id` is the `TRAN_ID` of the same expenditure in `pas2` generally, not only in NEU-2279's example (Q5).
- That `prev_file_num` names the filing an amendment replaces, and that an amendment restates its whole report (Q3).
- That `pas2` holds an independent expenditure once, from the periodic report, and not also from its 24- or 48-hour report (Q4).
- That `SUB_ID` is the same for one communication cost in `pas2` and in the CSV (Q8).
- That 2026's pre-general reports closed on 14 October and its post-general reports are due on 3 December (20 days before and 30 days after the 3 November election). FEC's calendar was not read; Q7 reads the files' own dates.
- That `https://docquery.fec.gov/cgi-bin/forms/<sponsor id>/` lists a sponsor's Form 9 filings, each readable at `dcdev/posted/<FILE_NUM>.fec` as NEU-2279 read Form 3X and Form 5 (Q9). If not, the document says what it used.

## 4. The run

Over SSH on the VM, in `tmux`, using the `fl` helper from `docs/runbooks/first-run.md`. The setup script and each block are files in `~/measure-outside-spending-2024` on the VM, copied there with `scp`, never pasted (a long paste into `tmux` mangles). The document carries every block verbatim with its output, in the shape of `docs/measurements/oppexp-2024.md`, with its `run.sh` and `all.sh`.

### 4.1 Setup script

One Python file, kept at the top of the document and prepended to each block. It is `oppexp-2024.md`'s setup with these changes; the helpers are named as they stand at `54fe259` (read them again at the run's SHA):

- `work = scratch / "measure-outside-spending-2024"`.
- `fetch(path)`: one FEC file into `work` with the project's `USER_AGENT`, following the redirect, its URL, `Last-Modified`, size and download time printed; skipped when already there.
- `view_csv(name, path)`: the file rewritten by `copy_as_utf8`, then a view of VARCHAR columns over `read_csv(…, header = true, all_varchar = true, quote = '"')`, named by the header row as served. It prints the header and the count of lines whose field count differs from it.
- `bulk(name, cycle)`: the cycle's bronze file through `fetch_bulk` and `register_bulk`, as the transform sees it (`pas2` with repeated rows dropped, `pas2_published` with them kept), registered as `<name>_<cycle>` so two cycles can be open at once.
- `silver(table, cycle)`: the live build's partition of `table` for the cycle as the view `silver_<cycle>.<table>`, the build id read from `gold.meta` on a read-only connection.
- `show(title, sql)`: a timed Markdown table.
- For 2026 only, `pas226.zip` is fetched from FEC into `work` in the same hour as the 2026 CSV and read through `register_bulk`, so the two are of one date. Bronze's copy may be a week older.

Query shape: `connect` turns DuckDB's build-side optimizer off (NEU-2076), so every join puts the smaller table on the right. The matched and unmatched sets are materialized once as Parquet in `work` and reused. `work` is deleted at the end of the run and the document says so.

### 4.2 Queries and figures

Each is one or more SQL blocks, dated, each followed by its result and one or two sentences of reading. Dollar figures are split by spender group wherever a spender is involved.

**Q1 — Shape of the three CSVs (2024).** Per file: bytes, lines, the header as served, fields per line, quoting dialect against project spec §3's (every data field double-quoted, LF, no BOM), embedded newlines. Rows; cells whose amount or date fails its cast, and each date column's format. Keys: whether (`spe_id`, `file_num`, `tran_id`) is unique in the 24/48-hour file, `SUB_ID` in the communication-costs file, and whether the electioneering file holds any fully identical rows. Dollars in all. `amndt_ind`, `sup_opp`, `ele_type`, `TRANSACTION_TP`, `COMMUNICATION_TP`, `COMMUNICATION_CLASS` and `NUMBER_OF_CANDIDATES` by value. Blank `exp_date` and `dissem_dt`, and how `exp_amo` relates to `agg_amo`.

**Q2 — Who the spenders are (2024).** The 24/48-hour file's spenders by group and id prefix: spenders, rows, dollars. Every `absent` spender listed by name with its rows and dollars. The same split for counted `pas2` rows. Then the two files against each other by spender: in both, only in the 24/48-hour file, only in `pas2`, per group. For each `type I` filer, its counted `pas2` dollars against its `reported_total.independent_expenditures`: the distribution of the ratio, and the filers more than 1% apart. This is the test of whether `pas2` is the complete record for Form 5 filers as it is for committees.

**Q3 — Amendments in the 24/48-hour file (2024).** `amndt_ind` by value; `prev_file_num` fill; filings named by another's `prev_file_num`, and chain depth. (`spe_id`, `tran_id`) pairs on more than one `file_num`, split by whether amount, candidate and date agree. For each amendment, the share of its original's transaction ids it carries: the distribution, and the dollars on amendments carrying under half. Rows and dollars each rule keeps and drops: the filing chain, and per transaction. Transactions the chain rule drops and the per-transaction rule keeps (an amendment deleted them), and the reverse, each with 20 rows shown. The **decision line**: §1.1's bar applied, the rule adopted, the dollars it keeps and drops.

**Q4 — `pas2`'s own independent expenditures (2024).** Counted rows by `RPT_TP`, `AMNDT_IND` and spender group. Whether any counted row is from a 24- or 48-hour report: a (`CMTE_ID`, `TRAN_ID`) on more than one `FILE_NUM` among counted rows, by the `RPT_TP`s involved, rows and dollars. If `pas2` counts an expenditure from both its 24-hour report and its periodic report, that is a live defect in v1's totals: the document states the dollars and files the Bug ticket (§1.1).

**Q5 — The ladder (2024).** Per rung and spender group: rows and dollars on each side. Inside rung 1: amounts equal or not, with the distribution of `pas2 ÷ 24/48-hour` and the net dollars the estimates were off by; candidate equal after aliases or not; `sup_opp` against silver's `support_oppose`; date equal, `dissem_dt` equal, or neither. The memo-line bucket. Then the two residuals, **only in 24/48-hour** and **only in `pas2`**: by spender group, by month, by `RPT_TP` on the `pas2` side, the 20 largest spenders on each side, and 20 rows of each shown. Unmatched 24/48-hour rows at spenders that have a counted `pas2` row, as dollars and as a share of counted independent expenditure dollars. The **decision line**: §1.1's 1% bar applied, the add rule adopted or handed to NEU-2163, and the dollars each grain would add.

**Q6 — What the rule adds (2024).** Under the adopted rule: spenders, rows and dollars added, by group and by `sup_opp`; the 20 largest spenders added. Their candidate ids: blank, not in `cn`, not a candidate of the cycle, alias-resolved. Rows and dollars that reach a candidate and a race of the cycle, and those that reach the spender's total alone. This is the figure NEU-2165's definition of done is within 1% of.

**Q7 — Timeliness.** *2026, live.* Each file's `Last-Modified`. The latest transaction date in 2026's `pas2` among 24A/24E rows, by `RPT_TP`. Per spender, the 2026 live build's `reported_total.period_end`. Latest-amendment 24/48-hour rows dated after their spender's `period_end`: rows, dollars, by group and by week; how many already match a `pas2` row by the ladder. Rows dated on or before it: the share the ladder matches. The **decision line**: §1.1's timeliness bar applied; if met, the rule stated (a spender's latest-amendment 24/48-hour rows dated after its `period_end` are added until a periodic report covers them) with the dollars it adds on 2026 today. *2024, by date.* The same rule applied to 2024 as it stands now: what it would add (expected: next to nothing, every report being filed), and what those rows are. `committee_summary`'s date against `pas2`'s is stated beside both.

**Q8 — Communication costs (2024).** The CSV against `pas2_published`'s 24F/24N rows by `SUB_ID`: in both with equal amounts, in both with different amounts, only in the CSV, only in `pas2`; rows and dollars each, the unmatched listed. The same by (`CMTE_ID`, `FILE_NUM`, `TRAN_ID`) for what `SUB_ID` left. `pas2` memo lines among them, which silver drops. Filers by group and `cm` type. `SUPPORT_OPPOSE_IND` against 24F and 24N. `COMMUNICATION_TP` and `COMMUNICATION_CLASS` by value with dollars. Each filer's sum against Form 7's reported communication cost if a file read here carries one, else said to be unchecked. The **decision line**: §1.1's 99% bar applied with Q12's cycles, the single source named, and the dollars it counts.

**Q9 — Electioneering communications (2024).** Rows, disbursements, dollars, sponsors by group and `cm` type. Blank `CANDIDATE_ID`: rows and dollars, by sponsor, and what the description says the ad was. Named candidates: in `cn`, a candidate of the cycle, with a race. The split: whether `CALCULATED_CANDIDATE_SHARE × NUMBER_OF_CANDIDATES` equals `REPORTED_DISBURSEMENT_AMOUNT` within a cent, and whether each disbursement has as many rows as `NUMBER_OF_CANDIDATES`; the multi-candidate share of rows and dollars. Repeat groups (§2): count, rows, dollars. Then every 2024 sponsor's Form 9 filings fetched, and each repeat group marked a restatement by an amendment or two payments, with the filing numbers; §1.1's fallback if 2024 has fewer than 5 groups. The **decision line**: the dedup rule the Form 9s support, the rows and dollars it keeps and drops, and the counted total NEU-2166's definition of done is within 1% of.

**Q10 — Party coordinated expenditures (2024).** Silver's `kind = 'coordinated'` rows: rows and dollars by party committee and by candidate, the 20 largest of each. Any 24C from a filer that is not a party committee (`cm` type X or Y). Memo lines dropped. Each committee's sum against its `reported_total.party_coordinated`. The figure NEU-2167's definition of done is within 1% of.

**Q11 — Across kinds (2024).** Whether one payment is in two kinds: electioneering rows against 24/48-hour and `pas2` rows, and communication-cost rows against 24/48-hour rows, by spender id, and by payee, date and amount. Spender ids that appear in more than one kind. The **decision line**: no rule needed, or the overlap by key with its dollars.

**Q12 — Every cycle's profile (2010–2026).** For each cycle, its three CSVs fetched, profiled and deleted, with its bronze `cm` and `pas2`. One table per measure, a cycle per row: bytes and `Last-Modified`; header equal to 2024's or not; rows and dollars per file; 24/48-hour spenders by group; `amndt_ind` mix and the chain rule's kept and dropped dollars; rung 1's match rate against raw `pas2` 24A/24E; electioneering sponsors, blank candidates, multi-candidate share and repeat groups; the communication-costs `SUB_ID` overlap as Q8's four buckets; `pas2`'s 24C and 24F/24N rows and dollars. A closing paragraph names each cycle where a figure leaves 2024's by enough that a 2024 rule cannot apply as written, for NEU-2163 and for NEU-2180's backfill.

**Q13 — Five Senate races (2024).** The pick by §1.1's rule, with the ranking it came from and any swap. For each race, per candidate: independent expenditures for and against as live gold has them; what Q5's rule adds, for and against; electioneering communications (the candidate's shares under Q9's rule; no side); communication costs for and against under Q8's source; party coordinated expenditures. Each race's non-committee spenders and electioneering sponsors named. These are the figures NEU-2171 compares gold against.

### 4.3 The document

`docs/measurements/outside-spending-2024.md`, in this order:

1. Header table: run times, `main` SHA, container, DuckDB version and `Limits`, the 2024 and 2026 live builds and their source dates, each file's URL, `Last-Modified`, size and download time, the Form 9 filings read.
2. **Headline**: the source and dedup rule for each of the four kinds, each with the dollars it keeps and drops; what the 24/48-hour file adds; the timeliness verdict; any Bug ticket filed.
3. **How to re-run** and the setup script.
4. Q1–Q13.
5. **Decisions**: (1) non-committee spenders: who they are and where their spending is; (2) the 24/48-hour amendment rule; (3) the match and the add rule; (4) timeliness; (5) the communication-costs source; (6) the electioneering dedup rule, blank candidates and the split; (7) party coordinated expenditures; (8) cross-kind overlap; (9) cycles where a 2024 rule does not apply. Each states its source, its rule and its dollars, and which of the milestone's contracts it confirms or asks NEU-2163 to amend.
6. **For NEU-2163 to NEU-2171**: what each takes. NEU-2163: the nine decisions. NEU-2164: each header as served, the redirect, date formats, cells that fail a cast, the fixture rows worth having. NEU-2165, NEU-2166, NEU-2167: the 2024 figure each definition of done is within 1% of. NEU-2171: Q13.

No `capacity.md` row: this is a measurement, not a pipeline step. No change to `CONTEXT.md` or `docs/adr/`.

## 5. Acceptance criteria

- [ ] `docs/measurements/outside-spending-2024.md` is merged; every figure is dated, every query is inline and runnable from the setup script, and each file's URL and `Last-Modified` are given.
- [ ] Q1–Q13 are all present with results; nothing is marked "to do". Each of §3's six asserted facts is confirmed or corrected by the query it names.
- [ ] For each kind (independent expenditure, electioneering communication, communication cost, party coordinated) the document states its source and dedup rule with the dollars the rule keeps and drops.
- [ ] Every spender figure is split by `committee`, `type I` and `absent`, and every `absent` spender is listed.
- [ ] The ladder's dollars are given per rung, with both residuals, and §1.1's 1% bar is applied in a decision line.
- [ ] The 24/48-hour amendment rule is stated with the dollars under both candidate rules and §1.1's partial-amendment bar applied.
- [ ] Q7 was run on 2026's files before 3 December 2026 and states the timeliness verdict with §1.1's bar applied.
- [ ] The communication-costs source is named with §1.1's 99% bar applied across 2010–2026.
- [ ] Each electioneering repeat group checked is marked from its Form 9 filings, and blank-candidate rows are counted.
- [ ] Q12 has a row for every cycle 2010–2026 in every table, and names the cycles where a 2024 rule does not apply.
- [ ] Q13 records the five races' per-candidate figures by kind, with the rule that picked them.
- [ ] Any live defect found has a Bug ticket in P-NEU-105 named in the document; none is filed for data not yet built.
- [ ] `/data/fundlens/scratch/measure-outside-spending-2024` is removed; no bronze, silver, marker or gold object was written.
- [ ] No change under `sql/`, `src/` or `frontend/` in the PR.

## 6. Out of scope

- Any change to `sql/`, `src/`, `frontend/`, `CONTEXT.md` or `docs/adr/`, and the edits to spec §6 and the milestone's contracts the Decisions call for (NEU-2163).
- Cataloguing the three CSVs or reading them in the pipeline (NEU-2164 to NEU-2167).
- The silver columns and gold fields (NEU-2163), and how a blank-candidate electioneering communication is shown: measured here, decided there.
- Fixing a defect found in v1's figures: the Bug ticket does that.
- The candidate a `pas2` row names (NEU-2279 measured it; its corrections stand).
- The donors behind non-committee spenders and electioneering sponsors (Form 5 and Form 9 schedules; M5, NEU-2181).
- Deep measurement of any cycle but 2024: Q12 is one profile row per cycle, and Q7 reads 2026 for timeliness alone.
