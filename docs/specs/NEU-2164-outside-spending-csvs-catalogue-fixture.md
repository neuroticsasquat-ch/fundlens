# NEU-2164 — Catalogue and extract the three outside-spending CSVs, with fixtures

**Ticket:** [NEU-2164](https://linear.app/neuroticsasquatch/issue/NEU-2164) · **Milestone:** M3 All outside spending · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Parent:** NEU-2161
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §3 (file catalogue), §6 (outside spending: the rules the fixture's rows are for), read with the v1 spec §5.1 (extract), §5.3 (transform), §12 (testing) · **Glossary:** `CONTEXT.md` (File catalogue, Bronze, 24/48-hour file, Hoax filing, Spender, Non-committee spender, Electioneering communication, Communication cost, Repeated row, Handoff) · **ADRs:** 0002 (bronze is the file as downloaded)
**Measurement:** `docs/measurements/outside-spending-2024.md` (NEU-2162; "Q" numbers below are its).
**Blocked by:** NEU-2137, NEU-2138 (both merged). **Blocks:** NEU-2165, NEU-2166, NEU-2167, which read this ticket's catalogue entries and fixture rows.

Planned 2026-11-24. `/implementit NEU-2164` produces **one PR**: three catalogue entries in `fec/files.py`, three fixture files, the supporting rows they need in four existing fixture files with every expected value those move, tests, and the doc amendments of §2.4. No silver model, no reader change, no extract change. Where the Linear ticket and this spec differ, this spec wins (§1.2).

## 1. What and why

FEC's three outside-spending CSVs are not in the file catalogue, so they are neither downloaded nor read, and M3's silver models have nothing to read. This ticket catalogues them on NEU-2138's CSV support, so `extract` brings them into bronze and `transform` registers each as a view, and it plants the fixture rows that NEU-2165, NEU-2166 and NEU-2167 test project spec §6's rules on.

| Catalogue name | FEC's file | Glossary |
|---|---|---|
| `ie_24_48` | `<yyyy>/independent_expenditure_<yyyy>.csv` | the 24/48-hour file |
| `ElectioneeringComm` | `<yyyy>/ElectioneeringComm_<yyyy>.csv` | electioneering communications |
| `CommunicationCosts` | `<yyyy>/CommunicationCosts_<yyyy>.csv` | communication costs |

### 1.1 Decisions this spec pins (grilled 2026-11-24)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| The 24/48-hour file's catalogue name | **`ie_24_48`**, one name everywhere: the entry, its DuckDB view, its bronze folder (`bronze/cycle=2024/ie_24_48/<date>.csv`), `--file`, its `gold.meta.source_dates` key, and the `source_file` value project spec §6.2 gives its rows. Its `url_pattern` still writes FEC's name. | `register_bulk` names a file's view for its entry, and `09_independent_expenditure.sql` runs `CREATE TABLE independent_expenditure`. DuckDB 2.0.0 refuses the second (`View with name "independent_expenditure" already exists!`, tried 2026-11-24), so the name project spec §3.1 gave it would stop every transform of every cycle at model 09: before 2010 too, where `register_unpublished` makes an empty table of that name. The glossary already says not to call it "the independent expenditure file". Rejected: `independent_expenditure_24_48`, a 29-character identifier in every NEU-2165 query and in the public dataset's `source_file`; keeping FEC's name and adding a `view` field to `BulkFile`, a catalogue field one file uses and two names for one file from then on; a schema of their own for the bulk-file views, which rewrites every model. |
| Who plants the supporting rows | **This ticket plants everything**: the three files, the rows their cases need in `cm`, `committee_summary`, `webk` and `pas2` (§3.4), and every existing expected value those rows move. For the three new files `expected.yaml` records only `rows.<file>`; which rows silver adds and what they sum to are NEU-2165's, NEU-2166's and NEU-2167's. | The tenfold screen, timeliness and communication costs cannot be planted on today's committees: every fixture `period_end` is 2024-12-31, `pas2.csv` has no 24F or 24N row, and one Form 5 filer reports a figure. Three silver tickets branch from `main`; planted here, none of them edits a shared fixture file. NEU-2151 left `oppexp`'s expected spending to NEU-2152 the same way. Rejected: only the three files on existing committees, which moves most cases and the `cm.csv`, `pas2.csv` and `expected.yaml` edits into NEU-2165 and NEU-2167 together; all rows but the timeliness committee's `pas2` independent expenditures, which loses the ticket's "one before (not added)" case, since a spender with a reported figure and no `pas2` row has its earlier rows added by the by-spender rule. |

Not user decisions, pinned so the diff is predictable:

- **Types** (§2.1). Amounts `DECIMAL(14,2)`, filing numbers `BIGINT`, `SUB_ID` `UBIGINT`, years `SMALLINT`, `NUMBER_OF_CANDIDATES` `SMALLINT`; every date and everything else VARCHAR, as in every catalogued file. No cell of any published cycle, 2010 to 2026, fails a cast under them, and the largest amount is $9,999,999,999.00 (§5).
- **Column names are the header row's, character for character**: the 24/48-hour file's are lower case, the other two upper case.
- **Position.** The three are appended to `FecFile` and `CATALOGUE` after `oppexp`, in the order `ie_24_48`, `ElectioneeringComm`, `CommunicationCosts`. No existing file moves.
- **No reader change.** `transform` already registers every file `files_for(cycle)` lists. `ie_24_48` and `ElectioneeringComm` lack `TRANSACTION_KEY`'s columns, so each is one view. `CommunicationCosts` has all four (`CMTE_ID`, `FILE_NUM`, `TRAN_ID`, `SUB_ID`), so `register_bulk` makes `CommunicationCosts_published`, `CommunicationCosts_repeat` and the view `CommunicationCosts` with repeated rows read once. That is wanted: its rows are `pas2`'s rows under the same `SUB_ID`, and `pas2`'s view drops the same repeat. It drops one row in 2016 and none in any other cycle (§5).
- **No extract change.** `urllib` follows FEC's 302 to S3 already, as it does for `committee_summary`.
- **`transform` reads the three from this merge on**, though no model reads their views until the silver tickets: the pattern NEU-2142 and NEU-2151 set. What that means on the VM is §4.
- **The fixture plants every case project spec §6.2 to §6.4 name** (§3), as NEU-2151's did for §5, not the ticket's nine alone.
- **No ADR.** The name is a catalogue entry; ADR-0002 already covers bronze.

### 1.2 Where the ticket text is corrected

- "`independent_expenditure`" as a catalogue entry is `ie_24_48` (§1.1). The ticket's title names FEC's files and stands.
- "`test_files.py`" is `tests/unit/test_fec_files.py`.
- "amounts `DECIMAL(14,2)`, ids VARCHAR": filing numbers and `SUB_ID` are typed as every catalogued file types them.
- "types are checked against the real 2024 header": they were checked against every cycle's file (§5).
- "`fundlens extract --cycle 2024` on the dev stack writes all three to bronze; a second run downloads nothing" is checked with `--file`, once per file, the two runs back to back (§2.5 step 4). A whole-cycle extract against fec.gov also downloads `indiv24.zip`; the whole-cycle path is covered by `tests/integration/test_extract.py` against the fake FEC. FEC rewrites all three CSVs of every cycle daily at about 10:12 UTC (§5), so a second run on a later day downloads them again, as project spec §3 says of `committee_summary`.
- The fixture's nine cases become §3's lists, with the supporting rows of §3.4.
- Project spec §6.6 says two cycles have cells that fail a cast and "NEU-2164 reads them as NULL". They are blank cells, NULL already; nothing is done for them (§5, §2.4).

## 2. The deliverables, file by file

### 2.1 `src/fundlens/fec/files.py`

- `FecFile` gains `"ie_24_48"`, `"ElectioneeringComm"`, `"CommunicationCosts"`, last, in that order.
- A type constant `COUNT = "SMALLINT"` beside `YEAR`, for `NUMBER_OF_CANDIDATES` (22 at most in any cycle, §5).
- Three entries, each `format="csv"`, `member` `None`, first cycle 2010:

| Entry | `url_pattern` | Columns, in file order (typed ones marked; the rest VARCHAR) |
|---|---|---|
| `ie_24_48` | `{yyyy}/independent_expenditure_{yyyy}.csv` | `cand_id`, `cand_name`, `spe_id`, `spe_nam`, `ele_type`, `can_office_state`, `can_office_dis`, `can_office`, `cand_pty_aff`, `exp_amo` (`AMOUNT`), `exp_date`, `agg_amo` (`AMOUNT`), `sup_opp`, `pur`, `pay`, `file_num` (`FILE_NUM`), `amndt_ind`, `tran_id`, `image_num`, `receipt_dat`, `fec_election_yr` (`YEAR`), `prev_file_num` (`FILE_NUM`), `dissem_dt` |
| `ElectioneeringComm` | `{yyyy}/ElectioneeringComm_{yyyy}.csv` | `CANDIDATE_ID`, `CANDIDATE_NAME`, `CANDIDATE_OFFICE`, `CANDIDATE_STATE`, `CANDIDATE_DISTRICT`, `COMMITTEE_ID`, `COMMITTEE_NAME`, `SB_IMAGE_NUM`, `PAYEE_NAME`, `PAYEE_STREET`, `PAYEE_CITY`, `PAYEE_STATE`, `DISBURSEMENT_DESCRIPTION`, `DISBURSEMENT_DATE`, `COMMUNICATION_DATE`, `PUBLIC_DISBURSEMENT_DATE`, `REPORTED_DISBURSEMENT_AMOUNT` (`AMOUNT`), `NUMBER_OF_CANDIDATES` (`COUNT`), `CALCULATED_CANDIDATE_SHARE` (`AMOUNT`) |
| `CommunicationCosts` | `{yyyy}/CommunicationCosts_{yyyy}.csv` | `CMTE_ID`, `CMTE_NM`, `CAND_ID`, `CAND_NAME`, `CAND_OFFICE`, `CAND_STATE`, `CAND_OFFICE_DISTRICT`, `CAND_PTY_AFFILIATION`, `TRANSACTION_DT`, `TRANSACTION_AMT` (`AMOUNT`), `TRANSACTION_TP`, `COMMUNICATION_TP`, `COMMUNICATION_CLASS`, `SUPPORT_OPPOSE_IND`, `IMAGE_NUM`, `LINE_NUM`, `FORM_TP_CD`, `SCHED_TP_CD`, `TRAN_ID`, `SUB_ID` (`SUB_ID`), `FILE_NUM` (`FILE_NUM`), `RPT_YR` (`YEAR`), `CAND_STATE_DESCRIPTION`, `CAND_PTY_AFFILIATION_DESCRIPTION`, `PURPOSE` |

- A comment on `ie_24_48` says: this is FEC's `independent_expenditure_<yyyy>.csv`, the 24/48-hour file; it is not catalogued under FEC's name because a file's view is named for its entry and `independent_expenditure` is silver's table; its header is lower case; its dates are `DD-MON-YY` (`20-APR-24`), as `ElectioneeringComm`'s are, and `CommunicationCosts`' `YYYYMMDD`; `exp_date` or `dissem_dt` may be blank, never both. It cites project spec §3 and §6.
- A comment on `CommunicationCosts` says it carries the itemized files' transaction key, so its view reads a repeated row once (`transform.runner._drop_fec_repeats`), and that a row of no electronic filing has a negative or blank `FILE_NUM` and no `TRAN_ID`.
- The module docstring's `csv` bullet gains one sentence: an entry's name is the view's and the bronze folder's, and need not be FEC's file name (`ie_24_48`). The comment above the type constants adds the two new date formats.

### 2.2 `src/fundlens/transform/runner.py`

No logic change. The module docstring's first bullet, which says the itemized files `indiv`, `oth` and `pas2` read each transaction once, adds `oppexp` if it is still missing there and `CommunicationCosts`.

### 2.3 Tests

- **`tests/unit/test_fec_files.py`**:
  - The three in the first-cycle parametrization at 2010, which asserts each is in `files_for(2010)` and not in `files_for(2008)`.
  - Their URLs in the URL parametrization: `("ie_24_48", 2024, f"{BASE}/2024/independent_expenditure_2024.csv")`, `("ElectioneeringComm", 2010, f"{BASE}/2010/ElectioneeringComm_2010.csv")`, `("CommunicationCosts", 2024, f"{BASE}/2024/CommunicationCosts_2024.csv")`.
  - `files_for(2010)` is `cm, cn, ccl, indiv, pas2, oth, weball, webk, committee_summary, oppexp, ie_24_48, ElectioneeringComm, CommunicationCosts`, in that order; `files_for(2008)` ends at `oppexp`.
  - Each has its 23, 19 and 25 columns, the typed ones typed as §2.1 says and the rest VARCHAR.
  - `CommunicationCosts` holds every `TRANSACTION_KEY` column; `ie_24_48` and `ElectioneeringComm` do not.
  - **The collision, pinned:** no entry's name, lower-cased, is a silver table's (`get_args(paths.SilverTable)`) or another entry's, and none is another entry's name followed by `_published` or `_repeat`. This is the test that fails if anyone catalogues the file under FEC's name.
- **`tests/unit/test_fec_fixture.py`**:
  - `test_each_csv_has_the_catalogued_header_row_then_every_field_quoted` covers the three through its parametrization.
  - `ie_24_48`: (`file_num`, `tran_id`) is unique; every row has an `exp_date` or a `dissem_dt`; no `file_num` is a `FILE_NUM` of the `pas2`, `indiv`, `oth` or `oppexp` fixture (Q4f); every `prev_file_num` but case 11's names a `file_num` of the same spender in the file; the rows of §3.1's two cm-absent spenders name ids no `cm.csv` row has.
  - The screen's arithmetic, from the fixture CSVs: ONE NATION's rows on no filing another names add up to more than $0 and no more than ten times its `committee_summary` `INDT_EXP`; GUNPOWDER VALUES PROJECT's add up to more than ten times its own.
  - NANTICOKE ACTION's `pas2` independent expenditures are all dated on or before its `CVG_END_DT`, 2024-09-30.
  - `ElectioneeringComm`: §3.2's case 2 is the only disbursement (rows equal on `COMMITTEE_ID`, `SB_IMAGE_NUM`, `PAYEE_NAME`, `DISBURSEMENT_DATE`, `REPORTED_DISBURSEMENT_AMOUNT`) with more rows than its `NUMBER_OF_CANDIDATES`.
  - `CommunicationCosts`: `SUB_ID`s are unique; each is a `pas2.csv` 24F or 24N row's but case 4's; each such pair's `pas2` amount is the CSV's with the cents dropped; the planted repeat is `fec_repeats`' one row for the file, and `pas2`'s repeats gain its twin.
  - The existing tallies and counts (`test_the_expected_counts_match_the_fixture`, `test_the_expected_totals_match_a_tally_of_the_fixture` and the reported-totals tests) pass on the moved values of §3.5.
- **`tests/unit/test_transform_outside_spending_csvs.py`** (new; the ticket's third definition of done). On an in-memory DuckDB connection, as `test_transform_trailing_delimiter.py` does, each fixture file rendered as FEC serves it (`fec_fixture.csv_text`), copied with `copy_as_utf8` and registered with `register_bulk`:
  - `ie_24_48` and `ElectioneeringComm` have `rows.<file>` rows. `CommunicationCosts_published` has `rows.CommunicationCosts`, the view one fewer, and `CommunicationCosts_repeat` holds the repeat's `SUB_ID`.
  - Reading every column of every row raises nothing, and `typeof` gives each typed column its §2.1 type.
  - The lower-case names resolve: `SELECT spe_id, exp_amo FROM ie_24_48`.
  - A blank reads NULL: a blank `exp_date`, `cand_id`, `sup_opp`, `agg_amo` and `prev_file_num`; a blank `CANDIDATE_ID`; a blank `TRAN_ID`.
  - Amounts read as filed: the hoax filing's $9,978,412,568.00, a negative one, one with cents, `$0`, and a share written with one decimal (`26409.5`).
  - A negative `FILE_NUM` reads, and its row is no repeat.
  - A value with a comma reads whole.
- **`tests/integration/test_extract.py`**: a new test, `extract --cycle 2008 --file ie_24_48` exits 2 and requests nothing. The whole-cycle tests take the three in through `files_for`.
- Nothing else should need a change beyond expected values (§3.5): `put_bronze`, `seed`, `test_load`'s `source_dates` and the per-cycle dictionaries all read `files_for` or `FecFile`. If another test fails, fix the test's assumption or the expected value, not the catalogue or the planted rows.

Run while iterating: `task test -- tests/unit/test_fec_files.py tests/unit/test_fec_fixture.py tests/unit/test_transform_outside_spending_csvs.py tests/integration/test_extract.py`, one process at a time. The pre-commit hook runs the whole suite at the commit.

### 2.4 Docs, in the same PR

- **`CONTEXT.md`**: the 24/48-hour file's entry names its catalogue entry. Written at planning; it ships in this PR.
- **Project spec §3.1**:
  - The table's first M3 row: File `ie_24_48`, "On FEC's page as" and URL pattern unchanged.
  - A bullet: the 24/48-hour file is catalogued as `ie_24_48`, not under FEC's name, and why (§1.1).
  - A bullet: every cycle of the three, 2010 to 2026, was read through `register_bulk` on 2026-11-24 with no cast failing (this spec's §5); the 24/48-hour file's header is lower case; dates are `DD-MON-YY` in two files and `YYYYMMDD` in `CommunicationCosts`; `CommunicationCosts` carries the transaction key, so its view reads a repeated row once.
- **Project spec §6**, the name only: `independent_expenditure` becomes `ie_24_48` in §6.2's `source_file` row, in §6.3's "(`CONTEXT.md`; `independent_expenditure` in the file catalogue, 2010–)", in §6.3's "Rows with `source_file = 'independent_expenditure'`" and in §6.7's README sentence. The table `independent_expenditure` keeps its name everywhere.
- **Project spec §6.6**, its last paragraph:
  - "only 2016 and 2018 have cells that fail a cast, 12 and 1 (Q12a, Q12b): NEU-2164 reads them as NULL" becomes: no cell of any cycle fails a cast under the catalogue's types; Q12b's 12 and 1 are blank `exp_amo` cells, NULL as any blank is (this spec's §5).
  - "**Asserted, not measured:** that (`file_num`, `tran_id`) is unique in every cycle's 24/48-hour file" becomes: it is unique in every cycle's file, 2010 to 2026, as read on 2026-11-24 (this spec's §5); the key check still fails a build where it is not.
- **Linear**, patched by `/implementit`, each with "Amended 2026-11-24 by NEU-2164's spec.":
  - NEU-2165: "the race's support/oppose totals change by exactly the two added rows' amounts" becomes "by exactly the added rows' amounts (NEU-2164's spec §3.1 says which step adds or leaves out each row)". Its Fixture bullet gains: the file is `ie_24_48` in the catalogue, and its rows' `source_file`.
  - NEU-2166 and NEU-2167: no text changes; their Fixture bullets' cases are §3.2's 2 and 4 and §3.3's 1.

### 2.5 Order of work

1. The entries and `COUNT` (§2.1), then `tests/unit/test_fec_files.py`.
2. The supporting rows (§3.4), then the three fixture files (§3.1 to §3.3), then `expected.yaml` (§3.5) and the remaining tests.
3. Docs (§2.4). `task format`.
4. Dev stack, against fec.gov: `task up`, then each line twice, the second straight after the first:

   ```bash
   docker compose exec -T app fundlens extract --cycle 2024 --file ie_24_48
   docker compose exec -T app fundlens extract --cycle 2024 --file ElectioneeringComm
   docker compose exec -T app fundlens extract --cycle 2024 --file CommunicationCosts
   ```

   **Expected:** the first run of each logs `<file> 2024 downloaded to bronze/cycle=2024/<file>/<today>.csv (<n> bytes)` (about 19.5 MB, 18 KB and 237 KB); the second logs `<file> 2024 unchanged since bronze/cycle=2024/<file>/<today>.csv` and downloads nothing. A `--file` run writes no marker. This leaves 2024's three files in the dev stack's bronze, which NEU-2165, NEU-2166 and NEU-2167's 2024 dev-stack transforms need.

## 3. The fixture

Three files under `tests/fixtures/fec/2024/`, each a header row of §2.1's names, `#` comment lines saying what each block plants and what project spec §6 makes of it, then the rows. The 1998 fixture cycle gets none: `files_for(1998)` lists none of them.

Conventions for all three:

- Every candidate named is one of `cn.csv`'s unless the case says otherwise. Names of candidates and spenders are written as a filer would, not copied from `cn` and `cm` (mixed case, a middle initial): no model reads them.
- Mostly whole-dollar amounts, so the silver tickets' sums can be checked by hand; each file has at least two amounts with cents.
- Dates in `ie_24_48` and `ElectioneeringComm` are `DD-MON-YY` with the month in capitals (`15-OCT-24`); in `CommunicationCosts`, `YYYYMMDD`.
- A value may hold a comma; the fixture builder quotes every field. No value holds a `"`: no cell of any published cycle does (§5), and `sample.csv` covers the rendering.

### 3.1 `ie_24_48.csv`

About 40 rows. `fec_election_yr` is 2024 on every row. `file_num`s run `1910001` upward, a block no other fixture file uses, one per filing. `tran_id`s follow real shapes (`SE.4128`, `F57.000003`, a 20-character hex id, a web form's `WFT20243201436-1`). `image_num` is 18 digits and `receipt_dat` a day or two after the row's date. `ele_type` has `G` and `P`; `can_office_dis` is `00` for a Senate or presidential candidate and `05` for a Maryland 5th one; `cand_pty_aff` is written out (`DEMOCRATIC PARTY`). One `spe_nam` begins with a space (2024's `" Go America PAC"`), and one row's `agg_amo` is blank.

The opening comment gives §6.3's five steps in a line each. Each block's comment names its case, the step that decides it, and whether NEU-2165 adds its rows.

Spenders:

| Spender | In `cm` | Reported independent expenditures | `pas2` IE | `period_end` |
|---|---|---|---|---|
| ONE NATION `C90800206` | type `I` | $30,000 | none | 2024-12-31 |
| GUNPOWDER VALUES PROJECT `C90800209` (new) | type `I` | $1,000 | none | 2024-12-31 |
| NANTICOKE ACTION `C00800210` (new) | type `O` | its `pas2` sum | two rows, by 2024-09-30 | 2024-09-30 |
| MARYLAND FORWARD PAC `C00800201` | type `O` | $670,000 | six rows | 2024-12-31 |
| RESTORATION PAC `C00800205` | type `O` | $0 | none | 2024-12-31 |
| RESTORATION PAC `C90800207` | type `E` | blank | none | blank |
| Two ids no `cm` row has | no | — | — | — |

| # | Plants | Rows and what makes the case | §6.3 |
|---|---|---|---|
| 1 | Added by spender | ONE NATION, an original filing (`N`): one row for OKAFOR (`S`), one against WHITLOCK (`O`), amounts with cents | Step 4: added |
| 2 | A row with no `exp_date` | ONE NATION: `exp_date` blank, `dissem_dt` filled. Its date is `dissem_dt` | Step 4: added |
| 3 | A row with no side | ONE NATION: `sup_opp` blank, a small amount (2024's is $85) | Step 4: added; in no candidate's or race's figure |
| 4 | A row naming no candidate | ONE NATION: `cand_id` blank, `cand_name` filled | Step 4: added, candidate and race NULL |
| 5 | A row naming an id `cn` lacks | ONE NATION | Step 4: added, candidate and race NULL |
| 6 | An alias | ONE NATION: `cand_id` `H6MD05113`, which is `H4MD05107`'s alias | Step 4: added, DRISCOLL's |
| 7 | The handoff | ONE NATION: two rows naming `P80000722`, dated `20-JUL-24` and `21-JUL-24` | Step 4: added; the first BIDEN's, the second HARRIS's |
| 8 | A negative amount and a `$0` row | ONE NATION | Step 4: added, as filed |
| 9 | The filing chain | ONE NATION: filing A (`N`) with two rows; filing B (`A1`, `prev_file_num` A) restates the first under the same `tran_id` with another amount and the second under a new `tran_id` | Step 1: A's rows not read. B's added |
| 10 | A chain of two | ONE NATION: C (`N`), D (`A1`, names C), E (`A2`, names D), one row each | Step 1: only E's row is read, and added |
| 11 | An amendment naming a filing the file lacks | ONE NATION: `A1`, `prev_file_num` a number no row has | Kept, added |
| 12 | An `A1` naming no filing | ONE NATION: `amndt_ind` `A1`, `prev_file_num` blank | Kept, added |
| 13 | One original named by two amendments | ONE NATION: F (`N`), and two `A1` filings each naming F, each with one row | F's row not read; both amendments' rows added (counted twice, as filed, Q3d) |
| 14 | One `tran_id` on two filings | ONE NATION: `SE.1` on two original filings, neither naming the other, two different expenditures | Both added; their `source_record_id`s differ by `file_num` |
| 15 | The tenfold screen | GUNPOWDER VALUES PROJECT: two rows adding up to more than $10,000, both dated on or before 2024-12-31. A row after its `period_end` would be added by timeliness, since its reported figure is a track record: it has none | Step 4: not added |
| 16 | A hoax filing at a spender `cm` lacks | One row at an id in no `cm` row: `tran_id` `WFT20243201436-1`, `exp_amo` `9978412568`, `agg_amo` below it, `pur` `Political Contribution`, for HARGROVE (2024's largest row, Q1j) | Step 2: dropped |
| 17 | A real spender `cm` lacks | One Form 5 line at a second absent id, a few thousand dollars (Casey Family Farms' shape, Q2b) | Step 2: dropped |
| 18 | A hoax filing at a committee that reports none | RESTORATION PAC `C00800205`: a web-form row of $255,000,000 | Step 4: not added (no figure above $0) |
| 19 | A spender with no period end | RESTORATION PAC `C90800207`: one row | Not added by step 3 or 4 |
| 20 | Timeliness | NANTICOKE ACTION: a row dated `15-OCT-24`; and one with `exp_date` blank and `dissem_dt` `20-OCT-24` | Step 3: both added |
| 21 | Before the period end | NANTICOKE ACTION: a row dated `15-SEP-24`, the 48-hour report of one of its `pas2` rows, under that row's `TRAN_ID`, its amount an estimate that differs | Step 5: not read |
| 22 | On the period end | NANTICOKE ACTION: a row dated `30-SEP-24` | Step 5: not read ("after") |
| 23 | The chain before timeliness | NANTICOKE ACTION: a row dated `22-OCT-24` on a filing an `A1` replaces; the amendment's row, another amount | The first not read (step 1); the amendment's added (step 3) |
| 24 | A spender `pas2` holds | MARYLAND FORWARD PAC: the 48-hour report of `pas2`'s `SE.00301` ($120,000, 2024-09-20), same `tran_id`, `exp_amo` `118500`, dated `18-SEP-24` | Step 5: not read |

ONE NATION's rows that survive the chain add up to a little over its reported $30,000 and far under ten times it, as 2024's fourteen added spenders do ($1,001,297 against $996,357 reported, Q6).

The tenfold boundary (exactly ten times is added) and a spender with a track record through its reported figure alone are NEU-2165's to test on hand-made rows, not planted here.

### 3.2 `ElectioneeringComm.csv`

About 16 rows. The spender is RESTORATION PAC `C90800207` (type `E`) but in case 10. `SB_IMAGE_NUM` is 18 digits. Each block's comment names its case and what project spec §6.4 makes of it.

| # | Plants | Rows and what makes the case | §6.4 |
|---|---|---|---|
| 1 | One candidate, one row | For OKAFOR; share equals the amount | Kept |
| 2 | A disbursement's copies | One-candidate disbursement on two rows, both naming CALLOWAY, equal on the five disbursement columns and differing in `COMMUNICATION_DATE` alone (2024's Evan Low pair) | One kept, one dropped |
| 3 | Two candidates, both named | OKAFOR and WHITLOCK, one row each, an odd amount so each share ends in `.5` (FEC writes `61660.5`) | Both kept |
| 4 | Two candidates, none named | Two rows equal in every column, `CANDIDATE_ID` and the candidate's columns blank, `NUMBER_OF_CANDIDATES` 2 (Q9i) | Both kept, candidate and race NULL |
| 5 | Fewer rows than candidates | A two-candidate disbursement with one row | Kept; the disbursement is half short |
| 6 | An id `cn` lacks | One row | Kept, candidate and race NULL |
| 7 | A split off by more than a cent | `CALCULATED_CANDIDATE_SHARE` times `NUMBER_OF_CANDIDATES` is not the amount (2010's shape, Q12f) | Kept, the share as filed |
| 8 | The handoff | Two rows naming `P80000722`, `DISBURSEMENT_DATE` `20-JUL-24` and `21-JUL-24` | BIDEN's, then HARRIS's |
| 9 | An alias | `CANDIDATE_ID` `H6MD05113` | DRISCOLL's |
| 10 | A spender `cm` lacks | One row at an id in no `cm` row | Dropped |
| 11 | A restated report | The same payee, date, amount and candidate on two `SB_IMAGE_NUM`s | Both kept: no amendment rule |
| 12 | A blank `PUBLIC_DISBURSEMENT_DATE` | On one of the rows above | NULL |

### 3.3 `CommunicationCosts.csv`

Six rows, and one in `pas2.csv` alone. The filer is STEAMFITTERS LOCAL 486 `C70800208` (new, type `C`, a union). `FORM_TP_CD` `F7`, `SCHED_TP_CD` `F76`, `LINE_NUM` and `PURPOSE` blank, `IMAGE_NUM` FEC's URL form (`http://docquery.fec.gov/cgi-bin/fecimg/?<18 digits>`). Each row's `SUB_ID` is its `pas2` twin's.

| # | Plants | Rows and what makes the case | §6.2 |
|---|---|---|---|
| 1 | A communication cost in both files | A `24F` for OKAFOR; the CSV's amount has cents and `pas2`'s is the same with the cents dropped; `COMMUNICATION_TP` `DM`, `COMMUNICATION_CLASS` `M`, `SUPPORT_OPPOSE_IND` `S` | Counted once, from `pas2`; type and class from the CSV |
| 2 | One against | A `24N` against WHITLOCK; `COMMUNICATION_TP` `O`, `COMMUNICATION_CLASS` `E`, `SUPPORT_OPPOSE_IND` `O` | The same |
| 3 | A `pas2` row the CSV lacks | In `pas2.csv` only: a `24F` naming no candidate | Counts, type and class NULL |
| 4 | A CSV row `pas2` lacks | A `SUB_ID` no `pas2.csv` row has | Adds nothing |
| 5 | A row with a negative `FILE_NUM` | `RPT_YR` 2023, a negative `FILE_NUM`, `TRAN_ID` blank, `24F` in `SUPPORT_OPPOSE_IND`. Its `pas2` twin is written as FEC's `pas2` writes one of 2024's six such rows (`SUB_ID` `1091820230265311382`), which the implementer reads first | Counted from `pas2`; no repeat |
| 6 | A repeated row | Two rows equal in every column but `SUB_ID`, `FILE_NUM` above 0, `TRAN_ID` filled (2016's `F7612291673341`), and the same two in `pas2.csv` | Each view reads the lower `SUB_ID`; `CommunicationCosts_repeat` and `pas2_repeat` hold the higher |

### 3.4 Supporting rows in existing fixture files

Names and ids below are in no fixture file today, so no name rule (NEU-2131, NEU-2195), organization key or payee key matches them.

- **`cm.csv`**, three rows, each under a comment saying what it is for:
  - `C70800208` STEAMFITTERS LOCAL 486: `CMTE_TP` `C`, `CMTE_DSGN` `U`, `ORG_TP` `L`. A Form 7 filer.
  - `C90800209` GUNPOWDER VALUES PROJECT: `CMTE_TP` `I`, `CMTE_DSGN` `U`. A Form 5 filer.
  - `C00800210` NANTICOKE ACTION: `CMTE_TP` `O`, `CMTE_DSGN` `U`. A super PAC whose last report ends 2024-09-30.
- **`committee_summary.csv`**, three rows:
  - `C70800208`: coverage 2023-01-01 to 2024-12-31, `TTL_COMMUNICATION_COST` the sum of its `pas2` rows, as 65 of 2024's 68 type-`C` rows carry one (§5).
  - `C90800209`: coverage 2023-01-01 to 2024-12-31, `INDT_EXP` `1000`.
  - `C00800210`: coverage 2023-01-01 to **2024-09-30**, `INDT_EXP` the sum of its two `pas2` rows, its other figures consistent with having raised and spent that much.
- **`webk.csv`**: a row for `C00800210`, agreeing with its `committee_summary` row, as MARYLAND FORWARD PAC and RESTORATION PAC have one.
- **`pas2.csv`**, eight rows, `SUB_ID`s continuing its `42402…` block but case 5's:
  - NANTICOKE ACTION: a `24E` for OKAFOR and a `24A` against WHITLOCK, dated August and September 2024, on a filing of its own. One is §3.1 case 21's row.
  - STEAMFITTERS LOCAL 486: §3.3's cases 1, 2, 3, 5 and 6 (two rows), modelled on real 2024 `pas2` 24F and 24N rows (Q8).

No `cn`, `ccl`, `indiv`, `oth`, `oppexp` or `weball` row is added.

### 3.5 `expected.yaml` and the values that move

- `rows` gains `ie_24_48`, `ElectioneeringComm` and `CommunicationCosts`, and its `cm`, `pas2`, `committee_summary` and `webk` counts rise by §3.4's rows.
- The supporting rows move existing values, each updated to what the fixture now holds and nothing else: `silver.committee`, `silver.independent_expenditure` (two `ie` rows and five `communication_cost` rows, the repeat dropped) and `silver.reported_total`; the Maryland Senate race's and OKAFOR's and WHITLOCK's independent-expenditure figures, by NANTICOKE ACTION's two rows; `race_top_committees`; the `committees` and `reported_totals` entries for the three new committees; `gold_reported`; and whatever else the tally tests and the hook's suite name. The 24F and 24N rows are in no total, as the 24C row is not.
- No expected value is added for what silver makes of the three new files. The comment above `rows` says so and names NEU-2165, NEU-2166 and NEU-2167.

## 4. At the merge

Nothing reads the three views yet, and three things change on the VM:

- **The next weekly run** (`fundlens run`, cycle 2026) downloads the three CSVs (13,733,832, 12,275 and 48,982 bytes on 2026-11-24) to `bronze/cycle=2026/<file>/<date>.csv` and keeps them on local disk with the current cycle's other files. FEC rewrites them daily, so every weekly extract writes three new dated objects, as `committee_summary`'s does. Its transform copies them under `scratch/` and registers three views; only `CommunicationCosts` (165 rows) gets the repeated-row scan. **Asserted, not measured:** that this does not move the transform's memory peak; the largest of the three in any cycle is 42 MB (2016).
- **A transform of a cycle from 2010 on whose bronze lacks any of the three** stops with `FileNotFoundError: no <file> file in bronze for <cycle>` before anything is written. That is every such cycle already extracted, 2024's live build among them, until they are extracted:

  ```bash
  docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --file ie_24_48
  docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --file ElectioneeringComm
  docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --file CommunicationCosts
  ```

  NEU-2171's runbook runs these for 2024 before it transforms, as `spending-run.md` did for `oppexp`. Anyone re-transforming an older cycle by hand sooner runs them first. A cycle's own full `extract` downloads them with the rest, so NEU-2180's backfill needs nothing extra.
- **`gold.meta.source_dates`** names the three for a cycle once its bronze has them, and leaves them out before (`load/gold.py` `_source_dates`). `/meta` types it `dict[str, date]`, and the methodology page reads the distinct dates only. The 24/48-hour file's key there is `ie_24_48`.

Merge outside the windows `docs/runbooks/weekly.md` gives (02:00 to 02:30 UTC daily; Sunday from 03:00 UTC to the run's end).

## 5. What FEC served, and what the reader did with it

Run on the dev stack's `app` container on 2026-11-24, after FEC's publication of that morning and before 16:22 UTC, DuckDB 2.0.0, `main` at `691a998`. Each file was downloaded from `https://www.fec.gov/files/bulk-downloads/<yyyy>/<stem>_<yyyy>.csv`, copied with `copy_as_utf8` and registered with `register_bulk` under a `BulkFile` of §2.1's columns and types, then every row read into a table. Every file's `Last-Modified` was that day's, between 10:11:58 and 10:13:31 GMT. Nothing was written to bronze.

**In every one of the 27 files:** the header row equals §2.1's columns; no record has another width; no field holds a `"` or a line break; there is no CR byte; and the typed read raises nothing.

**The 24/48-hour file.** No filled cell fails a cast in `exp_amo`, `agg_amo`, `file_num`, `fec_election_yr` or `prev_file_num`. Every filled `exp_date`, `dissem_dt` and `receipt_dat` parses as `%d-%b-%y`. `spe_id` and `tran_id` are never blank, and (`file_num`, `tran_id`) is on one row only, in every cycle.

| Cycle | Bytes | Rows | `exp_amo` blank | `agg_amo` blank | `prev_file_num` filled | Largest `exp_amo` |
|---|---|---|---|---|---|---|
| 2010 | 11,437,199 | 48,328 | 0 | 2 | 11,895 | 2,750,000.00 |
| 2012 | 26,951,945 | 113,386 | 0 | 475 | 13,233 | 17,661,251.08 |
| 2014 | 16,656,127 | 68,234 | 0 | 6 | 3,451 | 7,750,494.00 |
| 2016 | 42,350,280 | 171,405 | 12 | 161 | 12,137 | 50,000,000.00 |
| 2018 | 11,772,520 | 45,039 | 1 | 123 | 7,433 | 4,611,105.52 |
| 2020 | 21,357,680 | 80,766 | 0 | 99 | 12,327 | 850,000,000.00 |
| 2022 | 16,646,736 | 61,779 | 0 | 258 | 6,393 | 9,999,999,999.00 |
| 2024 | 19,534,174 | 73,449 | 0 | 160 | 12,867 | 9,978,412,568.00 |
| 2026 | 13,733,832 | 51,403 | 0 | 61 | 5,050 | 9,000,000,000.00 |

The measurement's Q12b counts 12 and 1 "cast fails" in 2016 and 2018: its measure adds rows whose amount is NULL, and those are these blank `exp_amo` cells. `DECIMAL(14,2)` holds up to $999,999,999,999.99, a hundred times the largest hoax filing.

**The electioneering file.** No cell of `REPORTED_DISBURSEMENT_AMOUNT`, `NUMBER_OF_CANDIDATES` or `CALCULATED_CANDIDATE_SHARE` is blank or fails a cast, and every filled date parses as `%d-%b-%y`. `COMMITTEE_ID` is never blank.

| Cycle | Bytes | Rows | Largest amount | Largest `NUMBER_OF_CANDIDATES` |
|---|---|---|---|---|
| 2010 | 160,783 | 654 | 1,226,000.00 | 22 |
| 2012 | 75,779 | 288 | 1,002,620.60 | 8 |
| 2014 | 10,506 | 40 | 1,916,222.00 | 2 |
| 2016 | 27,703 | 97 | 943,360.00 | 2 |
| 2018 | 51,662 | 212 | 2,754,571.05 | 10 |
| 2020 | 71,074 | 273 | 1,598,138.92 | 5 |
| 2022 | 11,977 | 45 | 600,000.00 | 2 |
| 2024 | 18,370 | 69 | 1,574,994.00 | 2 |
| 2026 | 12,275 | 45 | 1,050,312.00 | 2 |

2026's file had 48 rows and 13,079 bytes when the measurement read it a day earlier: FEC's file lost three rows overnight.

**The communication-costs file.** No filled cell fails a cast in `TRANSACTION_AMT`, `SUB_ID`, `FILE_NUM` or `RPT_YR`, and every filled `TRANSACTION_DT` parses as `%Y%m%d`. `SUB_ID` is never blank and never repeated.

| Cycle | Bytes | Rows | `TRAN_ID` blank | `FILE_NUM` blank | `FILE_NUM` ≤ 0 | `TRANSACTION_DT` blank | `PURPOSE` filled | Repeated rows | Largest amount |
|---|---|---|---|---|---|---|---|---|---|
| 2010 | 1,819,157 | 5,947 | 313 | 313 | 0 | 0 | 0 | 0 | 2,983,844.00 |
| 2012 | 1,718,667 | 5,791 | 11 | 0 | 0 | 0 | 0 | 0 | 846,596.14 |
| 2014 | 1,136,509 | 3,961 | 47 | 0 | 0 | 1 | 1 | 0 | 343,159.36 |
| 2016 | 761,139 | 2,382 | 0 | 0 | 0 | 23 | 1 | 1 | 1,174,734.00 |
| 2018 | 411,037 | 1,344 | 0 | 0 | 0 | 7 | 1 | 0 | 221,369.11 |
| 2020 | 308,464 | 1,018 | 0 | 0 | 0 | 0 | 0 | 0 | 222,812.24 |
| 2022 | 1,280,869 | 4,416 | 3,530 | 0 | 3,530 | 0 | 0 | 0 | 227,500.00 |
| 2024 | 237,322 | 779 | 6 | 0 | 6 | 0 | 0 | 0 | 1,116,681.00 |
| 2026 | 48,982 | 165 | 0 | 0 | 0 | 0 | 0 | 0 | 382,649.75 |

- The one repeated row is 2016's: `C70000211`, filing `1136232`, `TRAN_ID` `F7612291673341`, $512.52, under `SUB_ID`s `2011820171368326095` and `…096`. The view reads the first.
- A row with no `TRAN_ID` has a blank `FILE_NUM` in 2010 and a negative one in 2022 and 2024 (`-1104456`): no electronic filing, which the reader's repeated-row rule takes a `FILE_NUM` above 0 to be. 2012's 11 and 2014's 47 have a `FILE_NUM` above 0. `SUPPORT_OPPOSE_IND` holds `24F` or `24N` in place of `S` or `O` on some rows of 2022 and 2024 (Q1i).
- `PURPOSE` is filled on three rows in all, none of 2024's.

**Two things read on the way, for other tickets.** Neither changes this one.

- FEC's `committee_summary_2024.csv` holds 68 rows of type `C`, each with a `CVG_END_DT`, 65 with `TTL_COMMUNICATION_COST` above 0; 208 of type `I`, 200 with `INDT_EXP` above 0; and none of type `E`. Project spec §6.2 says Form 7's reported total is in no file fundlens reads. Whether that sentence should change is NEU-2167's to say.
- The fixture's type-`E` row in `committee_summary.csv` (`C90800207`) has no counterpart in FEC's 2024 file. It stays: §3.1's case 19 uses it.

## 6. Acceptance criteria

- [ ] `tests/unit/test_fec_files.py` asserts the three entries' first cycle (2010), URLs, column counts and types, that `files_for(2008)` excludes them, and that no entry's name is a silver table's.
- [ ] `tests/unit/test_transform_outside_spending_csvs.py` passes: each fixture file, rendered as FEC serves it, reads through `register_bulk` with no cast error, blanks as NULL, the hoax filing's amount whole, and `CommunicationCosts`' repeat dropped.
- [ ] The three fixture files hold every case of §3.1, §3.2 and §3.3, each under a comment naming its case and what project spec §6 makes of it, and `expected.yaml`'s `rows` has their counts.
- [ ] `cm.csv`, `committee_summary.csv`, `webk.csv` and `pas2.csv` hold §3.4's rows, and `tests/unit/test_fec_fixture.py`'s tallies pass on the updated `expected.yaml`.
- [ ] The fixture transform runs: `tests/integration/test_transform.py` passes with the three views registered beside silver's `independent_expenditure`.
- [ ] `fundlens extract --cycle 2024 --file <file>` on the dev stack writes `bronze/cycle=2024/<file>/<date>.csv` for each of the three; a second run straight after logs `unchanged` and downloads nothing.
- [ ] `extract --cycle 2008 --file ie_24_48` exits 2.
- [ ] Project spec §3.1, §6.2, §6.3, §6.6 and §6.7 are amended as §2.4 says, `CONTEXT.md`'s entry ships, and NEU-2165's description is patched.
- [ ] `task fec:headers -- --check` still exits 0: a CSV has no vendored header.
- [ ] The pre-commit hook's full suite passes, and no new test is near the top of its slowest-tests list.

## 7. Out of scope

- Any silver model, check or expected silver value for the three files: NEU-2165 (`ie_24_48` into `independent_expenditure`), NEU-2166 (`electioneering_communication`), NEU-2167 (communication type and class).
- Gold, the API, pages, the dataset, `BACKFILL_PENDING`, `columns.yaml`.
- Extracting the three on the VM for any cycle: NEU-2171's runbook for 2024, NEU-2180's backfill for the rest.
- Any change to `extract`, `fetch_bulk`, `copy_as_utf8` or `register_bulk`.
- Adding `CommunicationCosts_repeat` to `sql/checks/silver_fec_repeat.sql`: no silver table is built from the file's rows; NEU-2167 joins two of its columns on.
- Whether project spec §6.2's sentence on Form 7's reported total stands (§5): NEU-2167.
- `docs/capacity.md`: bronze grows by about 0.2 GB over all nine cycles per extract, recorded when a run measures it.
