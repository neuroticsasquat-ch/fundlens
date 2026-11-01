# NEU-2054 — DIME validation: join to FEC records, precision/recall report into `gold.meta`

**Ticket:** [NEU-2054](https://linear.app/neuroticsasquatch/issue/NEU-2054) · **Milestone:** M3 Resolution · **Parent story:** NEU-2021
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §3.4, §5.1, §6.9, §7.1, §10.5, §12, §13 (amended by this spec) · **ADRs:** 0002 (R2 is the store of record), 0005 (crosswalk in Postgres), 0009 (resolution quality is scored against DIME by FEC ids; written with this spec)
**Blocked by:** NEU-2049 (merged: `donor_id` on bucketed silver, `app.crosswalk`). **Blocks:** NEU-2056 (methodology page, `/v1/meta` quality fields), NEU-2060 (backfill).

Planned 2026-11-01. `/implementit NEU-2054` implements straight from this file.

## 1. What and why

Resolution's central claim, that the donor behind many contributor spellings is one person, has no number behind it: the first resolved production run (NEU-2079) was judged by looking at Elon Musk. Adam Bonica's DIME (Database on Ideology, Money in Politics, and Elections) labels every FEC contribution with a resolved contributor id, `bonica.cid`, produced by its own probabilistic linkage. Scoring fundlens's `donor_id` against `bonica.cid` on the contributions both know gives a precision and a recall to publish and, later, to tune against.

This ticket adds:

- `fundlens dime --cycle C --import PATH`: takes a downloaded DIME contribution file for cycle `C`, archives it in R2, and writes the slim Parquet of its FEC individual rows that the validator reads.
- `fundlens validate --cycle C [--model-version M] [--top N]`: joins the slim DIME file to the cycle's FEC records by exact FEC ids, scores the cycle's resolved silver against `bonica.cid`, writes two rows to `app.resolution_quality` (overall and top-N scopes) and prints the report.
- `app.resolution_quality` (migration), four new `gold.meta` columns, and `load` copying the figures into `gold_build.meta`.
- The fixture DIME file brought to the real file's columns, `expected.yaml`'s validation block, and `docs/runbooks/refreshing-dime.md`.

### 1.1 Decisions this spec pins (the ticket asked `/planit` to research them)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| DIME release | **Public version 4.0** (Bonica 2024), 1979–2024, from `https://data.stanford.edu/dime`. Files are Dropbox links on that page, one `contribDB_<cycle>.csv.gz` per even year. `DIME_VERSION = "4.0"` in `resolve/validate.py` names every R2 key and every stored row. | Harvard Dataverse (`doi:10.7910/DVN/O5PX0B`) is stale at v3.0. |
| Terms of use | ODC-BY 1.0 ("Data Use Agreement" on the Stanford page). Attribution is the only condition: `DIME_CITATION` in `validate.py` holds the citation string (§3.1), the runbook repeats it, and NEU-2056 (methodology page) and M6 (dataset README) print it. fundlens publishes only derived figures, never DIME rows, so nothing of DIME is redistributed. The CRP/NIMSP state rows are excluded from the public download and are not needed. | — |
| Size | `contribDB_2024.csv.gz` is **19,158,623,840 bytes** (19.2 GB gzipped; `Content-Length` checked 2026-11-01), about 200M rows, state and federal, individuals and committees. Earlier cycles are much smaller. | — |
| Join key | **Exact FEC ids**: DIME's `efec.comid.orig` (the filer's `CMTE_ID`) and `efec.transaction.id.orig` (the filer's `TRAN_ID`), plus `amount` and `date`, against the cycle's bronze `indiv` file; then `SUB_ID` to silver `contribution.source_record_id`. The codebook (v4.0 §"Contribution records", items 39 and 42) defines them as the original transaction id and committee id from FEC electronic filings, and a 40 MB sample of the live 2024 file had them on all but 1 of 409,557 individual rows. | The spec's fuzzy join (date, amount, recipient committee, normalized name): 12 of the fixture's 308 `indiv` rows already collide on that key, it needs the 30 MB recipients file to map `bonica.rid` to FEC ids, and name normalization differences would make the matched set depend on our own normalizer. Adding `TRAN_ID` to silver `contribution`: the same join, but a silver schema change and a re-transform of every cycle before its first validation. Bronze is in R2 for every cycle and never pruned. |
| Where the file lives | R2 `reference/dime/v<version>/contribDB_<cycle>.csv.gz` (the raw file, archived) and `reference/dime/v<version>/cycle=<cycle>/fec_individual.parquet` (the slim file the validator reads). Both written by `fundlens dime`. Local cache under `DATA_DIR/reference/…` (`paths.local_path`). | Not archiving the raw file: Dropbox links rot and `bonica.cid` values change between releases (codebook §14), so a published figure could not be reproduced. Reading the raw gzip on every validation: tens of minutes of single-threaded decompression per run. R2 cost for 2024's raw file is about $0.30/month. |
| Truth rows | A DIME row is truth when `contributor.type = 'I'`, `efec.comid.orig` matches `^C\d{8}$` and `efec.transaction.id.orig` is non-empty. Collapsed to distinct `(cmte_id, tran_id, amount, date, cid)`; an FEC row that still matches more than one `cid` is dropped as ambiguous, as is one that matches none. | Keeping committee rows or rows without FEC ids: nothing to join them to. Using `bk.ref.transaction.id` to dedupe: the exact-id collapse already removes a duplicate with the same label, and a duplicate with a different label is exactly the ambiguity to drop. |
| Record scored | **Labelled contributor key**: one record per distinct `(contributor_key, bonica.cid)` among the matched contributions, with the key's `donor_id` as its predicted label. A key DIME assigns to two people becomes two records that fundlens necessarily puts together, and costs precision. | Keys labelled by majority `cid`: scores a key DIME splits as if fundlens got it right. Matched contribution rows: a 500-gift donor contributes 124,750 pairs and a one-gift donor none, so the figure would measure frequent givers. |
| Metrics | **Pairwise precision and recall** over the records, from the contingency table `n(donor_id, cid)`: `correct = Σ C(n(d,c), 2)`, `predicted = Σ_d C(n(d,·), 2)`, `true = Σ_c C(n(·,c), 2)`; `precision = correct / predicted`, `recall = correct / true`, each NULL when its denominator is 0. | Cluster-level (exact-match) accuracy punishes one stray key in a 40-key cluster as a whole miss. B-cubed needs per-record weights that the methodology page could not state in one sentence. |
| Top scope | The `cid`s with the most matched dollars, `--top N` of them (default 10,000; ties broken by `cid`), and the metrics over the records of those `cid`s only. Truth-side, so the scope does not move when our clustering does, and a big donor fundlens split is still scored. | Top fundlens donors: a split big donor may fall out of the scope. The union of both: harder to state. |
| Model version | The version the figures belong to is the newest saved model in R2, `resolution/model/<version>.json` (key order is training order, `paths.resolution_model`), through a new `resolve.model.latest_version(store)`; `--model-version` overrides it. `load` uses the same helper to pick the rows for `gold_build.meta`, and NEU-2056 writes `gold.meta.model_version` from it, so the three agree. | `max(app.crosswalk.build_id)`: the crosswalk records a build only on rows whose id changed, so a re-resolve that changed nothing leaves the old version there. The `resolved` marker: it does not record the model. |
| `gold.meta` shape | Keep `precision` and `recall` as the overall scope; add `precision_top numeric`, `recall_top numeric`, `matched_rows bigint`, `dime_version text`. NULL until the cycle has been validated under the live model. | One `quality jsonb`: `/v1/meta` already exposes the scalars. Reading the top scope from `app` in the API: no public route reads `app`. |
| Tuning | Out of scope, as the ticket says. Spec §13's "tuned in the DIME validation ticket" is amended: this ticket produces the number; a follow-up ticket tunes. | — |

### 1.2 Not in scope

Tuning `RESOLVE_MATCH_THRESHOLD` / `RESOLVE_CLUSTER_THRESHOLD` or the model; the methodology page and the `/v1/meta` fields (NEU-2056: this ticket changes neither `api/schemas.py` nor `routers/meta.py`); multi-cycle `gold.meta` (NEU-2059/NEU-2060); adjudication (NEU-2055); wiring `validate` into `fundlens run` (NEU-2061 decides; `validate` is run by hand); matching paper-filed rows, which have no `efec.*` ids (cycles before electronic filing will match few rows, and `matched_rows` says so); a dataset-manifest entry for the figures (M6).

### 1.3 Facts found while planning

- The live 2024 file's header, verbatim: `cycle, transaction.id, transaction.type, amount, date, bonica.cid, contributor.name, contributor.lname, contributor.fname, contributor.mname, contributor.suffix, contributor.title, contributor.ffname, contributor.type, contributor.gender, contributor.address, contributor.city, contributor.state, contributor.zipcode, contributor.occupation, contributor.employer, occ.standardized, is.corp, recipient.name, bonica.rid, recipient.party, recipient.type, recipient.state, seat, election.type, latitude, longitude, gis.confidence, contributor.district, censustract, efec.memo, efec.memo2, efec.transaction.id.orig, bk.ref.transaction.id, efec.org.orig, efec.comid.orig, efec.form.type, excluded.from.scaling, contributor.cfscore, candidate.cfscore` (45 columns). A sample FEC individual row: `2024,e:ind:2024:2024072617:886943320,15,250,2020-09-25,32373199050,"effres, justin",…,I,…,STAND FOR BETTER PAC,comm154842,…,SA11AI.4105,,Stand For Better LLC,C00758672,sa11ai,0,-0.951,-1.122`. Nulls are written as `\N` or empty. Names are lower-case; dates ISO; `amount` may carry cents.
- `bonica.rid` is DIME's own recipient id (`comm154842`, `cand100270`); the FEC committee id is `efec.comid.orig`. The fixture's README guessed `bonica.rid` would hold the FEC id; §7 corrects the fixture.
- The fixture's `indiv.csv` already gives every row a unique `TRAN_ID` (`SA11AI.00001` …), so the exact join needs no `indiv` change.
- Codebook v4.0 §12: duplicates exist (conduit double-reporting, 527 cross-reporting); §14: `bonica.cid` values change between releases, `transaction.id` is stable.

## 2. Layout

```
src/fundlens/resolve/validate.py      DIME_VERSION, DIME_CITATION; import_dime(); validate(); score() (pure)
src/fundlens/resolve/model.py         + latest_version(store) -> str | None
src/fundlens/paths.py                 + reference_dime_raw(version, cycle), reference_dime(version, cycle)
src/fundlens/transform/runner.py      _unzip → unzip_bulk (public, same signature); validate reuses it
src/fundlens/cli.py                   + dime, validate (both @step with no family, like resolve)
src/fundlens/app_schema.py            + resolution_quality
migrations/versions/<rev>_add_resolution_quality.py   down_revision 5d8e919b342d
src/fundlens/load/gold.py             meta insert gains the four columns from app.resolution_quality
sql/gold/ddl/meta.sql                 + precision_top, recall_top, matched_rows, dime_version
tests/fixtures/dime/contribDB_2024.csv  + efec.comid.orig, efec.transaction.id.orig; README rewritten
tests/fixtures/fec/2024/expected.yaml   + validation block (§7)
tests/unit/test_validate.py           score() on a hand-built contingency; truth-row filter
tests/unit/test_fec_fixture.py        dime_cids() joins on the FEC ids
tests/integration/test_validate.py    dime --import, validate, load → gold_build.meta (§8)
tests/integration/test_migrations.py  EXPECTED_COLUMNS + resolution_quality
docs/runbooks/refreshing-dime.md      download, import, validate, what the next load carries (§9)
docs/adr/0009-…md                     written with this spec
CONTEXT.md                            Reference label, Labelled key, Validation (written with this spec)
```

## 3. The DIME file

### 3.1 Constants (`resolve/validate.py`)

```python
DIME_VERSION = "4.0"
DIME_SOURCE = "https://data.stanford.edu/dime"
DIME_CITATION = (
    "Bonica, Adam. 2024. Database on Ideology, Money in Politics, and Elections: "
    "Public version 4.0 [Computer file]. Stanford, CA: Stanford University Libraries. "
    "https://data.stanford.edu/dime"
)
DIME_LICENSE = "ODC-BY 1.0"
```

A new DIME release is a PR that bumps `DIME_VERSION`, re-imports every cycle (§9) and re-validates; old versions' keys stay in R2 untouched.

### 3.2 R2 keys (`paths.py`)

```python
def reference_dime_raw(version: str, cycle: int) -> str:
    """The DIME contribution file for `cycle` as downloaded: reference/dime/v<version>/contribDB_<cycle>.csv.gz."""

def reference_dime(version: str, cycle: int) -> str:
    """The FEC individual rows of that file, slimmed: reference/dime/v<version>/cycle=<cycle>/fec_individual.parquet."""
```

Both `_check_cycle`. Spec §3.4's R2 layout gains the `reference/` line (amended with this spec).

### 3.3 The slim Parquet

One row per DIME row kept by the truth filter (§1.1), columns:

| Column | From | Type |
|---|---|---|
| `transaction_id` | `transaction.id` | text (DIME's stable id, for tracing a row back) |
| `cmte_id` | `efec.comid.orig` | text |
| `tran_id` | `efec.transaction.id.orig` | text |
| `amount` | `amount` | decimal(14,2) |
| `date` | `date` | date |
| `bonica_cid` | `bonica.cid` | text (never numeric: ids like `5000002667852691` are not quantities) |
| `transaction_type` | `transaction.type` | text |
| `contributor_name` | `contributor.name` | text |

zstd, row groups ≤ 1M rows, written by DuckDB `COPY … TO`. Nothing else of DIME is kept.

## 4. `fundlens dime --cycle C --import PATH`

`resolve.validate.import_dime(store, *, cycle, path, data_dir, limits) -> Imported(rows_read, rows_kept, cids, raw_key, parquet_key)`.

1. `PATH` must exist and be a `.csv` or `.csv.gz` (DuckDB picks the compression from the name; the fixture is a plain `.csv`). Its header must contain the eight source columns of §3.3; a missing one is an error naming it (so a v5 column rename fails loudly, not silently with zero rows).
2. DuckDB (connected like transform: `limits`, `temp_directory` under `scratch/`) reads it with `read_csv(path, header = true, all_varchar = true, quote = '"', escape = '"', nullstr = ['', '\N'], parallel = false)` (a gzip is read single-threaded anyway; `parallel = false` keeps memory flat), applies the truth filter, casts `amount` and `date` (`try_cast`; a row whose cast fails is dropped and counted), and writes the Parquet under `paths.local_path(data_dir, reference_dime(DIME_VERSION, cycle))`.
3. Uploads the Parquet to R2 (`store.put` with a `Path`: boto3 handles multipart), then the raw file to `reference_dime_raw` (19 GB for 2024: multipart, minutes). Parquet first, so a bad file fails before the long upload.
4. Prints `rows read`, `rows kept`, `distinct cids`, `rows dropped (cast)`, both keys. Re-running overwrites both objects.

`PATH` is not deleted: the runbook says when to.

## 5. `fundlens validate --cycle C [--model-version M] [--top N]`

`resolve.validate.validate(store, *, cycle, model_version, top, data_dir, limits, conn) -> Validated` (the two `Quality` rows plus the counts printed).

1. **Build.** The cycle's newest build with a `resolved` marker (list `markers_dir(cycle)`, keep keys ending `/resolved.json`, take the max `build_of`). None: `FileNotFoundError("no resolved build for <cycle>: run `fundlens resolve --full`")`, exit 1.
2. **Model version.** `M` or `model.latest_version(store)` (the max key under `resolution/model/`, its version parsed by `paths`). None: exit 1 with the same hint.
3. **DIME.** `reference_dime(DIME_VERSION, cycle)` from the local cache, downloaded if missing. Absent in R2: exit 1 naming `docs/runbooks/refreshing-dime.md`.
4. **Bronze.** `transform.runner.unzip_bulk(store, cycle, INDIV, data_dir=…, work=<scratch>/validate/)`; a DuckDB view over the text file with the vendored header, `all_varchar`, as transform registers it. Only `SUB_ID, CMTE_ID, TRAN_ID, TRANSACTION_DT, TRANSACTION_AMT` are read.
5. **Silver.** The build's `contribution` partition (every `bucket=*/` part; `_local_partition`-style download of missing parts), columns `source_record_id, contributor_key, donor_id`. A NULL `donor_id` anywhere: exit 1 ("build <B> is not resolved").
6. **Join** (DuckDB):

```sql
CREATE TABLE dime AS
SELECT DISTINCT cmte_id, tran_id, amount, date, bonica_cid FROM read_parquet(<slim>);

CREATE TABLE fec AS                       -- counted contributions only
SELECT b.SUB_ID::UBIGINT AS sub_id, b.CMTE_ID AS cmte_id, b.TRAN_ID AS tran_id,
       try_cast(b.TRANSACTION_AMT AS DECIMAL(14,2)) AS amount,
       try_strptime(b.TRANSACTION_DT, '%m%d%Y')::DATE AS date,
       s.contributor_key, s.donor_id
FROM indiv AS b JOIN silver AS s ON s.source_record_id = b.SUB_ID::UBIGINT;

CREATE TABLE matched AS                   -- one cid per contribution, or nothing
SELECT sub_id, contributor_key, donor_id, amount, any_value(bonica_cid) AS bonica_cid
FROM fec JOIN dime USING (cmte_id, tran_id, amount, date)
GROUP BY sub_id, contributor_key, donor_id, amount
HAVING count(DISTINCT bonica_cid) = 1;

CREATE TABLE labelled AS                  -- the records (§1.1)
SELECT contributor_key, donor_id, bonica_cid, sum(amount) AS amount
FROM matched GROUP BY ALL;
```

   `contribution_rows` = `count(*)` of `silver`; `matched_rows` = `count(*)` of `matched`.
7. **Score.** `score(records)` is a pure function over `(key, donor_id, cid)` rows (in SQL for the real run, the same arithmetic as the Python function the unit test pins), run twice: on `labelled`, and on `labelled` restricted to the `cid`s in `SELECT bonica_cid FROM labelled GROUP BY 1 ORDER BY sum(amount) DESC, bonica_cid LIMIT :top`.
8. **Write.** Upsert two rows into `app.resolution_quality` (§6) in one transaction, `ON CONFLICT (model_version, cycle, scope) DO UPDATE` on every other column.
9. **Print** a table, one row per scope: `scope, precision, recall, labelled keys, correct / predicted / true pairs`, then `matched <m> of <n> counted contributions (<pct>%)`, `model <M>, DIME v<version>, build <B>`. Exit 0 whatever the figures: it is a report, and the DoD compares numbers, not exit codes.

No marker (it is not a pipeline step that `run` resumes), no Kuma family, no Cloudflare. Idempotent: re-running under the same model overwrites the same two rows.

## 6. `app.resolution_quality`

```sql
CREATE TABLE app.resolution_quality (
    model_version     text        NOT NULL,   -- resolution/model/<version>.json
    cycle             integer     NOT NULL,
    scope             text        NOT NULL,   -- 'overall' | 'top'
    dime_version      text        NOT NULL,
    top_limit         integer,                -- NULL for overall
    contribution_rows bigint      NOT NULL,   -- counted contributions in the build
    matched_rows      bigint      NOT NULL,   -- of them, labelled by exactly one cid
    labelled_keys     bigint      NOT NULL,   -- records scored (in scope)
    correct_pairs     bigint      NOT NULL,
    predicted_pairs   bigint      NOT NULL,
    true_pairs        bigint      NOT NULL,
    precision         numeric,                -- NULL when predicted_pairs = 0
    recall            numeric,                -- NULL when true_pairs = 0
    validated_at      timestamptz NOT NULL,
    PRIMARY KEY (model_version, cycle, scope),
    CONSTRAINT ck_resolution_quality_scope CHECK (scope IN ('overall', 'top'))
);
```

Declared in `app_schema.py` (so `alembic check` sees it), created by one migration revising `5d8e919b342d`, pinned in `test_migrations.EXPECTED_COLUMNS` and the table set. The pair counts are stored so a later ticket can pool cycles (micro-average: sums of the three counts) without re-running anything. Snapshotting this table to R2 at publish is not needed: it is regenerated by `validate`.

## 7. `gold.meta` and `load`

`sql/gold/ddl/meta.sql` gains, after `recall`: `precision_top numeric, recall_top numeric, matched_rows bigint, dime_version text`. The DDL comment's "NULL until M3" becomes "NULL until the cycle is validated under the live model (NEU-2054)".

`load.gold._load_postgres` inserts them: with `M = model.latest_version(store)` (None → all four NULL and `precision`/`recall` NULL), `SELECT scope, precision, recall, matched_rows, dime_version FROM app.resolution_quality WHERE model_version = %s AND cycle = %s`; the `overall` row fills `precision, recall, matched_rows, dime_version`, the `top` row fills `precision_top, recall_top`. No rows: NULLs. `load`'s output gains one line: `quality: precision <p> recall <r> (top <pt>/<rt>), <m> matched rows, DIME v<v>` or `quality: not validated for model <M>`.

NEU-2056 reads these columns into `/v1/meta` and writes `model_version` from the same helper; a comment on that ticket (posted with this spec) says so.

## 8. Fixture and tests

### 8.1 Fixture

`tests/fixtures/dime/contribDB_2024.csv` gains two columns, `efec.comid.orig` (the labelled row's `CMTE_ID`) and `efec.transaction.id.orig` (its `TRAN_ID`), and keeps the rest as a DIME-shaped subset. `bonica.rid` stays but holds a DIME-style id (`comm<n>`), not the FEC id, so nothing joins on it by accident. `README.md` is rewritten: the real file's columns, the join, and that the file is a subset of §1.3's header.

`tests/unit/test_fec_fixture.dime_cids()` joins on `(CMTE_ID, TRAN_ID)` and asserts, as today, that every counted contribution has exactly one label and each planted donor's rows share one `cid`.

`expected.yaml` gains:

```yaml
# What `fundlens validate --cycle 2024 --top 3` must report on the fixture after `resolve --full`
# with the fixture overrides (spec §6.9). Pairs follow from `donors` above: a donor with k
# contributor keys among its counted contributions contributes k(k-1)/2 true pairs.
validation:
  dime_version: "4.0"
  matched_rows: 281          # every counted contribution: the fixture labels them all
  labelled_keys: 107         # contributor keys with a counted contribution (108 less the 15J-only key)
  overall: {precision: 1.0, recall: 1.0}
  top: {limit: 3, precision: 1.0, recall: 1.0}
```

`test_fec_fixture` checks `labelled_keys` and `matched_rows` against the CSVs like every other number there.

### 8.2 Unit (`tests/unit/test_validate.py`)

- `score()` on this hand-built contingency: records `(k1,d1,c1), (k2,d1,c1), (k3,d1,c2), (k4,d2,c2), (k5,d3,c3)` → `correct 1, predicted 3, true 2, precision 1/3, recall 1/2`. And: no records → all counts 0, both metrics None; every record alone → `predicted 0, true 0`, both None.
- The truth filter on a six-row in-memory CSV: a committee row, a row with no `efec.comid.orig`, a row with a non-FEC committee id, a `\N` amount, a bad date, and one good row → one kept, the cast-drop counted.
- `paths.reference_dime*` shapes and `_check_cycle`.

### 8.3 Integration (`tests/integration/test_validate.py`)

Built on `test_resolve`'s `transformed` fixture and `resolve("--full", "--build-id", MODEL)`:

- `fundlens dime --cycle 2024 --import tests/fixtures/dime/contribDB_2024.csv` → MinIO holds the raw copy and a Parquet of 281 rows; the output says `281 rows kept`.
- `fundlens validate --cycle 2024 --top 3` → two rows in `app.resolution_quality` for `(MODEL, 2024)` with the `expected.yaml` figures, `contribution_rows` = `expected['silver']['contribution']`, and pair counts equal to those derived from `expected['donors']` (keys per donor from silver, as `test_resolve.keys_by_sub_id` does). Printed table carries the same numbers.
- Re-running `validate` leaves the same two rows (`validated_at` moves).
- Altering one label (a copy of the fixture with one `efec.transaction.id.orig` changed) and re-importing: `matched_rows 280`.
- `fundlens load --cycle 2024 --build-id BUILD` after validation → `gold_build.meta` has the overall and top figures, `matched_rows 281`, `dime_version "4.0"`; before any validation (fresh `app`), all six are NULL and `load` prints `not validated`.
- `validate` before `resolve`: exit 1, the message names `resolve --full`. Without the DIME file: exit 1, the message names the runbook.

### 8.4 Everything runs in the container

`task test:unit`, `task test:integration`, `task lint`, `task typecheck`, `task db:check` (alembic autogenerate agrees with `app_schema.py`), `task format` before committing; files staged by name.

## 9. Runbook: `docs/runbooks/refreshing-dime.md`

In `first-resolved-run.md`'s shape: facts table (version, page, licence, citation, 2024 file size, R2 keys), then steps, each with its command and expected output, then a Log. Every value gets an explicit command; no two alternatives in one block.

1. Check `https://data.stanford.edu/dime` for the version; if it is not `DIME_VERSION`, stop: bump the constant in a PR first.
2. In the `pipeline` container on `music-box-dancer`: `mkdir -p /data/fundlens/reference/dime/v4.0 && curl -L -o /data/fundlens/reference/dime/v4.0/contribDB_2024.csv.gz '<the page's 2024 link>'`; expect 19,158,623,840 bytes (`ls -l`). Disk check first (`df -h /data`): the file plus the Parquet plus scratch.
3. `fundlens dime --cycle 2024 --import /data/fundlens/reference/dime/v4.0/contribDB_2024.csv.gz`; expected output shape; expect tens of minutes (decompression) plus the 19 GB upload. Record the time in the Log.
4. `fundlens validate --cycle 2024`; expected table shape; record the figures in the Log and in a new "Validation" table in `docs/capacity.md` (date, model, cycle, matched, precision, recall, wall s).
5. The next `fundlens load --cycle 2024` + `publish` carry the figures into `gold.meta` (they ride the next scheduled run or the backfill; no run of their own).
6. `rm` the raw file from `/data` once the import printed its R2 key: R2 holds it (ADR-0002).
7. Repeat 2–4 per cycle for the backfill (NEU-2060 links here).

## 10. Acceptance criteria

- [ ] `fundlens validate --cycle 2024 --top 3` on the fixture (after `resolve --full` with the fixture overrides and `fundlens dime --import` of the fixture file) prints and stores precision 1.0 and recall 1.0 for both scopes, `matched_rows 281`, `labelled_keys 107`, and pair counts derived from `expected.yaml`'s donors (integration test).
- [ ] `score()` returns precision 1/3 and recall 1/2 on §8.2's contingency (unit test).
- [ ] `gold_build.meta` after `load` carries `precision`, `recall`, `precision_top`, `recall_top`, `matched_rows` and `dime_version` for the fixture build, and NULLs when nothing was validated (integration test).
- [ ] `alembic upgrade head` creates `app.resolution_quality` with §6's columns and the migrations test pins them; `task db:check` passes.
- [ ] `fundlens dime --cycle 2024 --import <fixture>` writes both R2 objects and reports 281 rows kept (integration test).
- [ ] `docs/runbooks/refreshing-dime.md` exists with every command explicit; `tests/fixtures/dime/README.md` describes the real columns and the join; this spec's §1.1 records the DIME version (4.0), the column mapping (§3.3), the terms-of-use check (ODC-BY 1.0) and the R2 location (§3.2), which is the ticket's third DoD item.
- [ ] `/v1/meta`, `api/schemas.py` and the frontend are untouched.

## 11. Deferred

- Pooling several cycles' figures into one `gold.meta` row (the pair counts are stored for it): with multi-cycle meta (NEU-2059/NEU-2060).
- Paper-filed rows (no `efec.*` ids) and pre-2001 cycles: unmatched by design; a later ticket may add the fuzzy join as a second pass if the backfill shows coverage too low to publish.
- A `--all` cycles mode: the backfill runbook loops the command.
- Tuning thresholds against the figure: a follow-up ticket; spec §13 amended.
