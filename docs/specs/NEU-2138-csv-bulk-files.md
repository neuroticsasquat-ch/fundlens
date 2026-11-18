# NEU-2138 — CSV bulk files: a `format` and a URL pattern on the file catalogue, header-checked extract, the CSV reader

**Ticket:** [NEU-2138](https://linear.app/neuroticsasquatch/issue/NEU-2138) · **Milestone:** M1 Reported totals · **Project:** P-NEU-107 "fundlens: every FEC dollar"
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §3 (formats, the three URL shapes, the ten files), read with the v1 spec §3.4 (storage layout), §5.1 (extract), §5.3 (transform), §12 (testing) · **Glossary:** `CONTEXT.md` (File catalogue, Undated file, Bronze) · **ADRs:** 0002 (R2 is the source of truth; bronze is the file as downloaded)
**Blocked by:** NEU-2137 (merged, PR #184). **Blocks:** NEU-2142 (`committee_summary`), NEU-2164 (`independent_expenditure`, `ElectioneeringComm`, `CommunicationCosts`), NEU-2174 (`leadership`, `lobbyist`, `lobbyist_bundle`).

Planned 2026-11-18. `/implementit NEU-2138` produces **one PR**: the mechanism in `fec/files.py`, `fec/extract.py`, `transform/runner.py` and `paths.py`, two small fixes it forces (`load/gold.py`, `fec/refresh_headers.py`), the fixture builder's CSV support with a two-row sample, and the doc amendments in §2.8. It adds **no file to `CATALOGUE`**. Where the Linear ticket and this spec differ, this spec wins (§1.2).

## 1. What and why

`fundlens extract` and the transform reader handle one kind of bulk file: a zip holding pipe-delimited text with no header row, at `<yyyy>/<name><yy>.zip`, its columns named by a vendored header. Seven of the ten files P-NEU-107 adds are comma-separated CSVs with a header row, not zipped, at three URL shapes (project spec §3). Nothing can catalogue them today: `BulkFile.url` hard-codes the zip URL, `_download` rejects anything that is not a zip, and the reader opens a zip member.

This ticket adds the mechanism, and tests it with two test-only catalogue entries. The three file tickets it blocks then add entries, fixtures and silver models, and touch no extract or reader code.

### 1.1 Decisions this spec pins (grilled 2026-11-18)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| A CSV whose header row is not the catalogue's column list | **Exact match, checked twice.** The header row must equal the entry's `columns`: the same names, in the same order. Extract rejects a download that differs, so it never reaches bronze. Transform checks the bronze file again before reading it. | FEC's header rows are byte-identical in every cycle of all five per-cycle files (§5), so a difference is an event a person should see, and it stops the run as loudly as a zip's column drift does. Exact match also lets the reader give DuckDB explicit columns, with no sniffing. Rejected: requiring only that the header contain the catalogued columns and reading by name, which survives an added column but tells nobody; a structural check only, which moves the failure to transform. |
| Encoding at transform | **A CSV goes through `copy_as_utf8`, as a zip's text does.** Every bulk file is copied into scratch as UTF-8 without NUL bytes and read from there. Bronze is untouched. | The eight files sampled are pure ASCII (§5), but that is one cycle per file. A stray latin-1 byte or NUL in another cycle would fail a transform mid-backfill (NEU-2069) or reach Postgres (NEU-2282), and the extra pass is over at most about 20 MB. Rejected: reading the bronze file directly as strict UTF-8. |
| The change check for CSVs | **`Last-Modified` and size, as for zips.** | FEC rewrites some historical CSVs daily (`committee_summary_2008.csv` had that day's `Last-Modified`, §5), so re-extracting a historical cycle downloads those files again and writes a new dated bronze object. The weekly run extracts only the current cycle, and the files are small. v1 §3.4's "historical cycles download once" gets a recorded exception (§2.8). Rejected: comparing a content hash, a second change check that still has to download (S3's ETag is not an MD5 for a multipart upload such as `independent_expenditure_2024.csv`). |
| How tests put a CSV entry in front of the code | **Test-only `BulkFile`s** defined under `tests/`, passed to `extract_file` and to the reader functions, which take a `BulkFile` already. `CATALOGUE`, `FecFile`, and the signatures of `extract()` and `transform()` do not change. | The cycle-level loops only dispatch to the functions tested here; they first see a CSV when NEU-2142 catalogues `committee_summary`. Rejected: a `catalogue` parameter on `files_for`, `extract()` and `transform()` that only tests pass; patching `CATALOGUE` in tests. |
| The fixture builder | **`tests/fec_fixture.py` learns CSV-format entries here**, and this ticket's sample goes through it. | NEU-2142, NEU-2164 and NEU-2174 each add CSV fixture files; one convention, written once. Rejected: leaving it to NEU-2142, which is implemented from the project spec alone. |
| Glossary | **"Undated file"** is a term (`CONTEXT.md`, added at planning). | The project spec and three tickets already use the word. |

Not user decisions, pinned so the diff is predictable:

- **An undated file needs no flag.** It is an entry whose URL pattern names no cycle. Extract keys bronze by the cycle being extracted whatever the URL, so the same URL extracted for two cycles writes two bronze objects, each with its own change check. Nothing else treats it differently.
- **The dialect is RFC 4180:** comma, `"` as the quote, `""` as the escape, a header row. No sampled file has a quote character inside a field (§5), so how FEC escapes one is unobserved; the reader takes the standard.
- **A blank field is NULL**, as a zip's empty field is. FEC writes a blank as `""`.
- **A wrong header at extract is a `DownloadError`**, as "not a zip" is: it is retried, then fails the step.

### 1.2 Where the ticket text is corrected

- The ticket names two URL shapes. There are three (project spec §3); the URL pattern covers all of them.
- The ticket says extract validates a CSV "by its header row". This spec says against what (the entry's `columns`, exactly) and adds the same check at transform.
- The ticket does not mention `load/gold.py`, which strips `.zip` from a bronze key to get a source date (§2.5), or `fec/refresh_headers.py`, which fetches a header file for every entry (§2.6). Both break on the first real CSV entry.
- "A test entry in the fixture catalogue" means the test-only `BulkFile`s of §2.7, not an entry in `CATALOGUE`.

## 2. The deliverables, file by file

Function and field names below are the intended ones. The implementer may rename where the code reads better, but not change behaviour.

### 2.1 `src/fundlens/fec/files.py`

- `Format = Literal["zip", "csv"]`.
- `BulkFile` gains two fields:
  - `format: Format = "zip"`.
  - `url_pattern: str | None = None`: the file's URL below the base URL, a `str.format` template whose only placeholders are `{yyyy}` (the cycle, four digits) and `{yy}` (two digits, zero-padded). The file's name is written out in it, not substituted. `None` is allowed for a zip only and means `{yyyy}/<name>{yy}.zip`, today's URL.
- `member` becomes `str | None`: `None` for a CSV.
- `__post_init__` raises `ValueError` for an entry that cannot work, so a bad entry fails at import and not at its first extract: a zip without a `member`; a CSV with a `member` or a `split_dir`, or without a `url_pattern`; a pattern with any other placeholder.
- `url(base_url, cycle)` renders the pattern. The six existing entries' URLs do not change.
- `header_file` returns `None` for a CSV. `header()` returns `list(self.columns)` for a CSV: its header row is in the file, and the catalogue's `columns` is what that row must be. For a zip both are as today.
- `read_csv_header(path: Path) -> list[str]`: the first line of the file at `path`, parsed as one CSV record. It reads at most 64 KiB looking for the first newline, and decodes with replacement, so a zip, an HTML page or an empty file returns a list that equals no entry's columns instead of raising. No BOM is stripped: FEC sends none (§5), and one would be a difference worth failing on.
- The module docstring is rewritten for two formats and three URL shapes. `CATALOGUE` and `FecFile` are unchanged.

`BulkFile` holds a dict, so it does not hash; anything that caches by entry caches by name.

### 2.2 `src/fundlens/paths.py`

- `bronze_csv(cycle, file, download_date)`: `bronze/cycle=<c>/<file>/<date>.csv`. `bronze_zip` is unchanged.
- `download_date_of(key) -> str`: the ISO download date a bronze key ends in, for either suffix (`bronze/cycle=2026/indiv/2026-11-02.zip` and `…/2026-11-02.csv` both give `2026-11-02`).

### 2.3 `src/fundlens/fec/extract.py`

`extract_file` does what it does today, with two differences for `format == "csv"`:

- The bronze key is `paths.bronze_csv(...)`.
- `_download` validates the finished `.part` file by format. A zip: `zipfile.is_zipfile`, as today. A CSV: `read_csv_header(partial) == list(file.columns)`, else `DownloadError` naming the URL and saying the header is not the catalogued one. The size check against `Content-Length` runs first for both.

Everything else is shared and unchanged: the HEAD, the `Last-Modified`/size comparison with the newest bronze object's metadata, the `.part` file, the retries, the object metadata, keeping only the current cycle on disk, and fetching the current cycle's file back from R2 when only the disk copy is missing.

`extract()` is unchanged apart from its docstring. The module docstring, `Source`'s and `DownloadError`'s say "file", not "zip", where they now cover both, and the module docstring records that FEC rewrites some historical CSVs daily, so those download again on every re-extract (§1.1).

### 2.4 `src/fundlens/transform/runner.py`, and `resolve/validate.py`'s call

Two functions, each dispatching on `file.format`, replace today's zip-only pair for every caller:

- **Fetch** (today `unzip_bulk`): the newest bronze object of `file`, as UTF-8 text under `work`; returns the text's path. The local-copy rule is today's for both formats: the current cycle's file is read from the bronze cache, any other is downloaded into `work` and never outlives the run.
  - zip: as today (`copy_bulk`).
  - csv: before copying, `read_csv_header(local)` must equal `list(file.columns)`, else `ValueError` naming the bronze key, raised before any SQL runs. Then the file is copied through `copy_as_utf8` to `work/<name>.txt`.
- **Register** (`register_bulk`): the view `<file.name>`, every column read as VARCHAR and then cast to the catalogue's type, as today.
  - zip: unchanged, including the check of the vendored header against the catalogue.
  - csv: `read_csv` with `delim = ','`, `quote = '"'`, `escape = '"'`, `header = true`, `auto_detect = false`, the entry's columns as explicit VARCHAR columns, and `encoding = 'utf-8'`. A blank field, which FEC writes as `""`, must read as NULL; the test in §3 holds this, and the implementer sets whatever option DuckDB 2.0 needs for it.

`register_unpublished` needs no change: it builds an empty table from `columns` for either format.

`transform()` and `resolve/validate.py` call the fetch function under whatever name it ends with. `validate` reads `indiv` only, a zip, and its behaviour does not change. The module docstring's first bullet is rewritten: one view per bulk file, from a zip's member or a CSV, both rewritten as UTF-8 under `scratch/`.

### 2.5 `src/fundlens/load/gold.py`

`_source_dates` takes each file's date with `paths.download_date_of(keys[-1])` instead of `removesuffix(".zip")`. Today a CSV's source date would come out as `2026-11-02.csv`, which `api/schemas.py`'s `source_dates: dict[str, date]` refuses.

### 2.6 `src/fundlens/fec/refresh_headers.py`

Skips an entry whose `header_file` is `None`. A CSV has no vendored header to refresh.

### 2.7 Tests

**`tests/fake_fec.py`.** `FakeFec` can serve any body at any URL path, with a `Content-Type` (`text/csv` for a CSV, as FEC's bucket sends). `serve(cycle, name, …)` keeps working for zips, so the existing extract tests are not edited.

**`tests/fec_fixture.py`.** The fixture builder works from a `BulkFile`, not only from a name in `CATALOGUE`, and dispatches on `format`:

- A CSV-format fixture file is hand-written like the zip ones: a header row, then rows, with `#` comment lines. Its header row must equal the entry's `columns`, and every row must have one value per column; a `|` in a value is allowed.
- It is rendered into FEC's layout (§5): the header row unquoted, every data field double-quoted with `""` for a quote, LF line endings.
- Serving publishes each of a cycle's files at the path its `url()` gives, a zip as a zip and a CSV as the rendered text.
- The name-based functions the existing tests call (`read_rows("indiv")`, `bulk_text`, `zips`, `serve`) keep their behaviour.

**The sample.** `tests/fixtures/fec/csv/sample.csv`: two rows, four or five columns, at least one typed as `AMOUNT`. One row has a value holding a comma and a `"`, and a blank amount. Two test-only entries render it, defined once where both test modules can import them:

- `SAMPLE`: per cycle, `{yyyy}/sample_{yyyy}.csv`.
- `SAMPLE_UNDATED`: an undated file, `data.fec.gov/sample.csv`.

Their names are not in `FecFile`; the tests `cast`. `FecFile` is not widened for them.

**Tests to add** are listed as acceptance criteria in §3. While iterating, run only the touched files through `task`; the pre-commit hook runs the full suite once at commit.

### 2.8 Docs, in the same PR

- **`docs/specs/fundlens-every-fec-dollar-project-spec.md` §3**, the Formats bullet: a CSV's header row must equal the catalogue's columns exactly, checked at extract and again at transform; the dialect FEC serves (unquoted header, every field quoted, LF, no BOM); both formats are rewritten as UTF-8 at transform. The URL-shapes bullet: say the pattern is the entry's `url_pattern`, and drop "where NEU-2138's ticket text names two", now resolved. Add that FEC rewrites some historical CSVs daily, so a historical cycle's CSVs download again on re-extract.
- **v1 project spec §3.4**: a second bronze line, `bronze/cycle=2026/<file>/2026-11-02.csv`, with "a CSV file as downloaded; an undated file is kept under each cycle extracted", and "historical cycles download once" qualified: zips, and CSVs FEC does not rewrite. **§5.3**: "registers the bronze zips" becomes the bronze files, zip or CSV.
- **`CONTEXT.md`**: "Undated file" was added at planning and ships in this PR.
- No ADR: nothing here is hard to reverse, and ADR-0002 already covers bronze.

## 3. Acceptance criteria

The ticket's three Definition-of-done items are the first, sixth and last below, made specific.

- [ ] `tests/integration/test_extract.py`, for `SAMPLE` and for `SAMPLE_UNDATED`, through `extract_file` against the fake FEC and the test bucket:
  - the first extract downloads once and writes `bronze/cycle=<c>/<name>/<date>.csv`, with the source's `Last-Modified` and size as object metadata, and the object's bytes are the served bytes exactly;
  - a second extract of an unchanged source makes no GET and writes nothing;
  - a source with a new `Last-Modified`, extracted on a later date, is downloaded again to a new key;
  - a response that is not the catalogued CSV is rejected with `DownloadError` after the retries, leaving nothing in bronze and no `.part` file: an HTML page, a zip, and a CSV whose header has one column renamed.
- [ ] The same file: `SAMPLE_UNDATED` extracted for 2024 and then for 2026 requests the same URL path both times and writes one bronze object under each cycle; a second extract of 2024 downloads nothing.
- [ ] The same file: the current cycle's CSV stays on local disk after extract and a historical cycle's does not, as for zips.
- [ ] `tests/unit/test_fec_files.py`: `url()` for each of the three URL shapes and for a zip with no pattern; `__post_init__` refuses each invalid entry of §2.1; `header()` and `header_file` for a CSV entry; `read_csv_header` on a CSV, an empty file, a zip's bytes and a file with no newline in its first 64 KiB.
- [ ] `tests/unit/test_paths.py`: `bronze_csv`'s key, and `download_date_of` for a `.zip` and a `.csv` key.
- [ ] `tests/integration/test_transform.py`: with the sample in bronze (put there by `extract_file`), the fetch and register functions expose it as a view named for the entry, and a test model (SQL the test runs as the runner runs a silver model, `CREATE TABLE … AS SELECT … FROM sample`) reads it by that name. The test asserts both rows, the value holding a comma and a quote intact, the blank amount NULL, and the amount column's type `DECIMAL(14,2)`.
- [ ] The same file or a unit test: a bronze CSV whose header row differs from the entry's columns raises `ValueError` naming the bronze key before anything is read; a CSV holding a latin-1 byte and a NUL reads with the byte decoded and the NUL gone.
- [ ] A test of `gold`'s source dates, or of `download_date_of` where `_source_dates` calls it, shows a `.csv` bronze key giving a bare ISO date.
- [ ] `tests/unit/test_fec_fixture.py`: the sample renders to FEC's layout (unquoted header, every field quoted, a quote doubled, LF), and a fixture file whose header row is not the entry's columns, or with a short row, raises `ValueError`.
- [ ] `task fec:headers -- --check` still passes: the six zip entries are checked and nothing else is fetched.
- [ ] The existing zip tests in `test_extract.py`, `test_transform.py`, `test_fec_files.py`, `test_fec_fixture.py` and `test_paths.py` pass with no edit to their bodies. Renaming an imported function is the only allowed change.
- [ ] `CATALOGUE` still holds exactly `cm`, `cn`, `ccl`, `indiv`, `pas2`, `oth`, and `task typecheck` and `task lint` (or the hook's equivalents) are clean.
- [ ] The doc amendments of §2.8 are in the PR.

No new test may sit near the top of the slowest-tests list the hook prints. The new integration tests use a two-row file and need no seat calendar, silver build or seeded database.

## 4. Out of scope

- **Any real CSV file's catalogue entry, fixture or silver model**: NEU-2142, NEU-2164, NEU-2174. Their column names and types are theirs to read from the files; §5 is a starting point, not the record.
- **`weball` and `webk` in `refresh_headers`.** They are zips with no header file on FEC's site, so `task fec:headers` would 404 on them. NEU-2142 vendors their headers and decides how the refresher skips them; this ticket skips only entries with no `header_file`.
- **Which cycles' rows an undated file holds**, and what a cycle's silver model takes from its copy: NEU-2173's measurement.
- **Sharing one download of an undated file across cycles**, in a backfill or otherwise. Each cycle downloads its own copy; the two files are 2 MB and 0.3 MB.
- **A content-hash change check** (§1.1).
- **A `catalogue` parameter** on `extract()` or `transform()` (§1.1).

A consequence to know, not a task: a historical cycle's copy of an undated file is as old as that cycle's last extract, as its zips are. A row FEC adds later for that cycle appears when the cycle is extracted again.

## 5. What FEC served on 2026-11-18

Read with `curl` from `https://www.fec.gov/files/bulk-downloads/`. Every URL answers 302 to the same S3 bucket as the zips, then 200 with `Last-Modified`, `Content-Length` and `Content-Type: text/csv`.

| File | URL below the base | Bytes | Lines | `Last-Modified` | Header columns |
|---|---|---|---|---|---|
| `committee_summary` 2024 | `2024/committee_summary_2024.csv` | 7,862,137 | 14,067 | 18 Nov 2026 10:12:49 | 92 |
| `committee_summary` 2008 | `2008/committee_summary_2008.csv` | 4,930,042 | not read | 18 Nov 2026 10:12:37 | 92 |
| `independent_expenditure` 2024 | `2024/independent_expenditure_2024.csv` | 19,534,174 | 73,450 | 18 Nov 2026 10:13:11 | 23 |
| `independent_expenditure` 2010 | `2010/independent_expenditure_2010.csv` | 11,437,199 | 48,329 | not read | 23 |
| `ElectioneeringComm` 2024 | `2024/ElectioneeringComm_2024.csv` | 18,370 | 70 | 18 Nov 2026 10:11:55 | 19 |
| `CommunicationCosts` 2024 | `2024/CommunicationCosts_2024.csv` | 237,322 | 780 | 18 Nov 2026 10:11:46 | 25 |
| `leadership` 2024 | `data.fec.gov/leadership2024.csv` | 119,995 | 833 | 18 Nov 2026 10:10:37 | 8 |
| `leadership` 2010 | `data.fec.gov/leadership2010.csv` | 61,357 | not read | 2 Jan 2025 10:13:34 | 8 |
| `lobbyist` | `data.fec.gov/lobbyist.csv` | 2,042,059 | 14,156 | 18 Nov 2026 10:10:42 | 5 |
| `lobbyist_bundle` | `data.fec.gov/lobbyist_bundle.csv` | 347,542 | 1,930 | 18 Nov 2026 10:10:45 | 11 |

- **Layout.** Each file's first line is an unquoted header row. Every data field is double-quoted, a blank one as `""`. Line endings are LF. There is no BOM.
- **Content of the eight files downloaded whole** (every row above with a line count): valid UTF-8 and in fact pure ASCII, no NUL byte, no CR, no line that does not start and end with a quote (so no newline inside a field), and no quote character inside any field. Other cycles were not read.
- **Headers across cycles.** The first line is byte-identical in every cycle FEC publishes for all five per-cycle files: `committee_summary` 2008–2026, and `independent_expenditure`, `ElectioneeringComm`, `CommunicationCosts` and `leadership` 2010–2026, even years.
- **Header case varies by file:** `committee_summary` mixes (`Link_Image`, `CMTE_ID`), `independent_expenditure` is lower case (`cand_id`), `leadership` is `Committee_Id`. The catalogue's column names are the header's, character for character.
- **Rewrites.** `committee_summary_2008.csv` carried that day's `Last-Modified`; `leadership2010.csv` carried 2 January 2025. So FEC rewrites some historical CSVs daily and not others.
- **Values the file tickets will meet:** dates as `20241016` in some files and `31-OCT-24` in others; amounts with and without decimals (`9000`, `326152.45`); a leading space inside a quoted name (`" Go America PAC"`).
