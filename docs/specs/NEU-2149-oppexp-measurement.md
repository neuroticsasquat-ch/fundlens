# NEU-2149 — Measure FEC's 2024 `oppexp`: structure, counting rules, categories, payees

**Ticket:** [NEU-2149](https://linear.app/neuroticsasquatch/issue/NEU-2149) · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Milestone:** M2 Spending · **Parent story:** NEU-2148
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §5 is a stub (its **Shared contracts**, filled by NEU-2150 from this measurement); §3.1 lists `oppexp` (zip, first cycle 2004, catalogued by NEU-2151); §4.1 is `reported_total.operating_expenditures`. v1 spec §4 (memo lines, the refund rule of NEU-2073) · **ADRs:** 0002 (R2 is the store of record), 0011 (organizations are grouped, not resolved)
**Blocks:** NEU-2150 (spec §5, glossary, ADR 0012), and through it NEU-2152 (silver `operating_expenditure`). **Related:** NEU-2151 (catalogue and extract), NEU-2153 (the classifier, whose test set this ticket writes), NEU-2160 (the production run), NEU-2129 and NEU-2140 (the measurements whose shape and setup this one reuses).

Planned 2026-11-20. `/implementit NEU-2149` produces **one PR**: `docs/measurements/oppexp-2024.md`, written from a run over SSH on `music-box-dancer` (§4), and `tests/fixtures/spending/purpose_labels_2024.csv`. No change to `sql/`, `src/` or `frontend/`.

## 1. What and why

Milestone M2 shows where committees' money goes. Its silver table, its counting rules and its classifier (NEU-2150, NEU-2152, NEU-2153) rest on facts about FEC's operating expenditures file that nobody has measured:

1. **Sub-itemization.** A credit-card bill or a staff reimbursement is filed as one payment with the real payees itemized under it, linked by `BACK_REF_TRAN_ID`. Which side is a memo line, how often the children add up to the parent, and what a paper filing (no `TRAN_ID`) does instead, are unknown. The milestone's contract says one side counts, "as NEU-2149's measurement decides".
2. **Amendments and repeats.** v1 found two things in the itemized receipt files: repeated rows (NEU-2401) and superseded filings (NEU-2196). Whether `oppexp` has either is unknown.
3. **Overlap.** Whether a row of `oppexp` is also in `pas2`, `oth` or `indiv`, where fundlens already counts it as something else.
4. **Categories.** How often FEC's `CATEGORY` is filled, whether the milestone's 11 categories cover what filers write in `PURPOSE`, and a labelled test set for the classifier.
5. **Payees.** How raw payee names group under the organization normalizer, and what the conduits' fees and the refunds look like.
6. **Size.** What the table adds to the 2024 transform, which already peaks at 26.48 GiB under a 32 GB DuckDB limit (`docs/capacity.md`, 2026-11-16).

This ticket measures all six on 2024, profiles every cycle FEC publishes the file for, and writes the figures, the queries and the decisions into one document. It changes nothing in the pipeline.

### 1.1 Decisions this spec pins (grilled 2026-11-20)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Cycles | **2024 in full; one structural profile for every cycle 2004–2026** (Q2). Every rule, sample, payee and label is 2024's. | 2024 only, as the ticket says: Senate campaigns filed on paper until 2018 and FEC's description dates paper rows from October 2005, so a rule fitted to 2024 can stop holding in a cycle nobody looked at until the backfill (NEU-2180). 2004 and 2016 only: twelve zips total about 0.5 GB, and a break in 2008 would stay unseen. |
| Sub-itemization rule | **Children where they add up.** A parent whose children sum to its amount within $1.00 is not counted and its children are, whatever their memo code; any other parent counts and its children do not. Adopted if such fully itemized parents hold **at least half of the dollars of parents with children**; below that the rule is parent always. The document states the rule adopted with the dollars on each side. | Parent always: the card issuer becomes the payee and the real payee is under-credited by every memo child, on the pages the story exists for (NEU-2148). Parents in totals and children on payee pages: NEU-2150's one `counted` column becomes two, and a payee's dollars stop adding up to committees' totals. |
| What the rule does to the contract | The milestone's "`MEMO_CD = 'X'` rows are not counted" gains one exception if the rule is adopted: a memo child standing in for its parent. **NEU-2150 writes it** into spec §5 and the milestone; this document states it. | Reading the contract as forbidding the rule: the same contract says the measurement decides parent or children, and the children are the memo side. |
| Category list | **The 11 may be amended by a bar.** Purposes are labelled against the 11 first. A coherent group forced into `other` that holds **2% or more of the labelled set's dollars** becomes a category. The document states the final list, each category's one-sentence definition and the FEC `CATEGORY` codes mapped to it; the CSV is labelled in the final list. NEU-2150 writes the list into spec §5 and the milestone. | Keeping the 11 and reporting gaps: if NEU-2150 then changes the list, the test set is stale before NEU-2153 reads it. Keeping the 11 unreviewed: FEC's own codes include polling and campaign materials, which have no home in it. |
| Labelling | **Claude labels all 200 during `/implementit`; the user reviews in the PR.** Each row is marked `clear` or `judgement`, and a judgement row carries a one-line reason. The category definitions and tie-breaks are written in the document before any row is labelled. | Settling each judgement call live: 20 to 40 questions for labels a diff shows as well. The user labelling: the definitions would then live in one head. |
| Reconciliation | **Every 2024 committee's counted sum against `reported_total.operating_expenditures`, distribution only** (Q11): under each candidate rule, by committee group, with the count and dollars over 1% and the 20 largest excesses listed undiagnosed. **No Bug tickets.** | Leaving it to NEU-2160's ten committees: it is the only test of the counting rules against a figure fundlens did not compute. Diagnosing every excess, as NEU-2140 did: nothing is built yet, so an excess is input to NEU-2150's rules, not a bug. |
| Where the queries run | **Prod's `pipeline` container** on `music-box-dancer`, over SSH, as `docker exec -i … python - <<'PY'` scripts reusing `fundlens.transform.runner` and `fundlens.resolve.normalize`. | The dev stack: no 2024 bronze or silver, and the memory figure must be taken under prod's limits. |
| The file | `oppexp<yy>.zip` for each cycle is **downloaded into the work dir** with its `Last-Modified` recorded, **not catalogued, not in bronze**. | Cataloguing it here: that is NEU-2151, which needs this document's reader notes first. |
| Samples | **Whole population by SQL; samples picked by a stated rule and shown.** The ticket's "100 sampled parents" are the 100 the document prints (Q3), not the basis of the decision. | Deciding from 100 rows: NEU-2140 set the pattern, and the SQL covers every parent at no extra cost. |
| Payee key | **`organization_key(NAME)`**, the function ADR-0011's organizations use (`normalize_employer`, falling back to the cleaned name). | `normalize_employer` alone: it returns NULL for names it reads as no employer, and a payment must keep a key. |
| Glossary and ADR | **None here.** NEU-2150 owns `CONTEXT.md`'s Operating expenditure, Payee, Payee key and Spending category, and ADR 0012. This spec says "payee" and "spending", never "vendor" or "spend". | Adding terms before the numbers are in. |

## 2. Definitions used in the document

- **Amount:** `TRY_CAST(TRANSACTION_AMT AS DECIMAL(14,2))`, cast inside each query so a cell that fails is counted, not a read error. Dates likewise (`try_strptime(TRANSACTION_DT, '%m/%d/%Y')`, else `'%m%d%Y'`; the document says which the file uses).
- **Memo row:** `MEMO_CD = 'X'`.
- **Electronic row:** `FILE_NUM > 0` and `TRAN_ID` filled. **Paper row:** `TRAN_ID` blank. The two-by-two of `FILE_NUM` and `TRAN_ID` is reported, so a row that is neither is visible.
- **Child:** a row with `BACK_REF_TRAN_ID` filled. **Parent:** a row whose `(CMTE_ID, FILE_NUM, TRAN_ID)` some child names by its `(CMTE_ID, FILE_NUM, BACK_REF_TRAN_ID)`. **Orphan child:** a child whose parent is not in the file.
- **Fully itemized parent:** `abs(sum(children's amounts) − parent's amount) <= 1.00`.
- **Parent kind:** `card` (the payee name or the purpose names a card or its issuer: the document carries the regular expression), `reimbursement` (`ENTITY_TP = 'IND'` or the purpose names a reimbursement), `other`.
- **Counting rules compared.** R1: non-memo rows (FEC's own rule). R2: §1.1's sub-itemization rule; a row that is neither a parent nor a child of a parent in the file counts when it is not a memo row. R3: R2 less rows on a superseded filing (Q6). R4: R3 less overlap rows (Q7). "Counted" in Q8 to Q10 means the rule Q3 adopts, with Q6's and Q7's exclusions.
- **Filer group** from `cm.CMTE_TP`: `candidate` (H, S, P), `party` (X, Y), `super PAC` (O, U), `other`, `not in cm`; as NEU-2129's recipient groups.
- **Purpose:** `PURPOSE` upper-cased, trimmed, runs of whitespace made one space. Grouping and the CSV use this form.
- **Payee key:** `organization_key(NAME)`. **Spelling:** a distinct raw `NAME` under one key.
- **Repeated row** and **superseded filing:** `CONTEXT.md`'s terms, measured by v1's definitions (`_drop_fec_repeats` in `transform/runner.py`; `superseded_filing` in `sql/silver/04_contribution.sql`).

## 3. Preconditions

- Bronze 2024 `cm`, `pas2`, `oth` and `indiv` in R2, and the live build's silver `committee`, `reported_total`, `committee_transfer` and `independent_expenditure`. The document records `gold.meta.build_id` and each file's download date.
- No pipeline step running (the Sunday 03:00 UTC scheduled run, or a runbook in progress), and **no merge to `main` while the run is in progress**: a merge recreates the stack and kills the `docker exec` (`docs/runbooks/weekly.md`, Facts).
- Free disk under `/data/fundlens/scratch` for 2024's unpacked `indiv` (about 5 GB) and one cycle's `oppexp` at a time.
- FEC's `data_dictionaries/oppexp_header_file.csv` still names the 25 columns it did on 2026-11-20: `CMTE_ID, AMNDT_IND, RPT_YR, RPT_TP, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, NAME, CITY, STATE, ZIP_CODE, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_PGI, PURPOSE, CATEGORY, CATEGORY_DESC, MEMO_CD, MEMO_TEXT, ENTITY_TP, SUB_ID, FILE_NUM, TRAN_ID, BACK_REF_TRAN_ID`. The run fetches it again and records any difference.

Known on 2026-11-20, from HTTP headers and FEC's file description only; no file's contents were read for this spec:

| | |
|---|---|
| `oppexp24.zip` | 64,105,756 bytes, `Last-Modified` 2026-11-15 |
| `oppexp16.zip`, `oppexp04.zip` | 51,856,704 and 25,734,364 bytes |
| What FEC says the file holds | Disbursements "including" Form 3 line 17, Form 3P line 23 and Form 3X lines 21(a)(i), 21(a)(ii) and 21(b); electronic filers from the 2004 cycle, paper filers from October 2005; `CATEGORY` codes 001–012 and 101–107 |

**Asserted, not measured**, each checked by Q1 before anything else is read: that the zip holds one text member; that each row has 25 fields (a trailing `|` making 26 has been reported of this file); that a sub-item's parent is on the same filing; that `SUB_ID` is the same for one transaction in `oppexp` and in `pas2` or `oth`.

## 4. The run

Over SSH on the VM, in `tmux`, using the `fl` helper from `docs/runbooks/first-run.md`. The document carries every block verbatim with its output, in the shape of `docs/measurements/summary-files-2024.md`: header table, **Headline**, **How to re-run**, the setup, Q1–Q11, **Decisions**, **For NEU-2150 to NEU-2153 and NEU-2160**.

### 4.1 Setup script

One Python heredoc, kept at the top of the document and pasted before each query block. Its shape, with the helpers as they stand at `89635a5` (read them again at the run's SHA: `unzip_bulk` became `fetch_bulk` since NEU-2140):

```python
import datetime as dt
import resource
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg

from fundlens import paths
from fundlens.fec.extract import USER_AGENT
from fundlens.fec.files import CATALOGUE
from fundlens.load.gold import _require_inputs
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.settings import get_settings
from fundlens.transform.runner import Limits, connect, copy_as_utf8, fetch_bulk, literal, register_bulk

settings = get_settings()
store = R2.from_settings(settings)
scratch = paths.scratch_dir(settings.data_dir)
work = scratch / "measure-oppexp-2024"
work.mkdir(parents=True, exist_ok=True)
con = connect(Limits.from_settings(settings), scratch)
normalize.register(con)  # organization_key, as silver calls it

# 2024 bronze as the transform sees it: pas2, oth and indiv with repeated rows dropped,
# and <file>_published with them kept.
for name in ("cm", "pas2", "oth", "indiv"):
    register_bulk(con, CATALOGUE[name], fetch_bulk(store, 2024, CATALOGUE[name], data_dir=settings.data_dir, work=work))

# The live build's silver tables this measurement reads, as views silver.<table>.
with psycopg.connect(settings.database_url) as pg:
    BUILD = pg.execute("SELECT build_id FROM gold.meta").fetchone()[0]
parts = _require_inputs(store, 2024, BUILD, data_dir=settings.data_dir)
con.execute("CREATE SCHEMA silver")
for table in ("committee", "reported_total", "committee_transfer", "independent_expenditure"):
    con.execute(f"CREATE VIEW silver.{table} AS SELECT * FROM read_parquet("
                f"{literal(parts[table] / '**' / '*.parquet')}, hive_partitioning = false)")
```

and three helpers, written out in the document:

- `fetch(path)`: one FEC file into `work` with the project's `USER_AGENT`, its URL, `Last-Modified`, size and download time printed; skipped when already there (as NEU-2140's).
- `view_oppexp(name, zip_path)`: the zip's text member rewritten by `copy_as_utf8` (the transform's own repair), then a view of VARCHAR columns over `read_csv(…, delim = '|', quote = '', escape = '', header = false, auto_detect = false)`, named by the fetched header plus `extra_<n>` for any field beyond the 25 that Q1 finds.
- `show(title, sql)`: a timed Markdown table, as in the two earlier measurements.

Query shape: `connect` turns DuckDB's build-side optimizer off (NEU-2076), so every join puts the smaller table on the right. `oppexp` is the small side against `indiv`. Per-parent and per-committee aggregates are materialized once and reused. `work` is deleted at the end of the run and the document says so.

### 4.2 Queries and figures

Each is one or more SQL blocks, dated, each followed by its result and one or two sentences of reading.

**Q1 — Size, shape and memory (2024).** Before any view: the zip's members, the text's bytes, lines, and the distribution of fields per line (the asserted 25). Then rows; cells whose amount, date, `SUB_ID` or `FILE_NUM` fails its cast; `SUB_ID` uniqueness; lines `copy_as_utf8` had to re-decode. Dollars: all rows, and R1. Rows and dollars by `FORM_TP_CD` × `SCHED_TP_CD` × `LINE_NUM`, with the memo share of each: which forms, schedules and lines the file really holds beside the five lines FEC names (a Schedule H4 row carries a shared payment, and the document says what its amount is). By `ENTITY_TP`, by `AMNDT_IND`, by `RPT_YR`, by filer group. Parquet size: the typed rows written with the transform's `COPY … (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 999424)`. Memory, each in a fresh process whose `resource.getrusage(RUSAGE_SELF).ru_maxrss` is printed at exit: (a) one full-scan aggregate; (b) `CREATE TABLE` of the typed rows with `organization_key` evaluated once per distinct name and joined back, and the child-to-parent join, which is the shape NEU-2152 builds, with `PRAGMA database_size` after it. The transform holds every silver table in memory until it is written, so (b)'s table size is what `operating_expenditure` adds to the 2024 peak; the document states it as NEU-2152's budget beside the 26.48 GiB and the 32 GB limit.

**Q2 — Every cycle's profile (2004–2026).** For each cycle, its zip fetched, profiled and deleted: bytes and `Last-Modified`; rows; dollars and R1 dollars; memo share of rows and of dollars; paper rows' share of rows and of dollars; the share with `BACK_REF_TRAN_ID`; fully itemized parents' share of parents' dollars; fill rate of `CATEGORY`, `ENTITY_TP` and `PURPOSE` by rows and by dollars; the form and schedule mix; the earliest and latest parsed date and the count unparseable; fields per line. One table per measure, a cycle per row. A closing paragraph names each cycle where a figure leaves 2024's by enough that a 2024 rule cannot apply as written (a paper share that leaves most sub-items unlinked; `CATEGORY` or `ENTITY_TP` empty), for NEU-2150 to write the pre-rule behaviour and for NEU-2180's backfill.

**Q3 — Sub-itemization (2024).** Children: rows, dollars, memo share, and orphans. Parents: rows, dollars, memo share, by parent kind and filer group. The two-by-two of parent memo code against child memo code, rows and dollars each: the cell where neither is a memo row is money R1 counts twice, and the document says what those rows are. Chains deeper than one level: count, and how the rule reads them. For every parent, children's sum against its amount: the share fully itemized by parents and by dollars, and the distribution of `children ÷ parent` for the rest. Then **100 parents printed with their children**, 50 `card` and 50 `reimbursement`: in each kind the 25 largest by amount and 25 by `hash(SUB_ID)` order, so the pick is re-runnable. Then the **decision line**: §1.1's bar applied, the rule adopted, and the dollars on each side: counted at children, counted at parents, card issuers' dollars that stay with the issuer, and children's dollars that reach no payee because their parent is not fully itemized.

**Q4 — Paper filings (2024).** Paper rows' share of rows and dollars, by filer group and form. How a paper filing shows a sub-item with no `TRAN_ID` to link it: memo rows by `MEMO_TEXT` pattern, and 20 printed in `IMAGE_NUM` order with the rows around them. The rule for a paper row, stated: it counts when it is not a memo row, and its sub-items are never promoted.

**Q5 — Repeated rows (2024).** What `register_bulk` will drop once the file is catalogued, since `oppexp` has all four `TRANSACTION_KEY` columns: rows beyond the first that share `CMTE_ID`, `FILE_NUM` and `TRAN_ID` and every column but `SUB_ID`; rows and dollars, by committee and filing for the ten largest. `TRAN_ID`s whose rows differ, which are all read. Whether the rule is right for this file is stated: a repeated payment row is one payment as a repeated gift row is one gift, or it is not, with the evidence.

**Q6 — Amendments (2024).** (a) `TRAN_ID`s under more than one `FILE_NUM` at one committee, split by whether payee, amount and date agree: a filer's ids restarting each report are not an amendment. (b) v1's rule applied to payments: a payment is the hash of committee, name key, ZIP5, amount, date and purpose on a dated non-memo electronic row; a filing is superseded when a later-numbered amendment (`AMNDT_IND = 'A'`) at the same committee repeats at least half of its payments. Filings, rows and dollars. (c) The `indiv`-derived `superseded_filing` set, from the three statements of `04_contribution.sql` copied verbatim at the run's SHA and quoted: the `oppexp` rows and dollars on those filings. (d) The two sets against each other: in both, only in (b), only in (c). The **decision line**: the amendment rule, one of *the receipt side's set alone*, *the union*, or *none needed*, with the dollars on each side. A filing is one report, so the default is that a filing superseded for receipts is superseded for spending; (b) adds a filing only if the document shows filings with spending and too few gifts for (c) to see. Q11 cannot decide this: FEC's own summary adds a superseded filing to its amendment (NEU-2196).

**Q7 — Overlap with `pas2`, `oth` and `indiv` (2024).** By `SUB_ID` against each file's `_published` view: rows and dollars, by `oppexp`'s form and line and by the other file's `TRANSACTION_TP`. By `(CMTE_ID, FILE_NUM, TRAN_ID)` with the same amount, for rows `SUB_ID` did not match, in case the files number rows apart. Against silver `committee_transfer` and `independent_expenditure` by `source_record_id`, which is what NEU-2152's `no_contribution` check reads. `indiv` is this spec's addition: a refunded contribution is a Schedule B row too, and silver already nets it from receipts (NEU-2073). The **decision line**: the overlap rule, stated by key and, where the overlap is whole lines, by line, with the dollars dropped and the dollars kept.

**Q8 — `CATEGORY` and purposes (2024).** Fill rate of `CATEGORY` by rows and by counted dollars: overall, by filer group, by form, by `RPT_YR`. Every code with its `CATEGORY_DESC` as the file gives it, rows and dollars. Purposes: distinct count, blank share, and the share of counted dollars held by the top 50, 100, 200, 500 and 1,000, so NEU-2153 knows what a 200-row set stands for. **The top 200 purposes by counted dollars**, each with rows, dollars, the dollars on rows with `CATEGORY` blank, and its most common `CATEGORY` code where one is filled. The definitions and tie-breaks, then the labels (§4.3). Dollars per category, the 2% bar applied, the final list. Where a purpose has both a label and FEC codes: label against code, dollars agreeing and disagreeing per code, which is the check on the contract's "FEC's `CATEGORY` when filled". The FEC code to category map, every code placed.

**Q9 — Payees (2024).** Keys: distinct count, spellings per key, the share of counted dollars held by the top 100 and top 1,000. **The top 100 keys by counted dollars**: dollars, rows, committees paying, states, spellings, and up to ten spellings each by dollars; each read by eye for two payees under one key, and marked. Names `normalize_employer` returns NULL for, which take the cleaned-name fallback: rows, dollars, the top 20. Keys that name no payee (a card, cash, payroll, "various", "see memo"): the list found and its dollars, as a stoplist candidate. Payees that are people: rows and dollars by `ENTITY_TP`, and `IND` keys spanning more than one state as a count and dollars, a floor on how many people one key merges. Measured, not decided: whether a person gets a payee page is NEU-2150's.

**Q10 — Conduit fees and refunds (2024).** The keys of the committees in `fec/conduits.csv` (ActBlue, WinRed) as payees: rows, dollars, memo share, top purposes, `CATEGORY` codes, committees paying, and whether they are parents or children. Negative amounts: rows and dollars by form and line, top 30 purposes. Positive rows whose purpose names a refund, void or reissue: the same. The **sign rule** stated for the contract's "refunds and offsets net out": amounts summed as filed, or not, with the dollars a different rule would move.

**Q11 — Against FEC's reported operating expenditures (2024).** For every committee with a silver `reported_total.operating_expenditures`: the counted sum under R1, R2, R3 and R4, and under each restricted to the lines FEC names. Per rule: the distribution of `counted ÷ reported` by decile and filer group; committees and dollars over by more than 1%; committees with a reported 0 or blank beside counted money; committees with a reported figure and no `oppexp` row. The 20 largest excesses under the adopted rule with their form, schedule and line mix, undiagnosed. Itemized spending sits below the reported figure by design (payments under $200 are unitemized), so the reading is which rule puts the fewest dollars above it. The `oppexp` zip's date against the build's `committee_summary` date is stated beside the result.

### 4.3 The labelled test set

`tests/fixtures/spending/purpose_labels_2024.csv`, 200 rows plus a header, ordered by dollars:

| Column | Holds |
|---|---|
| `purpose` | §2's purpose |
| `rows`, `dollars` | counted rows and dollars in 2024 |
| `dollars_category_blank` | the dollars on rows with `CATEGORY` blank, which are what the purpose rule must classify |
| `fec_category` | the most common filled `CATEGORY` code on the purpose's rows, else empty |
| `spending_category` | the label, one of the final list's slugs |
| `confidence` | `clear` or `judgement` |
| `reason` | empty for `clear`; one line for `judgement`, naming the tie-break used |

Slugs are lower-case with underscores: `media`, `digital`, `fundraising`, `payroll`, `consulting`, `travel`, `events`, `administrative`, `legal_compliance`, `transfers_fees`, `other`, plus any category the 2% bar adds. Nothing reads the file until NEU-2153.

### 4.4 The document

`docs/measurements/oppexp-2024.md`, in this order:

1. Header table: run times, `main` SHA, container, DuckDB version and `Limits`, the live build and its source dates, each `oppexp` zip's URL, `Last-Modified`, size and download time, the header file's fetch.
2. **Headline**: the rule adopted for sub-items, amendments, overlap and sign, each with its dollars; the `CATEGORY` fill rate; the final category list; what the top 100 payees hold; the table's size against the transform's budget.
3. **How to re-run** and the setup script.
4. Q1–Q11.
5. **Decisions**: (1) the sub-itemization rule and the contract exception it needs; (2) the amendment rule; (3) the overlap rule; (4) the sign rule; (5) the category list, definitions and FEC code map; (6) payee key findings: wrong merges seen, stoplist candidates, people; (7) the memory budget; (8) cycles where a 2024 rule does not apply.
6. **For NEU-2150, NEU-2151, NEU-2152, NEU-2153 and NEU-2160**: what each takes. NEU-2151: fields per line, the member's name, cells that fail a cast, the fixture rows worth having. NEU-2152: the counted row count and dollars its definition of done is within 1% of, and the budget. NEU-2153: the test set, the share of dollars it stands for, and where FEC's codes disagree with the labels. NEU-2160: Q11's figures, to compare gold against.

No `capacity.md` row: this is a measurement, not a pipeline step. No change to `CONTEXT.md` or `docs/adr/`.

## 5. Acceptance criteria

- [ ] `docs/measurements/oppexp-2024.md` is merged; every figure is dated, every query is inline and runnable from the setup script, and each zip's URL and `Last-Modified` are given.
- [ ] Q1–Q11 are all present with results; nothing is marked "to do". Each of §3's four asserted facts is confirmed or corrected in Q1, Q3 or Q7.
- [ ] The sub-itemization rule is stated with §1.1's bar applied and the dollars counted at children and at parents; the 100 parents are printed.
- [ ] The amendment rule is stated with the dollars on superseded filings by each of Q6's two sets, and the repeated-row figure of Q5.
- [ ] The overlap rule is stated with the dollars in `pas2`, `oth` and `indiv` and the dollars kept.
- [ ] Q2 has a row for every cycle 2004–2026 in every table, and names the cycles where a 2024 rule does not apply.
- [ ] The final category list is stated with a definition per category and every FEC `CATEGORY` code mapped; `tests/fixtures/spending/purpose_labels_2024.csv` has 200 labelled rows in that list, each `clear` or `judgement` with a reason on the latter.
- [ ] The top 100 payee keys are listed with their spellings, and the stoplist candidates and person-payee figures are given.
- [ ] The memory budget for NEU-2152 is stated from Q1's measured table size.
- [ ] Q11's distribution is given under each rule, with no Bug ticket filed from it.
- [ ] `/data/fundlens/scratch/measure-oppexp-2024` is removed; no bronze, silver, marker or gold object was written.
- [ ] No change under `sql/`, `src/` or `frontend/` in the PR.

## 6. Out of scope

- Any change to `sql/`, `src/`, `frontend/`, `CONTEXT.md` or `docs/adr/`, and the edits to spec §5 and the milestone's contracts that Decisions 1 and 5 call for (NEU-2150).
- Cataloguing `oppexp` or reading it in the pipeline (NEU-2151, NEU-2152).
- The classifier's rules (NEU-2153): this ticket labels, it does not classify.
- Diagnosing the committees Q11 puts above FEC's figure, and any Bug ticket from them (NEU-2160, on gold).
- Whether a person gets a payee page, and the gold payee tables (NEU-2150).
- Deep measurement of any cycle but 2024: Q2 is one profile row per cycle.
