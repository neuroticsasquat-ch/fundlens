# NEU-2325 — `resolve --full` drops Splink's scratch as it goes, keeps its model, and re-clusters one component at a time

**Ticket:** [NEU-2325](https://linear.app/neuroticsasquatch/issue/NEU-2325) · **Milestone:** M4 Backfill and independent expenditures
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §6.3, §6.4, §6.10, §5.1 (amended by this spec, §7) · **ADRs:** 0010 (re-clustering; its algorithm is unchanged)
**Related:** **blocks** NEU-2060 (backfill runbook, step 9: its rerun measures this fix); NEU-2054 (thresholds; owns any change to what the model trains on); NEU-2122 (`docs/specs/NEU-2122-recluster-chains.md`).

Planned 2026-11-16. `/implementit NEU-2325` implements straight from this file. One PR. No manual steps of its own: the all-cycle rerun is NEU-2060's step 9.

## 1. What and why

`fundlens resolve --full` over all 24 cycles (29,213,828 contributor keys) cannot finish on the box. NEU-2060's step 9 ran it on prod on 2026-11-16 as `20261116T022944Z` from `62a47eb` with `DUCKDB_MEMORY_LIMIT=32GB`. It stopped in `recluster` after 3h22m with `No space left on device`.

- **Disk.** The working file `resolve.duckdb` grew to 254,181,650,432 bytes. Nearly all of it was Splink scratch the run never reads again: three EM sessions' `__splink__blocked_id_pairs_*` and `__splink__df_comparison_vectors_*` tables (2,636,580,964 + 621,859,329 + 55,991,435 pairs), plus `__splink__df_predict_*` (a copy of `edge`) and `__splink__df_clustered_with_input_data_*` (a copy of `component`). `resolve_full` drops Splink's tables only in `save`, after `recluster`, `overrides` and `adjudications`.
- **Memory.** `pipeline` read 40.00 GiB, its `mem_limit`, three minutes into `recluster`. It was not killed.
- **Lost training.** The model is written in `save`, and the next run deletes the working file, so the 8,420 s of training were lost.

This ticket makes four changes:

1. Splink's scratch is dropped as soon as the run has used it (§3).
2. The model goes to R2 right after `train`, and `resolve --full --model VERSION` resolves with a saved model without training (§4).
3. A model counts as the **live model** only once its run has finished (§4.3).
4. `recluster` holds one component in Python at a time and logs what it found (§5).

### 1.1 Decisions this spec pins (grilled 2026-11-16)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| How the memory fix is chosen | By reading the code, not by a new measurement: stream the offending components, and log enough for step 9's rerun to measure. The PR says so plainly. | The ticket said "choose by measuring the 2024 fixture-scale run". The failed working file was deleted at 14:45Z, there is no all-cycle data off prod, and 2024 alone (7,339 offending components, 12 s) says little about 29M keys. Measuring first on prod risks another failed 3-hour run and a second ticket. |
| A resolve-specific DuckDB limit | **Not added.** | A second setting and Coolify variable that may never be needed once the scratch is gone. If the rerun still peaks near 40 GiB, step 9 can pass a lower `DUCKDB_MEMORY_LIMIT` to that one command; §5.3's log lines say whether Python or DuckDB holds the memory. |
| What the 40.00 GiB was | **Not known**, and the spec does not claim to know. | The sampler reads `docker stats`, which counts active file cache; a run at exactly the limit, not killed, while writing a 254 GB file, fits reclaimable page cache as well as Python dicts or the buffer pool. `docs/capacity.md` records it as unexplained (§6). |
| When training scratch is dropped | **After each EM session**, not once after `train`. | The ticket said "after `train`". DuckDB never shrinks a file, so dropping only at the end leaves the file at all three sessions' sum (free disk fell to 58 GB in `train`, under the runbook's 60 GB stop line). Dropping per session caps the file near the largest session, and the next session reuses the freed blocks. |
| Reusing a saved model | `resolve --full --model VERSION` loads `resolution/model/VERSION.json`, skips `train`, and resolves as model `VERSION`. | Saving early without a way to read the model back keeps a file and saves no time. Reusing silently when `--build-id` matches a saved model makes one command train or not depending on what an earlier run left. |
| Which model is live | The newest saved model that also has a run record (`resolution/run/<version>.json`), which a run writes last. | With the model saved after `train`, a failed run's JSON would be the newest, and `load` would publish its version in `gold.meta` with no quality figures. A `pending/` key layout needs two lookups in `--model` and a second layout to document. Documenting "rerun before any load" leaves the weekly run free to load in between. |
| Vetoed pairs | Streamed per component with the members and edges; the algorithm and the veto's SQL are untouched. The largest component's size is logged. | Holding the sparse set of compatible pairs instead would bound a giant component, but rewrites the union check DIME's scores were measured on (ADR-0010) for a risk nobody has observed: 2024's largest component is 263 keys. A fail-fast threshold would be a setting picked without data. |
| `max_pairs` sampling for EM | **Not in this ticket** (the ticket's own rejection). | It changes the model and its DIME scores; that belongs to NEU-2054's thresholds work. |

## 2. Definitions

Glossary (`CONTEXT.md`, Resolution): **Live model** is new, added with this spec. Use it in code, docstrings and docs in place of "latest" or "newest" model wherever the meaning is "the model the current donor_ids were assigned with".

**Splink scratch** (this spec only, not a glossary term): the tables Splink creates in the working file. The four kinds this ticket drops early are named by prefix:

| Prefix | Made by | Dropped |
|---|---|---|
| `__splink__blocked_id_pairs_` | each EM session | after that session |
| `__splink__df_comparison_vectors_` | each EM session | after that session |
| `__splink__df_predict_` | `predict` | after `edge` and `component` are written |
| `__splink__df_clustered_with_input_data_` | clustering | after `component` is written |

## 3. Dropping Splink's scratch

### 3.1 One helper

One function in `src/fundlens/resolve/model.py` (it owns everything that touches Splink's internals), for example `drop_scratch(linker, con, prefixes)`:

- It finds the working file's tables whose names start with one of `prefixes` (from `duckdb_tables()` or `SHOW TABLES`), drops each, then runs `CHECKPOINT`.
- The two prefix groups are module constants, named for when they are dropped (training, prediction), so the call sites read as what they drop.
- It also removes each dropped table from Splink's own bookkeeping, so Splink never hands back a table that is gone. Splink 5.0 has `SplinkDataFrame.drop_table_from_database_and_remove_from_cache()` and a per-`db_api` cache; use the public call where a handle exists, and where only a name exists, drop by SQL and evict the cache entry whose `physical_name` matches (`remove_splinkdataframe_from_cache` does this by physical name).
- It returns or logs the names dropped, one `log.info` line per call with the count.

`save`'s `linker.table_management.delete_tables_created_by_splink_from_db()` stays exactly as it is. It uses `DROP TABLE IF EXISTS`, so tables already gone do not trouble it.

### 3.2 Where it is called

- **In `model.train`**, after each `estimate_parameters_using_expectation_maximisation(rule)`: drop the training prefixes. `train` needs the connection for this; pass `con`, or have the helper take it from the linker's `db_api`.
- **In `cluster.cluster`** (or in `resolve_full` right after it returns): once `edge` and `component` are written, drop the prediction prefixes.
- Nothing is dropped that `predict` reuses. The term-frequency and concatenated-input tables (`__splink__df_concat*`, `__splink__df_tf_*`) are outside the four prefixes and stay.

**To verify while implementing:** that `predict` and clustering give the same `edge` and `component` after the training tables are dropped and evicted. The existing fixture tests cover clusters; §8's training test covers the trained path.

### 3.3 What it does not do

- The file does not shrink. `CHECKPOINT` lets DuckDB reuse the freed blocks; the file stays at its high-water mark, about the size of the largest EM session's two tables plus what was there before. On 2026-11-16's figures that session (soundex + ZIP3, 2.6 billion pairs) is most of the 254 GB, so expect a working file well over 100 GB during and after an all-cycle run. Step 9's rerun measures it.
- It does not change what Splink computes.

## 4. The model: saved after `train`, reusable, live only when its run finishes

### 4.1 Save after `train`

In `resolve_full`, right after the `train` phase: `linker.misc.save_model_to_json(model_path, overwrite=True)` and `store.put(model_key, model_path)`. Time it as its own phase, `model`, between `train` and `cluster`.

The `save` phase keeps its name and now only deletes Splink's remaining tables. `docs/capacity.md`'s Resolution table has a `save` column in its header; it keeps that column, and the `model` phase's seconds go in the row's Notes (M4's shared contract fixes the columns).

### 4.2 `resolve --full --model VERSION`

A new option on `fundlens resolve`:

- `--model VERSION` requires `--full` and excludes `--build-id`. Giving both is a usage error.
- The run downloads `resolution/model/VERSION.json` (`paths.resolution_model`). If there is none it stops with exit 1 and a message naming the key, before loading contributors.
- It builds the linker from the saved JSON (`model.linker(db_api, table, saved)`, the path `test_resolve_full_saves_a_model_that_reloads_without_training` already exercises), runs no `train` phase and writes no model. Everything after is the same run: `cluster`, `recluster`, `overrides`, `adjudications`, `save`, `crosswalk`, `silver`, markers, run record.
- The run's version is `VERSION`: it is `Resolved.model_version`, the `build_id` the crosswalk records, and the key of the run record.
- `Resolved.trained` becomes a three-way fact the CLI prints: `trained`, `priors (too few keys to train on)`, or `reused (saved model)`. `phase_s` has no `train` or `model` entry on a reusing run.
- Reusing a model that is already live is allowed. It re-resolves with the same model and overwrites that version's run record.

`resolve_full` takes the choice as one parameter (for example `reuse: str | None` beside `build_id`, or a small union); the CLI maps the two options onto it.

### 4.3 The live model

`model.latest_version(store)` becomes `model.live_version(store)`: the newest version under `resolution/model/` that also has `resolution/run/<version>.json`. Rename the function and its three callers (`load/gold.py`, `resolve/validate.py`, `resolve/adjudicate.py`), and say **live model** in their docstrings and messages.

- `runner.run_record`'s "or one that failed after saving its model" case goes away for the live model: a live model always has a record. `load._quality` keeps handling `None` for a version given explicitly.
- `validate --model-version V` still scores any saved version by name.
- `--model VERSION` reads by key, not through `live_version`, so a failed run's model is reachable.

**One check before merge (prod, read-only):** the model live on prod today has a run record. Models trained before NEU-2056 have none; if the newest model on prod were one of them, `live_version` would skip it. The command, for the PR description's checklist:

```sh
docker exec "$(fl pipeline)" python -c "
from fundlens.r2 import R2; from fundlens.settings import get_settings; from fundlens import paths
s = R2.from_settings(get_settings())
print(sorted(s.list_keys(paths.MODEL_PREFIX))[-3:]); print(sorted(s.list_keys('resolution/run/'))[-3:])"
```

Expected: the last model key and the last run key carry the same version. If they do not, stop and say so on the ticket; do not merge.

## 5. `recluster` holds one component at a time

### 5.1 What changes

`recluster` today fetches every offending component's members, edges and vetoed pairs into three dicts, then loops. It becomes a stream:

- `offending` (oversized or holding a vetoed pair) is built in DuckDB as a table, not passed through Python as a list.
- Three queries, each `ORDER BY cluster_id` (members also by key, as now): members with first names, joining edges, vetoed pairs. Each is read with a cursor in batches (`fetchmany`), each on its own cursor (`con.cursor()`), and merged in Python by `cluster_id`, so only the current component's members, edges and vetoed pairs are held.
- `recluster_component` is called per component exactly as now. Its signature and behaviour do not change (ADR-0010).
- Moved keys go into a temp table in batches as components finish, not into one dict passed as a parameter list at the end. The final `CREATE OR REPLACE TABLE cluster` joins that table.
- The counts `Reclustered` reports are accumulated as the stream runs. `oversized`, `inconsistent` and `components` can come from SQL.

`_vetoed_pairs` keeps its SQL to the letter (the `name` CTE, the Jaro-Winkler bound, the initial and nickname fragments). Only how its rows are consumed changes.

`recluster_working_file` (`fundlens recluster`) calls the same function inside its transaction and needs no change of its own; check the temp tables behave inside `con.begin()`.

### 5.2 What stays unbounded

One component is still held whole, and its vetoed pairs grow with the square of its distinct first names. That is accepted (§1.1) and made visible by §5.3.

### 5.3 What it logs

`recluster` logs, at `info`, beyond the existing summary line:

- before the stream: the number of offending components, their keys and their joining edges;
- for the largest offending component: its keys, distinct first names and vetoed pairs;
- the process's peak resident memory when it finishes (`resource.getrusage(RUSAGE_SELF).ru_maxrss`, in GiB).

These are log lines, not fields of `Reclustered` or columns of `docs/capacity.md`. Step 9's rerun reads them from `resolve.log`.

## 6. `docs/capacity.md`

Under Resolution, a Notes-level record of the 2026-11-16 all-cycle run that failed (it has no row: it resolved nothing):

- model `20261116T022944Z`, `62a47eb`, 24 cycles, 29,213,828 keys, DuckDB limit 32 GB;
- phases load 54 s, train 8,420 s (EM 8, 7 and 12 iterations), cluster 2,499 s, failed in `recluster` after 3h22m;
- working file 254,181,650,432 bytes, with the table breakdown from NEU-2060's comment (the three sessions' pair counts, `__splink__df_predict` 112,392,100, `__splink__df_clustered_with_input_data` 29,213,828);
- free disk 266 → 202 → 78 → 128 → 58 → 14 → 3 → 1 GB;
- peak `pipeline` memory 40.00 GiB at 05:35:53Z by `docker stats`, **what held it not established**;
- what NEU-2325 changed, in two sentences, and that step 9's rerun gives the first all-cycle row.

Also a Findings bullet: pairs grow much faster than keys (5.6M keys made a 9.4–9.9 GB file; 29.2M made 254 GB), so a working-file estimate scaled by key count is wrong by a wide margin.

## 7. Other docs

- **Project spec** §6.3: the model is saved right after training; `--model VERSION` resolves with a saved model; the live model is the newest with a run record. §6.4: Splink's scratch is dropped per EM session and after `cluster`; `recluster` streams components. §5.1's CLI list gains `--model`. Each amendment names NEU-2325 and this file, as earlier amendments do.
- **`runner.py`'s module docstring** and `resolve_full`'s: the new order (model saved after `train`) and the reuse path.
- **`docs/runbooks/backfill.md`** step 9: what to do after a failed run, as an exact command (`resolve --full --model <the failed run's version>`), and the new log lines to grep. NEU-2060 owns the rerun; this ticket only makes the runbook's text true for the new CLI.
- No ADR: nothing here is hard to reverse, and ADR-0010's algorithm is unchanged.

## 8. Tests

Targeted while iterating (`task` targets, in the container); the pre-commit hook runs the full suite once at commit. Keep new tests cheap: share `transformed`/snapshot fixtures, and do not add a second full fixture resolve where a spy on an existing shape will do.

1. **No early-dropped scratch at the start of `recluster`, on a run that really trains.** `resolve_full` on the fixture with `min_training_keys` low enough that EM runs, and `recluster` replaced by a spy that records the working file's table names and then raises. Assert no table starts with any of the four prefixes, and that `contributor`, `edge` and `component` are there. The fixture trains on priors by default, so without lowering `min_training_keys` this test proves nothing about the training tables. If EM cannot run on the fixture (a blocking rule with no pairs raises `EMTrainingException`), test the helper where EM does run: `tests/unit/test_resolve_model.py` already trains a linker.
2. **The model is in R2 when a later phase fails.** The same run as test 1 serves: after the spy raises in `recluster`, `resolution/model/<build>.json` is in the store and there is no `resolution/run/<build>.json`. (The ticket's DoD says "makes `cluster` fail"; failing one phase later proves the same thing and saves a run. If a reviewer wants the letter, make `cluster` the spy instead for this assertion.)
3. **A failed run's model is not live.** After test 2's state, `model.live_version(store)` is the earlier version (or `None`), not the failed build.
4. **`--model` resolves without training and makes the model live.** `resolve --full --model <that build>` exits 0, logs no `train` phase, gives the same clusters as a full run of that model, writes the run record, and `live_version` is now that build.
5. **`--model` usage errors.** With `--build-id`: usage error. A version with no JSON: exit 1 naming the key.
6. **Streaming gives the same clusters.** The existing recluster tests (the chain, the cap of three, the threshold tests) must pass unchanged; they are the proof. Add one unit test in which two offending components interleave with a non-offending one in key order, so the merge by `cluster_id` is exercised with an empty-edges and an empty-vetoed component.
7. **The helper.** A unit test: tables with the prefixes and one without; after the call only the latter remains, and a second call is a no-op.

After the commit, read the hook's slowest-tests list; a new test near the top is a defect to fix before shipping.

## 9. Definition of done

- [ ] Test 1 passes with EM actually running (the log shows the EM sessions), and finds none of the four prefixes at the start of `recluster`.
- [ ] Test 2: the model JSON is in R2 after a failure past `train`; no run record.
- [ ] Tests 3–5: a failed run's model is not live; `--model` resolves with it without training and makes it live; the two usage errors.
- [ ] The existing recluster tests pass unchanged, and test 6's interleaving case passes.
- [ ] The PR states that the memory fix is streaming, chosen by reading the code and the 2026-11-16 figures, not by a new measurement, and that what held the 40 GiB is not established.
- [ ] The PR's checklist shows §4.3's prod check run, with its output.
- [ ] `docs/capacity.md` records the failed run (§6); the project spec, docstrings and `backfill.md` are amended (§7); `CONTEXT.md` has **Live model**.

## 10. Out of scope

- Resuming `resolve --full` from the working file after `cluster`.
- The all-cycle rerun and its measurements: NEU-2060 step 9.
- A resolve-specific DuckDB memory limit, EM `max_pairs` sampling, and any change to the veto or to `recluster_component`.
- Shrinking the working file after the run (DuckDB does not; a copy-out would be a separate ticket if the size matters at steady state).
- Incremental resolution (§6.10, NEU-2062). It will read `live_version`.
