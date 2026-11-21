# NEU-2151 — Catalogue and extract `oppexp` to bronze, with a fixture file

**Ticket:** [NEU-2151](https://linear.app/neuroticsasquatch/issue/NEU-2151) · **Milestone:** M2 Spending · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Parent:** NEU-2148
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §3 (file catalogue), §5 (spending: the rules the fixture's rows are for), read with the v1 spec §4 (the file table), §5.1 (extract), §5.3 (transform), §12 (testing) · **Glossary:** `CONTEXT.md` (File catalogue, Bronze, Operating expenditure, Sub-item, In-kind outlay, Repeated row, Superseded filing, Payee, Payee key) · **ADRs:** 0002 (bronze is the file as downloaded), 0012 (payees)
**Measurement:** `docs/measurements/oppexp-2024.md` (NEU-2149; "Q" numbers below are its).
**Blocked by:** NEU-2137 (merged). **Blocks:** NEU-2152 (silver `operating_expenditure`), which reads this ticket's catalogue entry and fixture rows.

Planned 2026-11-20. `/implementit NEU-2151` produces **one PR**: the catalogue entry and a `trailing_delimiter` field in `fec/files.py`, the vendored header, the fixture builder's support for the trailing `|`, the 2024 fixture file, tests, and two doc amendments. No silver model, no reader logic. Where the Linear ticket and this spec differ, this spec wins (§1.2).

## 1. What and why

`oppexp`, FEC's operating expenditures file (2004–), is not in the file catalogue, so it is neither downloaded nor read, and M2's silver table has nothing to read. This ticket catalogues it, so `extract` brings it into bronze and `transform` registers it as the view `oppexp`, and plants the fixture rows NEU-2152's rules are tested on.

### 1.1 Decisions this spec pins (grilled 2026-11-20)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| The trailing `\|` | **A `trailing_delimiter` field on `BulkFile`**, true for `oppexp` alone. The fixture builder writes the `\|`, the zip-layout test expects one field more than the columns with the last empty, and a unit test pins what the reader does with it. `register_bulk`'s `read_csv` call does not change. | Every `oppexp` line in every cycle has 26 fields: FEC's 25 and an empty one after a trailing `\|` (Q1, Q2a; §5 below). DuckDB 2.0.0 reads such a line under the 25 catalogued columns as written and refuses a non-empty 26th field (§5). That is DuckDB's behaviour, not ours, so the fixture must be FEC's layout and a test must hold the reader to it: a DuckDB upgrade that changed it would otherwise pass every test and stop the transform. Rejected: stripping the `\|` in `copy_bulk`, a per-line pass over 430 MB on the copy path every file shares; a 26th catalogued column, which breaks "the vendored header is the columns" and puts an empty column in the view and the repeated-row comparison; leaving it unmodelled. |
| What the fixture plants | **Every case project spec §5.1 and §5.2 name**, plus the payee and category rows §5.3 and §5.4 need a row for (§3). This ticket records only the file's row count in `expected.yaml`; NEU-2152 writes the expected spending and the tally. | The ticket's five cases predate the measurement and §5. NEU-2152's ticket says its expected values "carry the NEU-2151 fixture rows", and NEU-2142 planted NEU-2143's cases the same way. Rejected: the ticket's five only, or those plus the measurement's seven hand-off rows, either of which moves most of the fixture work into NEU-2152. |

Not user decisions, pinned so the diff is predictable:

- **Types.** Every column VARCHAR but four: `RPT_YR` `YEAR` (`SMALLINT`), `TRANSACTION_AMT` `AMOUNT`, `SUB_ID` `SUB_ID` (`UBIGINT`), `FILE_NUM` `FILE_NUM` (`BIGINT`). `TRANSACTION_DT` stays VARCHAR, as every file's dates do. No cell of any published cycle, 2004 to 2026, fails one of the four casts (§5).
- **Position.** `oppexp` is appended to `FecFile` and `CATALOGUE`, after `committee_summary`: catalogue order is the order `transform` registers files in, and no existing file moves.
- **No reader change.** `transform` already registers every file `files_for(cycle)` lists. `oppexp` has all four `TRANSACTION_KEY` columns, so `register_bulk` makes `oppexp_published`, `oppexp_repeat` and `oppexp` (repeated rows read once), and `register_unpublished` gives a cycle before 2004 the empty typed table and an empty `oppexp_repeat`. NEU-2152 relies on both.
- **`transform` reads `oppexp` from this merge on**, though no model reads the view until NEU-2152: the pattern NEU-2142 set for the summary files. What that means on the VM is §4.
- **No glossary or ADR change.** The trailing `|` is a file-format fact, not a domain term.

### 1.2 Where the ticket text is corrected

- "25 columns" is the header's count. Each line has 26 fields (the trailing `|`), which the ticket does not mention.
- "Amend v1 spec §2's file table": the table is in v1 **§4** (§2.5 below).
- The fixture's five cases become §3's list.
- `test_files.py` is `tests/unit/test_fec_files.py`.
- "`fundlens extract --cycle 2024` on the dev stack writes `oppexp` to bronze" is checked with `--file oppexp` (§2.6 step 4): a whole-cycle extract against fec.gov also downloads `indiv24.zip`, gigabytes this ticket does not change, and the whole-cycle path is covered by `tests/integration/test_extract.py` against the fake FEC server.
- "The fixture file loads in the transform's reader with no type errors" is the unit test of §2.4, on the fixture as FEC would serve it, trailing `|` included.

## 2. The deliverables, file by file

### 2.1 `src/fundlens/fec/files.py`

- `FecFile` gains `"oppexp"`, last.
- `BulkFile` gains `trailing_delimiter: bool = False`, documented as: each line ends with the delimiter after its last column, so it splits into one field more than `columns`, the last one empty. `__post_init__` raises `ValueError` for a CSV entry with it set ("a CSV has no trailing delimiter").
- The entry: `BulkFile("oppexp", 2004, "oppexp.txt", <columns>, trailing_delimiter=True)`. No `url_pattern` (the default gives `<yyyy>/oppexp<yy>.zip`, project spec §3.1), no `split_dir`, `header_from_fec` true. The member is `oppexp.txt` in every cycle's zip, the zip's only member (§5).
- Columns, in file order, written out in full, not built from `_ITEMIZED_HEAD` and `_ITEMIZED_TAIL`:

  `CMTE_ID`, `AMNDT_IND`, `RPT_YR` (`YEAR`), `RPT_TP`, `IMAGE_NUM`, `LINE_NUM`, `FORM_TP_CD`, `SCHED_TP_CD`, `NAME`, `CITY`, `STATE`, `ZIP_CODE`, `TRANSACTION_DT`, `TRANSACTION_AMT` (`AMOUNT`), `TRANSACTION_PGI`, `PURPOSE`, `CATEGORY`, `CATEGORY_DESC`, `MEMO_CD`, `MEMO_TEXT`, `ENTITY_TP`, `SUB_ID` (`SUB_ID`), `FILE_NUM` (`FILE_NUM`), `TRAN_ID`, `BACK_REF_TRAN_ID`.

- A comment on the entry says what differs from the itemized receipt files, so nobody reuses their layout: the column order (`ENTITY_TP` after the memo columns, `SUB_ID` before `FILE_NUM` and `TRAN_ID`, not last); no `TRANSACTION_TP`, `EMPLOYER`, `OCCUPATION` or `OTHER_ID`; `RPT_YR`, the form, schedule and line, `PURPOSE`, `CATEGORY` and `BACK_REF_TRAN_ID` in their place; dates written `MM/DD/YYYY`, not `MMDDYYYY`; and the trailing `|`. It cites project spec §3 and §5.
- The module docstring's `zip` bullet gains one sentence on `trailing_delimiter`. The comment above the type constants ("Dates stay VARCHAR: FEC writes them MMDDYYYY") is widened to say `oppexp` and the summary zips write `MM/DD/YYYY`.

### 2.2 `src/fundlens/fec/headers/oppexp_header_file.csv`

Written by `task fec:headers` once the entry exists (the refresh writes a header it has no vendored copy of). It must name the 25 columns of §2.1 in that order: FEC's file did on 2026-11-21 (`Last-Modified` 10 January 2018, the measurement's setup table). `task fec:headers -- --check` then exits 0. If FEC's header differs, stop and say so: the column list above is then wrong, and that is a finding, not something to paper over.

### 2.3 `src/fundlens/transform/runner.py`

No logic change. One comment at `register_bulk`'s zip dialect: a `trailing_delimiter` file's lines end in `|`; DuckDB reads the empty field after the last column as nothing and refuses a non-empty one, and `tests/unit/test_transform_trailing_delimiter.py` holds it to both.

### 2.4 Tests

- **`tests/fec_fixture.py`**: `pipe_text` ends each line with `|` when the entry's `trailing_delimiter` is set, so `bulk_text`, `body` and `bodies` give FEC's layout. The module docstring's zip bullet says so. `read_file` is unchanged: the fixture CSV has one value per column.
- **`tests/fixtures/fec/2024/oppexp.csv`**: §3. `expected.yaml` gains `rows.oppexp` and nothing else. The 1998 fixture cycle gets no file: `files_for(1998)` does not list `oppexp`.
- **`tests/unit/test_fec_files.py`**:
  - `("oppexp", 2004)` in the first-cycle parametrization, which asserts it is not in `files_for(2002)` and is in `files_for(2004)`.
  - `("oppexp", 2004, f"{BASE}/2004/oppexp04.zip")` in the URL parametrization and `("oppexp", 2024, "oppexp.txt")` in the member one.
  - `files_for(2004)` is `cm, cn, ccl, indiv, pas2, oth, weball, webk, oppexp`, in that order.
  - `oppexp` has 25 columns, the four typed ones typed as §1.1 says and the rest VARCHAR.
  - `trailing_delimiter` is true for `oppexp` and false for every other entry; a CSV entry with it set raises `ValueError`.
  - The existing header test covers `oppexp` through its parametrization over `FecFile`.
- **`tests/unit/test_fec_fixture.py`**:
  - `test_each_zip_holds_one_pipe_delimited_member_with_the_vendored_column_count` expects, for a `trailing_delimiter` entry, every line to end in `|` and split into one field more than the header with the last empty; for any other entry, as today (a line may still end in `|` there: its last column is empty, as a `cm` row with no `CAND_ID` is, and the field count already rules out a trailing delimiter).
  - `oppexp`'s `SUB_ID`s are unique and none is in `indiv`, `pas2` or `oth` (NEU-2152's `no_contribution` check needs that of the fixture).
  - `fec_repeats("oppexp")` is exactly §3's one planted repeat.
  - No row's `FILE_NUM` is the superseded filing's (`1900211`) but §3's one planted row.
- **`tests/unit/test_transform_trailing_delimiter.py`** (new; the ticket's third definition of done). On an in-memory DuckDB connection, as `test_transform_fec_repeats.py` does:
  - `register_bulk` on `fec_fixture.bulk_text("oppexp")` written to a file: `oppexp_published` has `rows.oppexp` rows, `oppexp` has one fewer (the repeat), and `oppexp_repeat` holds the repeat's `SUB_ID`.
  - Reading every column of every row raises nothing, and `typeof` gives `SMALLINT`, `DECIMAL(14,2)`, `UBIGINT` and `BIGINT` for the four typed columns.
  - The last column is not shifted: a named sub-item's `BACK_REF_TRAN_ID` is its parent's `TRAN_ID` as the fixture CSV has it, and a row with none reads NULL there.
  - A negative amount and an amount with cents read as filed.
  - A line whose 26th field is not empty makes the read raise.
  - A line with no trailing `|` reads the same as one with it (FEC has never served one; this records that the flag is about what FEC writes, and the reader accepts both).
- **`tests/integration/test_extract.py`**: `test_the_cli_rejects_a_file_the_catalogue_does_not_list` asks for `webl`, a file project spec §3.2 says fundlens never reads, in place of `oppexp`. A new test: `extract --cycle 2002 --file oppexp` exits 2 and requests nothing (FEC publishes none before 2004). The whole-cycle tests take `oppexp` in through `FILES` and `publish_all`.
- Nothing else should need a change: `put_bronze`, `seed`, `test_load`'s `source_dates` and the per-cycle `texts` dictionaries all read `files_for` or `FecFile`. If another test fails, fix the test's assumption, not the catalogue.

Run while iterating: `task test -- tests/unit/test_fec_files.py tests/unit/test_fec_fixture.py tests/unit/test_transform_trailing_delimiter.py tests/integration/test_extract.py`. The pre-commit hook runs the whole suite at the commit.

### 2.5 Docs, in the same PR

- **v1 spec §4**, the file table's `oppexp` row: "not loaded in v1 (operating expenditures)" becomes "not loaded in v1; read by *every FEC dollar* as `operating_expenditure` (that project's spec §3.1 and §5, catalogued by NEU-2151)". First cycle stays 2004.
- **Project spec §3.1**, a bullet under the table: every `oppexp` line ends with a trailing `|`, catalogued as `trailing_delimiter`; the zip's one member is `oppexp.txt` in every cycle; its dates are `MM/DD/YYYY`; every cycle 2004 to 2026 was read through `register_bulk` on 2026-11-21 with no cast failing (this spec's §5).

### 2.6 Order of work

1. The `BulkFile` field and the entry (§2.1), then `task fec:headers` (§2.2).
2. `pipe_text` and the fixture file (§2.4, §3), then the tests.
3. Docs (§2.5). `task format`.
4. Dev stack, against fec.gov: `task up` (which creates MinIO's buckets), then

   ```bash
   docker compose exec -T app fundlens extract --cycle 2024 --file oppexp
   docker compose exec -T app fundlens extract --cycle 2024 --file oppexp
   ```

   **Expected:** the first prints `oppexp: downloaded bronze/cycle=2024/oppexp/<today>.zip` (about 64 MB); the second prints `oppexp: unchanged` and downloads nothing. A `--file` run writes no marker.

## 3. The fixture file

`tests/fixtures/fec/2024/oppexp.csv`: a header row of §2.1's 25 names, `#` comment lines saying what each block plants, whether each row is counted under project spec §5.2 and by which rule, then the rows. About 40 rows. The opening comment states the three counting rules in a sentence each and says NEU-2152 records the expected sums.

Conventions:

- `SUB_ID`s run `4240400000000000001` upward in file order (`indiv` is `42401…`, `pas2` `42402…`, `oth` `42403…`).
- Payers are the fixture's committees in `cm.csv`. Form, schedule and line follow the filer: `F3`, `SB`, `17` for a House or Senate campaign; `F3P`, `SB`, `23` for a presidential one (`C00800101`, `C00703975`); `F3X`, `SB`, `21B` for a PAC or party.
- A sub-item and its parent share `CMTE_ID` and `FILE_NUM`. A committee's rows use `FILE_NUM`s of its own, never another committee's. Where a case must sit on a filing the `indiv` fixture already has (the superseded filing, the in-kind outlay), it uses that filing's number.
- Dates are `MM/DD/YYYY`. `RPT_YR` is 2023 or 2024, both present. `AMNDT_IND` has `N` and `A`. `CATEGORY_DESC` is filled where `CATEGORY` is.
- Mostly whole-dollar amounts, so NEU-2152's sums can be checked by hand; at least two rows carry cents.
- No value holds a `|`. A name with a comma is CSV-quoted, as in `indiv.csv`.

Cases. Each is at least the rows named; "counted" is what NEU-2152's `counted` must come to, stated in the block's comment.

| # | Plants | Rows and what makes the case | For |
|---|---|---|---|
| 1 | A plain payment | A campaign pays a firm; `ENTITY_TP` `ORG`, no memo code, no `BACK_REF_TRAN_ID`. Counted (rule 3) | §5.2 |
| 2 | A card bill fully itemized | A parent paying a card issuer, purpose `CREDIT CARD PAYMENT`, and two sub-items (`MEMO_CD` `X`, `BACK_REF_TRAN_ID` the parent's `TRAN_ID`) naming merchants and adding up to the parent. Parent counted (rule 2), sub-items not (rule 1) | §5.2; the ticket |
| 3 | A card bill that does not add up | As 2, the sub-items adding up to less than the parent by more than $1.00. Same counting: the parent, whatever its sub-items hold | §5.2 "parent always" |
| 4 | A memo parent | A parent whose own `MEMO_CD` is `X`, with one sub-item. Parent counted (rule 2, the exception to "memo rows are not counted") | §5.2 rule 2 |
| 5 | A chain | A top parent, a row that is its sub-item and itself a parent, and that row's sub-item. Only the top counts | §5.2 rule 1 |
| 6 | A memo row with no parent | `MEMO_CD` `X`, no `BACK_REF_TRAN_ID`, named by no row. Not counted (rule 3) | §5.2 rule 3 |
| 7 | An in-kind outlay, by structure | `BACK_REF_TRAN_ID` filled, no `oppexp` row on the filing with that `TRAN_ID`; it is the `TRAN_ID` of an `indiv` fixture row on the same committee and filing. No memo code, `MEMO_TEXT` `* IN-KIND RECEIVED`. Counted (rule 3); `is_in_kind` | §5.2 rule 3, §5.4 |
| 8 | An in-kind outlay, by purpose | An ordinary row, no `BACK_REF_TRAN_ID`, purpose `IN-KIND CONTRIBUTION`. Counted; `is_in_kind` | §5.4 |
| 9 | A row naming itself | `BACK_REF_TRAN_ID` equal to its own `TRAN_ID`, no memo code. No sub-item; counted (rule 3) | §5.1 `parent_source_record_id` |
| 10 | One `TRAN_ID` on two filings | A committee's two filings each hold a parent under the same `TRAN_ID` string and a sub-item naming it. Each sub-item's parent is the row on its own filing | §5.1 "same committee and filing" |
| 11 | One `TRAN_ID` twice on a filing | Two rows of one filing share a `TRAN_ID` and differ in amount (so neither is a repeated row), and a sub-item names it. Its parent is the lower `SUB_ID`; the other row is counted by rule 3 | §5.1 "the lower `SUB_ID`" |
| 12 | A repeated row | One payment on two rows, the same in every column but `SUB_ID`, `FILE_NUM` above 0, `TRAN_ID` filled. The reader drops the higher `SUB_ID`; the payment counts once | §5.1 rows; tested here |
| 13 | A superseded filing | MARYLAND FORWARD PAC (`C00800201`): one payment on its Q2 filing `1900211`, and the same payment under the same `TRAN_ID` on the amendment `1900212` that supersedes it in `indiv.csv` (NEU-2196). The `1900211` row is dropped; the `1900212` row counts | §5.1 rows |
| 14 | A filer `cm` lacks | One row whose `CMTE_ID` is in no `cm.csv` row. Dropped | §5.1 rows |
| 15 | A refund | A negative row from a payee the same committee paid in another row, purpose naming a refund. Counted, as filed: the two net | §5.2 sign; the ticket |
| 16 | A payment moved to Schedule E | A super PAC's (`C00800201` or `C00800205`) negative row, purpose `SEE SCHEDULE E`, against an earlier positive row to the same payee. Counted, as filed | §5.2 sign |
| 17 | A payee in two spellings | Two committees pay one firm under two spellings that `organization_key` gives one key (for example a trailing `LLC` against `, L.L.C.`). Run `normalize.organization_key` on both in the container and write the shared key in the comment | §5.4; the ticket |
| 18 | Two spellings the key does not join | A pair written with and without a space (the measurement's `AX MEDIA` and `AXMEDIA` shape), which stay two keys. The comment gives both keys and says this is exact grouping working as specified | §5.4, ADR-0012 |
| 19 | A conduit fee | A campaign pays `ACTBLUE` a fee per contribution processed, purpose naming processing fees. Counted; a payee by name, no link to `C00401224` | §5.4; the ticket |
| 20 | A row with no name | `NAME` empty. Counted; `payee_key` NULL | §5.1 `payee_key` |
| 21 | People as payees | One row `ENTITY_TP` `IND` (staff pay, `LAST, FIRST`); one `CAN` (the candidate reimbursed); one blank `ENTITY_TP` with a person's name; one blank with a firm's name. All counted. The comment records what `normalize.is_organization_name` says of the two blank rows' names, run in the container | §5.4 `payee_is_person` |
| 22 | A name that names nobody | `PETTY CASH`. Counted; for NEU-2155's no-page list | §5.4 |
| 23 | FEC's category code | A row with code `001` and a payroll purpose (a code not trusted); one with `004` and a purpose that says nothing (`SEE BELOW`), a trusted code; one written `1` and one written `01`, which are `001`; one with no code and the purpose `SEE MEMO` | §5.1 `fec_category`, §5.3 |
| 24 | Dates | One row dated `11/01/9201`, kept as filed; one with no date | §5.1 `date` |
| 25 | Who the spending is credited to | A principal campaign committee; an authorized one (`C00800113`); `C00800102`, designated D and named principal by its candidate's `cn` row; a leadership PAC credited to nobody (`C00800114`); a joint fundraising committee (`C00800115`); a party (`C00800203`). On `C00703975`, the committee handed from Biden to Harris: one row dated before 2024-07-21, one on or after it, and case 24's undated row | §5.1 `candidate_id`, §5.5 the handoff |

Rows may serve two cases where that keeps the file short (case 1's payment can be case 15's earlier payment; case 24's undated row is case 25's), and the comment then names both. Purposes are real ones from the measurement's Q8 list where a case does not fix the purpose, spread over at least five of §5.3's categories, so NEU-2153 and NEU-2154 have by-category totals to check.

Two questions the rows raise that are **NEU-2152's to answer**, not this ticket's: whether case 9's row, with `BACK_REF_TRAN_ID` filled and no parent, is an in-kind outlay under §5.4's wording; and how `04_contribution.sql`'s credit rule treats case 24's undated row on the handoff committee (project spec §5.5, asserted, not measured). The fixture plants both so the answers are tested.

## 4. At the merge

Nothing reads `oppexp` yet, and three things change on the VM:

- **The next weekly run** (`fundlens run`, cycle 2026) downloads `oppexp26.zip` (50,362,004 bytes on 2026-11-15) to `bronze/cycle=2026/oppexp/<date>.zip` and keeps it on local disk with the current cycle's other files. Its transform unpacks about 344 MB of text under `scratch/` and builds `oppexp_repeat` over 1.79M rows. On the dev stack the download, unpack and repeat scan of any one cycle took 4 to 26 seconds together (§5). **Asserted, not measured:** that this does not move the transform's memory peak, which is at "write contribution", long after the files are registered; NEU-2152's definition of done measures a 2024 transform.
- **A transform of a cycle from 2004 on whose bronze has no `oppexp`** stops with `FileNotFoundError: no oppexp file in bronze for <cycle>` before anything is written. That is every such cycle already extracted, 2024's live build among them, until its `oppexp` is extracted:

  ```bash
  docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --file oppexp
  ```

  NEU-2160's runbook runs this for 2024 before it transforms, as `reported-totals-run.md` did for the summary files. Anyone re-transforming an older cycle by hand sooner runs it first. A cycle's own full `extract` downloads it with the rest, so a backfill needs nothing extra.
- **`gold.meta.source_dates`** names `oppexp` for a cycle once its bronze has the file, and leaves it out before (`load/gold.py` `_source_dates`, NEU-2142). `/meta` types it `dict[str, date]`, and the methodology page reads the distinct dates only.

Merge outside the windows `docs/runbooks/weekly.md` gives (02:00 to 02:30 UTC daily; Sunday from 03:00 UTC to the run's end).

## 5. What FEC served, and what the reader did with it

Run on the dev stack's `app` container on 2026-11-21, shortly before 04:27 UTC, DuckDB 2.0.0, `main` at `1c95d3f`.

**The reader and a trailing `|`.** `register_bulk` on a `BulkFile` with §2.1's columns, one line per case:

| Line | Result |
|---|---|
| 25 fields then a trailing `\|`, `BACK_REF_TRAN_ID` empty | Read; `BACK_REF_TRAN_ID` NULL, no column shifted |
| The same with `BACK_REF_TRAN_ID` filled | Read; `BACK_REF_TRAN_ID` as written |
| 25 fields, no trailing `\|` | Read the same |
| A 26th field that is not empty | `InvalidInputException` (CSV error) |

**Every published cycle.** Each zip downloaded from `https://www.fec.gov/files/bulk-downloads/<yyyy>/oppexp<yy>.zip`, its member copied with `copy_bulk` and registered with `register_bulk` under §2.1's columns and types. "Cast failures" counts cells that are filled and fail `TRY_CAST` to their catalogued type, over `RPT_YR`, `TRANSACTION_AMT`, `SUB_ID` and `FILE_NUM`, and dates that are filled and not `MM/DD/YYYY`.

| Cycle | Zip bytes | `Last-Modified` | Members | Lines | Cast failures | `RPT_YR` | Read once | Repeated rows |
|---|---|---|---|---|---|---|---|---|
| 2004 | 25,734,364 | 31 Aug 2017 | `oppexp.txt` | 954,706 | 0 | 2003–2004 | 953,645 | 1,061 |
| 2006 | 30,217,068 | 31 Aug 2017 | `oppexp.txt` | 1,104,753 | 0 | 2005–2006 | 1,104,456 | 297 |
| 2008 | 43,785,331 | 31 Aug 2017 | `oppexp.txt` | 1,639,878 | 0 | 2007–2008 | 1,637,960 | 1,918 |
| 2010 | 37,478,492 | 20 Sep 2017 | `oppexp.txt` | 1,339,329 | 0 | 2009–2010 | 1,338,036 | 1,293 |
| 2012 | 45,382,905 | 20 Sep 2017 | `oppexp.txt` | 1,656,089 | 0 | 2011–2012 | 1,654,328 | 1,761 |
| 2014 | 38,894,605 | 30 Dec 2018 | `oppexp.txt` | 1,351,071 | 0 | 2013–2014 | 1,351,066 | 5 |
| 2016 | 51,856,704 | 16 Oct 2022 | `oppexp.txt` | 1,744,187 | 0 | 2015–2016 | 1,743,435 | 752 |
| 2018 | 52,731,735 | 1 Jan 2023 | `oppexp.txt` | 1,800,080 | 0 | 2017–2018 | 1,799,908 | 172 |
| 2020 | 64,556,004 | 29 Dec 2024 | `oppexp.txt` | 2,310,524 | 0 | 2019–2020 | 2,309,716 | 808 |
| 2022 | 56,164,549 | 15 Nov 2026 | `oppexp.txt` | 1,962,279 | 0 | 2021–2022 | 1,944,035 | 18,244 |
| 2024 | 64,105,756 | 15 Nov 2026 | `oppexp.txt` | 2,249,911 | 0 | 2023–2024 | 2,246,968 | 2,943 |
| 2026 | 50,362,004 | 15 Nov 2026 | `oppexp.txt` | 1,790,165 | 0 | 2025–2026 | 1,790,165 | 0 |

No `SUB_ID` or `RPT_YR` is empty in any cycle. The zips are the ones the measurement profiled (the same bytes and dates as its Q2a), and the rows read once and the repeated rows equal its Q2a figures in every cycle, so `register_bulk`'s repeated-row rule is the one the measurement spelled inline.

## 6. Acceptance criteria

- [ ] `tests/unit/test_fec_files.py` asserts `oppexp`'s first cycle (2004), its 25 columns and four types, its URL and member, that `files_for(2002)` excludes it, and that it alone has `trailing_delimiter`.
- [ ] `task fec:headers -- --check` exits 0 with `oppexp_header_file.csv` vendored.
- [ ] `tests/unit/test_transform_trailing_delimiter.py` passes: the fixture file, served with its trailing `|`, reads through `register_bulk` with no cast error, the repeat dropped, the last column unshifted, and a non-empty 26th field refused.
- [ ] The fixture file holds every case of §3, each under a comment naming its case and whether it counts, and `expected.yaml`'s `rows.oppexp` is its row count.
- [ ] `fundlens extract --cycle 2024 --file oppexp` on the dev stack writes `bronze/cycle=2024/oppexp/<date>.zip`; a second run prints `unchanged` and downloads nothing.
- [ ] `extract --cycle 2002 --file oppexp` exits 2, and `--file webl` exits 2.
- [ ] v1 spec §4's row and project spec §3.1's bullet are amended (§2.5).
- [ ] The pre-commit hook's full suite passes, and no new test is near the top of its slowest-tests list.

## 7. Out of scope

- Silver `operating_expenditure`, its checks, `expected.yaml`'s spending figures and the fixture tally (NEU-2152).
- The dataset, `BACKFILL_PENDING`, `columns.yaml` (NEU-2152, project spec §5.8).
- Extracting `oppexp` on the VM for any cycle (NEU-2160's runbook for 2024; NEU-2180's backfill for the rest).
- Any change to `copy_bulk`, `copy_as_utf8` or `register_bulk`'s `read_csv` call.
- `docs/capacity.md`: bronze grows by about 0.56 GB over all twelve cycles, recorded when a run measures it.
