# NEU-2268: restore pipeline state from session snapshots, then run the suite in parallel

Ticket: [NEU-2268](https://linear.app/neuroticsasquatch/issue/NEU-2268). Follows NEU-2267 (PR #124).
One PR, two stages, in this order: snapshots first, pytest-xdist on top.

## Why

The pre-commit hook runs the whole pytest suite on every backend commit, as CI does. After
NEU-2267 that is **857 tests in 199 s** (PR #124's hook run, 2026-11-10). Two costs remain:

1. **Tests that change pipeline state still build it themselves.** From PR #124's slowest 25:
   `test_adjudicate` spends 2.0–2.8 s of setup per test on a transform and a resolve, the
   `test_resolve` tests on `transformed` spend 1.0–1.3 s each on a transform, and `test_load`
   tests open with a `transform()` of the stock bronze. Estimated saving from restoring instead:
   35–45 s (estimated from that list, not measured).
2. **The suite runs on one process.** Most of the remaining time is a long tail of tests under
   2 s that no fixture change touches. The dev container has 14 cores and 18 GB.

## Starting point (what PR #124 shipped)

- `tests/integration/conftest.py`: `scratch_database(template=…)`, session `migrated_template`,
  `cli_pointed_at(conninfo=…, data_dir=…, bucket=…)`, session `published`,
  `TEST_BUCKET = "fundlens-test"`, `empty_store(bucket)`.
- `tests/integration/test_validate.py`: a module-scoped `snapshot` (own bucket
  `fundlens-test-snapshot`, database and data dir) and a per-test `resolved` that restores it:
  `copytree` of the data dir, `copy_object` of every key into the test bucket, and the test's
  database dropped and recreated `TEMPLATE` the snapshot's. This is the pattern to generalize.
- CI runs a bare `uv run pytest` (shared `python.yml@v1`), not `task test`. Anything CI must
  honour lives in `pyproject.toml`.

## Stage 1: snapshot and restore

### The mechanism, in `tests/integration/conftest.py`

- `Snapshot` (frozen dataclass): `data_dir: Path`, `database: str` (a database name nothing is
  connected to), `store: R2`. Moved from `test_validate.py`.
- `restore(snapshot, *, store, data_dir, conninfo)`: what `test_validate.resolved` does today,
  as one function. Copies the data dir, copies every object server-side, and makes the test's
  database over as a copy of the snapshot's.
- A builder helper so each rung is a few lines: given a rung name and an optional parent
  snapshot, it empties the rung's bucket, creates a database (from `migrated_template`, or from
  the parent's database), restores the parent into it if there is one, points the CLI at it
  with `cli_pointed_at`, and yields the `MonkeyPatch` for the rung's own steps.

### Three rungs, session-scoped, each built from the one before

| Fixture | State | Built by |
|---|---|---|
| `transformed_snapshot` | bronze, seats report, `transform` as `BUILD` | from `migrated_template` |
| `resolved_snapshot` | plus `resolve --full --build-id MODEL` under `MEMORY_LIMIT`, no verdicts | restoring `transformed_snapshot` |
| `validated_snapshot` | plus `adjudicate` with the fake model, then `resolve --full --build-id AGAIN` with the fixture overrides and release name | restoring `resolved_snapshot` |

Each rung has its own bucket (`fundlens-test-snapshot-<rung>`, plus the worker suffix in
stage 2), database and data dir, and is built lazily, so a run that needs none builds none.
`validated_snapshot` replaces `test_validate.py`'s module-scoped `snapshot`; its end state must
equal what that fixture produces today (test_validate passes unchanged).

Shared constants and helpers the rungs need (`BUILD`, `MODEL`, `AGAIN`, `MEMORY_LIMIT`,
`FIXTURE_OVERRIDES`, `put_bronze`, `seats_report`, `transform`, `resolve`) may stay where they
are and be imported inside the fixture bodies, as `published` does, or move to conftest. Either
is fine; no import cycle at module import time.

### Per-test fixtures

- `transformed` (moves to conftest; test_resolve, test_adjudicate and test_validate stop
  importing it from `test_resolve`): restores `transformed_snapshot` into the test's `store`,
  `cli_env` and `migrated_db`, then sets `DUCKDB_MEMORY_LIMIT=MEMORY_LIMIT`. Same contract as
  today: returns the `DATA_DIR`.
- `test_adjudicate.resolved`: restores `resolved_snapshot` instead of `transformed` + `resolve`.
- `test_validate.resolved`: restores `validated_snapshot`, then `resolved_env`.
- `test_load`: tests that open with `put_bronze(store)` (stock texts) + `seats_report()` +
  `transform()` take `transformed` instead. `test_load_of_a_resolved_build_builds_the_donor_tables`
  restores `resolved_snapshot` if its opening is the stock transform + resolve.

### What a restored state carries, and what to verify

A restore is a full copy, so these come across and must be right:

- **R2 markers and build IDs**: copied with the objects. A test that runs a later build uses a
  later ID (`AGAIN`, `NEWER`), as now.
- **The donor-id sequence and `app` tables the crosswalk writes**: `CREATE DATABASE … TEMPLATE`
  copies sequences with their position and all `app` rows. Tests that assert donor ids
  (`test_resolve_full_gives_each_cluster_one_donor_id_and_a_rerun_changes_none` and neighbours)
  run their own first resolve on a restored *transformed* state, where no id has been drawn.
- **Run records and logs**: a restored state has no CLI output. A test that asserts the output,
  log lines or marker *of the step the snapshot ran* keeps running that step itself and is a
  listed exception.
- **Template databases need no open connections**: every builder closes its connections before
  yielding; `Snapshot.database` is only ever a `TEMPLATE` source.
- **Paths**: nothing in the state may hold the snapshot's own `DATA_DIR` or bucket name. This
  already holds for the deepest rung (test_validate restores across both today); if a shallower
  rung surprises, fix the restore, not the test.

### The rule, and its exceptions

**No fixture or test opens by running `transform` or `resolve` over the stock fixture bronze
under default settings. That state comes from a restore.** Calls that stay, each to be listed in
the PR with its reason:

- the step is what the test is about (test_resolve's `resolve` calls; test_load's `load`);
- altered bronze, or non-default settings or build IDs for the opening step;
- a second or later run in the same test;
- a test asserting the output, logs or markers of the opening step itself.

**Not converted, deliberately:** `test_publish.py` (its builds are `B0`–`B3` and `BUILD` equals
`B0`, so a snapshot means renumbering its builds; no loaded rung in this ticket),
`test_transform.py` (transform is its subject; its read-only tests already share
`fixture_silver`), `test_api_donors.py` (already once per module), and the module-scoped
`fixture_resolved` / `fixture_silver` / session `published` read-only fixtures (they may be
rebased onto the snapshots if that is simpler, but need not be).

### Measure

After stage 1, run the suite once (through the hook's `task test`) and record wall-clock time
and the slowest 25. This is the "after snapshots, before xdist" figure the PR quotes.

## Stage 2: pytest-xdist

xdist is committed, not conditional. The only way out is the reliability bar below.

### Configuration

- Add `pytest-xdist` as a dev dependency (`task deps:add-dev -- pytest-xdist`, `task build`).
- `pyproject.toml` `addopts`: `--durations=25 -n auto --maxprocesses=8 --dist loadfile`.
  In `pyproject.toml` because CI runs bare `pytest`; the hook and CI stay identical.
  CI gets one worker per runner core; the dev box gets 8 and leaves room for Postgres and MinIO.
- `task test -- -n0` is the serial run for debugging. Say so in the Taskfile `desc`.
- Update the "about five minutes" comment in `.pre-commit-config.yaml` with the measured time.

### Each worker owns what it touches

- **Buckets, stable per worker, never deleted:** `fundlens-test-<worker>` and
  `fundlens-test-snapshot-<rung>-<worker>`, where `<worker>` is `PYTEST_XDIST_WORKER` (`gw0`…);
  no suffix when serial. Created if missing and emptied, as `empty_store` does now. `TEST_BUCKET`
  becomes a function (or a per-process constant computed at import) and its three importers
  (`test_seed`, `test_seats`, `test_extract`) follow.
- **Databases** are already uuid-named per test and per snapshot. Nothing to change.
- **Snapshots and module fixtures** are per worker. `--dist loadfile` keeps a file on one
  worker, so a module-scoped fixture builds once and only the workers that run test_resolve,
  test_adjudicate, test_load or test_validate build snapshots. No locks, no state shared
  between processes.
- **Data dirs** come from `tmp_path` / `tmp_path_factory`, which xdist already separates.
- Check for anything else shared: tests that touch the dev buckets (`fundlens-data`,
  `fundlens-public`) or the dev database must only read them. Fix any that write.

Two concurrent pytest *runs* still collide on the bucket names. The "one test process at a
time" rule stays, which also keeps the memory budget below true.

### DuckDB caps

`point_cli_at` sets `DUCKDB_MEMORY_LIMIT=1GB` and `DUCKDB_THREADS=2` for every CLI-driven test,
serial or parallel (one behaviour, not two). A test or fixture that sets its own
(`MEMORY_LIMIT = "256MB"`) still wins because it sets it afterwards. Budget: 8 workers ≤ 8 GB
and 16 threads. Any test that asserts an uncapped default must be adjusted to set what it needs.
DuckDB connections the tests open directly for reading are small and stay as they are.

### Timing tests

`test_search_ranks_trigram_matches_fast` (< 50 ms) and
`test_a_page_is_answered_in_under_100_ms_at_p95` keep their bounds. Each measures up to three
times and passes if any attempt meets the bound: a regression fails all three, a neighbouring
worker's burst does not. One small shared helper; no separate serial pass.

### Reliability bar

The full suite passes through the hook **three times in a row** with no failure. The ticket's
definition of done asks for this, so those runs are authorized (the first is the commit's own
hook run; the other two are `pre-commit run test --all-files` or `task test`, one at a time).
A failure that only happens in parallel is a bug to fix (shared state found late), not to retry
past. If the bar cannot be met, revert stage 2, ship stage 1 alone, and say in the PR what
flaked and why.

## Acceptance criteria

- [ ] `conftest.py` has `Snapshot`, `restore` and the three session snapshots; `test_validate.py`
      has no snapshot or restore code of its own and its tests pass unchanged.
- [ ] `transformed`, `test_adjudicate.resolved` and `test_validate.resolved` restore a snapshot.
      No fixture or test in `test_resolve.py`, `test_adjudicate.py`, `test_validate.py` or
      `test_load.py` opens with `transform`/`resolve` over stock bronze under default settings.
- [ ] The PR lists every remaining `transform(` and `resolve(` call in those four modules with
      its reason, and names each converted test and that it mutates state.
- [ ] In the slowest-25 list, no converted test shows more than 1 s of setup, apart from the
      first test on each worker that builds a snapshot.
- [ ] `pyproject.toml` runs the suite with `-n auto --maxprocesses=8 --dist loadfile`; a bare
      `pytest` and `task test` both run in parallel, and `task test -- -n0` runs serially and
      passes.
- [ ] Each worker uses its own buckets; `grep -rn '"fundlens-test' tests` finds the name built in
      one place only.
- [ ] `point_cli_at` sets the 1 GB / 2-thread caps.
- [ ] The two timing tests use best-of-three with their bounds unchanged.
- [ ] Three consecutive full hook runs pass. The PR quotes all three times.
- [ ] The PR quotes wall-clock time and the slowest 25 at three points: PR #124's 199 s, after
      stage 1, after stage 2. CI green, with its pytest step time quoted.

## Out of scope

- A loaded (gold_build) rung and converting `test_publish.py`.
- Sharing snapshots across workers; unique-per-run buckets; retiring the one-run-at-a-time rule.
- Changing what any test asserts, deleting tests, or moving tests out of the hook.
- The shared CI workflow, the hook's path filters, the frontend suite.
- No ADR and no `CONTEXT.md` change: this is test infrastructure, reversible, with no new
  domain terms.
