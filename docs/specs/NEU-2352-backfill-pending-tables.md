# NEU-2352 — Backfill-pending tables: gold load and the dataset snapshot tolerate a live build that predates a new silver table

**Ticket:** [NEU-2352](https://linear.app/neuroticsasquatch/issue/NEU-2352) · **Milestone:** M1 Reported totals · **Project:** P-NEU-107 "fundlens: every FEC dollar"
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §2 ("Older builds") and §8 (public dataset), read with the v1 spec §3.4 (storage layout, live builds), §5.5 (load) and §9 (the snapshot and its manifest) · **Glossary:** `CONTEXT.md` (Backfill-pending table, added at planning; Build, Live build, Snapshot) · **ADRs:** 0002 (R2 is the source of truth), 0007 (gold loads by DuckDB → CSV → `COPY`)
**Blocked by:** NEU-2137 (merged, PR #184). **Blocks:** NEU-2143 (silver `reported_total`), NEU-2144 (gold reported fields), NEU-2180 (the backfill, which empties the list).

Planned 2026-11-18. `/implementit NEU-2352` produces **one PR**: the list in `paths.py`, the two readers (`load/gold.py`, `publish/dataset.py`), a schema reader in `publish/dataset_schema.py`, the `docs_dir` argument through the CLI, tests, and the doc amendments in §2.7. It adds **no silver table** and leaves the list **empty**. Where the Linear ticket and this spec differ, this spec wins (§1.2).

## 1. What and why

`fundlens load` rebuilds all of gold from every cycle's live build, and the dataset snapshot copies every cycle's live build. Both refuse a build that lacks a silver table they read: `_require_inputs` raises `FileNotFoundError` for any table of `INPUTS`, and `_silver_copies` raises `BuildNotReady` for any table of `DATASET_TABLES`.

This project adds silver tables one milestone at a time and rebuilds only 2024 until the end-of-project backfill (NEU-2180). So from the day `reported_total` is a gold input and a dataset table, every other cycle's live build lacks it, and the load and the snapshot fail, and with them the weekly run.

The project spec's rule (§2, "Older builds"): a named list of tables may be absent from a live build, and a cycle whose build lacks one reads as having no rows of it. This ticket builds that list and teaches the two readers to honour it. Each silver ticket then adds its table to the list in the PR that creates the table, and NEU-2180 empties the list once every cycle is rebuilt.

### 1.1 Decisions this spec pins (grilled 2026-11-18)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| The term and the list | **"Backfill-pending table"** in `CONTEXT.md`; in code `BACKFILL_PENDING: frozenset[SilverTable]` in `fundlens/paths.py`, beside `SilverTable`. | The name says why a build may lack the table and when the entry leaves the list. Both readers already import `paths`. Rejected: "optional table" and "absent table", which read as a permanent property of the table. |
| Columns of `silver.<table>` when no build in the load has it | **From the committed dataset schema**, `docs/dataset/schema/<table>.json`: each property's name and `x-duckdb-type`, in file order. `load` gains a `docs_dir` argument (`DATASET_DOCS_DIR`). | The schema is already committed, shipped in the image, and regenerated from the fixture's Parquet by `tests/integration/test_dataset.py`, so it cannot drift from what transform writes. Rejected: declaring each table's columns in the list, a second hand-written copy; refusing a load in which no build has the table, which fails a manual load of an older build for no reason the operator can fix without a re-transform. |
| How the tests list a table | **`independent_expenditure` stands in**, put on the list by `monkeypatch.setattr(paths, "BACKFILL_PENDING", …)`, and its partition removed from a fixture build. The load test asserts the cycle's independent-expenditure figures are **0**, not NULL. | The list is empty in production and `SilverTable` and `GoldTable` are closed, so a test must use a real table. Every existing gold figure coalesces to 0; NULL for `reported_*` is NEU-2144's to assert. Rejected: asserting only on the DuckDB view, which checks no end-to-end result; a test-only gold model with a LEFT JOIN, which no production SQL resembles. |

Not user decisions, pinned so the diff is predictable:

- **One rule for every build.** The build being loaded is treated as every other cycle's live build is: a backfill-pending table it lacks reads as no rows. Exempting it would need a second code path for a case (a manual load of an older build) that is harmless.
- **Absent means R2 holds nothing under the partition's prefix.** R2 decides, never the local cache (ADR-0002). A partition that holds objects but no Parquet, or a `contribution` partition mid-rewrite, is an error exactly as today, listed or not.
- **Every backfill-pending table is a dataset table and is not a resolved table.** The first gives it a committed schema (project spec §8 already requires a new table to join the dataset in its silver PR). The second keeps `donor_id` handling out of the empty view. A unit test holds both.
- **The readers read `paths.BACKFILL_PENDING` at call time**, as an attribute of the module, never through `from fundlens.paths import BACKFILL_PENDING`: a test replaces the attribute, and an imported name would keep the old value.
- **A skipped partition is logged**, one INFO line per cycle and table, by each reader. Nothing else records it: not the `loaded` marker, not `gold.meta`.
- **Transform is unchanged.** It already writes one Parquet part per model, zero rows included, and already gives a model an empty table for a file FEC does not publish for the cycle (`register_unpublished`). This ticket adds the test that pins it.

### 1.2 Where the ticket text is corrected

- The DoD's first box said the older cycle's rows "read the table's figures as NULL". With `independent_expenditure` standing in, they read as 0, as a cycle with no independent expenditures does. The Linear DoD was reworded at planning.
- The ticket does not say where the empty view's column types come from. They come from the dataset schema, so `load` and its CLI command gain `docs_dir`.
- The ticket says `_require_inputs` "skips a listed table a build lacks". It also gains an explicit error for a partition that holds objects but no Parquet, for every table: today that case surfaces as a DuckDB error when the view is created.
- The ticket does not mention `docs/dataset/README.md`. It gets one sentence (§2.7), because a manifest table without files for every cycle is a change to what a dataset reader may assume.

## 2. The deliverables, file by file

### 2.1 `src/fundlens/paths.py`

```python
# The backfill-pending tables (CONTEXT.md): the silver tables a live build may lack, because it
# was transformed before the table existed. A cycle whose build lacks one reads as having no rows
# of it, in gold (`load.gold`) and in a dataset snapshot (`publish.dataset`). A silver ticket adds
# its table here in the PR that creates it; NEU-2180's backfill rebuilds every cycle and empties
# this again. Each must be a dataset table and not a resolved one.
BACKFILL_PENDING: frozenset[SilverTable] = frozenset()
```

Nothing else in the module changes.

### 2.2 `src/fundlens/publish/dataset_schema.py`

A reader for the committed schemas, the inverse of `columns(parquet)`:

```python
def committed_columns(docs_dir: Path, table: str) -> list[tuple[str, str]]:
    """`table`'s columns as its committed schema records them: each name with its DuckDB type,
    in the file's order. Raises `FileNotFoundError` when `docs_dir` holds no schema for it."""
```

It reads `docs_dir / SCHEMA_DIR / f"{table}.json"` and returns `(name, properties[name]["x-duckdb-type"])` for each property, in order.

### 2.3 `src/fundlens/load/gold.py`

- `_require_inputs`: for a table whose prefix has no keys in R2, when the table is in `paths.BACKFILL_PENDING`, log `build <b> of <cycle> has no silver <table>: backfill-pending, read as no rows` and leave the table out of the returned mapping. Any other table still raises today's `FileNotFoundError` ("no silver <table> partition for build …"), word for word.
- `_require_inputs`: a prefix with keys but none ending `.parquet` raises `FileNotFoundError` naming the table, the build and the command that writes it, for every table.
- `load`: gains `docs_dir: Path`. `local_dirs` keeps an entry for every table of `INPUTS`, with an empty list when no build has it.
- `_register_silver`: gains `docs_dir`. A table with no partitions gets
  `CREATE VIEW silver.<table> AS SELECT CAST(NULL AS <type>) AS "<name>", … WHERE false`
  from `committed_columns(docs_dir, table)`. A table with at least one partition is registered exactly as today, over the partitions that exist (`union_by_name`), so gold SQL reads the other cycles' rows and none for a cycle whose build lacks it.
- Module docstring, `_require_inputs`, `_register_silver` and `load` docstrings say the above.

The import of `publish.dataset_schema` into `load.gold` adds no cycle: `dataset_schema` imports only `transform.runner`.

### 2.4 `src/fundlens/cli.py`

The `load` command passes `docs_dir=settings.dataset_docs_dir` to `gold_load.load` (its one caller, which `fundlens run`'s load step also goes through).

### 2.5 `src/fundlens/publish/dataset.py`

- `_silver_copies`: for a table and cycle whose partition lists no objects at all, when the table is in `paths.BACKFILL_PENDING`, log `the live build <b> of <cycle> has no <table>: backfill-pending, not in the snapshot` and go on to the next cycle. Otherwise today's checks stand unchanged: the rewrite sentinel, then "has no <table>" for a partition with no Parquet.
- `_silver_tables` needs no change: it already gives every table of `DATASET_TABLES` a manifest entry, so a table with files for some cycles lists those, and a table with none lists `rows: 0, files: []`. `Manifest.cycles` still names every live cycle.
- Module docstring, `_silver_copies` and `snapshot` docstrings, and `BuildNotReady`'s, say that a backfill-pending table may be missing from a cycle.

`publish_docs`, `_refresh_latest`, `_retain`, `GET /v1/dataset` (`api/dataset.py`) and the dataset page need no change: the API groups whatever files a table has into parts, and the page already shows a dash for a table with no part for the chosen cycle.

### 2.6 Tests

Run only the files touched while iterating; the pre-commit hook runs the full suite. Each new integration test is read off the hook's `--durations` list after the commit: three gold loads and four small snapshots are added, and one near the top of that list is a defect.

**`tests/unit/test_paths.py`** (or a new `tests/unit/test_backfill_pending.py` if importing `load.gold` and `publish.dataset` into the paths test is unwelcome):

- `paths.BACKFILL_PENDING` is a subset of `DATASET_TABLES` and disjoint from `load.gold.RESOLVED`. Vacuous while the list is empty; it binds the day NEU-2143 adds to it.

**`tests/unit/test_dataset_schema.py`:**

- For every table of `MANIFEST_TABLES`, `committed_columns(docs/dataset, table)` gives a non-empty list, and a DuckDB view built from it as §2.3 builds one `DESCRIBE`s to the same names and types and holds no rows.
- A table with no schema file raises `FileNotFoundError`.

**`tests/unit/test_api_dataset.py`:**

- A manifest table with `rows=0, files=[]` summarises to `files: 0, bytes: 0, parts: []`.

**`tests/integration/test_multi_cycle.py`**, which owns the two-cycle state (`two_cycles`: 2024 and 1998, both live as build `BUILD`). Only 2024's `independent_expenditure` partition holds rows; 1998's is a zero-row part.

- *Transform writes an empty partition.* Read-only on `two_cycles`: the 1998 build's `independent_expenditure` partition is one Parquet part with zero rows whose column names and types equal the 2024 part's. This is the pin for "a silver model always writes its partition, empty for a cycle with no rows of its source".
- *Load, listed* (each case restores `two_cycles` into the test's own bucket, `DATA_DIR` and database, as `test_publishing_a_new_2024_build_leaves_1998_live` does; lists `independent_expenditure`; deletes the partition from R2 only, leaving the local cache's copy; then `fundlens load --cycle 1998 --build-id BUILD`). Parametrized over which builds lack the partition:
  - **2024 lacks it:** exit 0; every 2024 `candidate_cycle` row has `ie_support = ie_oppose = 0`, every 2024 `committee_cycle` row `ie_total = 0`, and no 2024 `race_top_committee` row comes from an independent expenditure.
  - **1998 lacks it:** exit 0; 2024's `ie_support`, `ie_oppose` and `ie_total` equal the live `gold` schema's, row for row.
  - **Both lack it:** exit 0 through the schema-built empty view; every row's three figures are 0.
- *Load, not listed.* The same state with 2024's partition deleted and the list left empty: exit 1, the output holds `no silver independent_expenditure partition for build <BUILD> of 2024`, and no `gold_build` schema exists.
- *Load, listed but broken.* The list names the table and 2024's partition holds one object that is not Parquet: exit 1 with the new "holds no Parquet" error.
- *Snapshot* (no restore: `R2.list_objects` is patched to return nothing for the hidden prefix, as `test_a_build_lacking_its_last_table_copies_nothing` does, against a copy of the `two_cycles` database and a public bucket of the test's own):
  - **Listed, 1998 hidden:** the snapshot succeeds; `manifest.cycles` names both cycles; `tables["independent_expenditure"]` has only files under `independent_expenditure/cycle=2024/` and 2024's row count; every other dataset table has files under both cycles.
  - **Listed, both hidden:** the snapshot succeeds and the table's entry is `rows: 0, files: []`.
  - **Not listed, 1998 hidden:** `BuildNotReady` matching `has no independent_expenditure`, and the public bucket holds nothing under the snapshot's directory.
  - **Listed, the partition holding one object that is not Parquet:** `BuildNotReady`, nothing copied.

### 2.7 Docs, in the same PR

- **Project spec §2**, the "Older builds" row: name the term and the list, "`BACKFILL_PENDING` in `fundlens/paths.py` (NEU-2352)", and that the empty view's columns come from the dataset schema. **§8**: "NEU-2352's list of tables a live build may lack" becomes "`paths.BACKFILL_PENDING`".
- **`CONTEXT.md`**: the "Backfill-pending table" entry, written at planning (already in the working tree).
- **`docs/dataset/README.md`**, where it describes the manifest: one sentence saying a table added to the dataset recently may have no files for a cycle not yet rebuilt, and that the manifest lists exactly the files that exist. No `CHANGELOG.md` entry: no schema changes.
- No ADR: project spec §2 records the decision and what it rejected.

## 3. Acceptance criteria

The ticket's Definition of done, as reworded:

- [ ] An integration test loads gold for two fixture cycles where only one build has a listed table: the load succeeds, and the cycle whose build lacks it reads as a cycle with no rows of the table (0 for the stand-in's figures).
- [ ] The same test with the table off the list fails with today's `FileNotFoundError`.
- [ ] A dataset test snapshots the same two builds: the snapshot succeeds and `manifest.json` lists the table with one cycle's files only; with the table off the list it raises `BuildNotReady`.
- [ ] The project spec's §2 names this ticket and the list's location in code.

And from this spec:

- [ ] A load in which no build has a listed table succeeds, `silver.<table>` built empty from `docs/dataset/schema/<table>.json`.
- [ ] A listed table whose partition holds objects but no Parquet fails the load and the snapshot.
- [ ] A test pins the 1998 fixture build's zero-row `independent_expenditure` part to the 2024 part's columns and types.
- [ ] `paths.BACKFILL_PENDING` is empty at merge, and a unit test holds it to dataset tables that are not resolved tables.
- [ ] `task typecheck` and the pre-commit hook pass, and no new test is near the top of the hook's slowest-tests list.

## 4. Out of scope

- Any silver table, and any entry in the list: NEU-2143 adds the first.
- Emptying the list: NEU-2180, once every cycle is rebuilt.
- The API's per-cycle silver readers (`api/itemized.py`). None reads a backfill-pending table today; an API ticket that reads one per cycle (the itemized spending list, the outside-spending lists) decides what a cycle whose build lacks it answers.
- Telling "not rebuilt yet" from "none" on a page or in gold. Project spec §2 decided a missing table reads as no rows; a gold ticket that wants NULL rather than 0 for such a cycle gets it from its own LEFT JOIN, as NEU-2144's `reported_*` fields do.
- `resolve`, `validate`, `seats` and `publish`'s prune: none reads a table this project adds.
- Amending the v1 spec: the "every FEC dollar" spec is where this project's additions to v1 §3.4 and §9 are recorded.
