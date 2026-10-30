# NEU-2039 — Gold build (non-donor tables), schema-swap publish, rollback, Cloudflare purge, silver pruning

**Ticket:** [NEU-2039](https://linear.app/neuroticsasquatch/issue/NEU-2039) · **Milestone:** M2 One cycle, committee-level · **Parent story:** NEU-2019
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §3.4, §5.5, §7.1, §7.3, §13 · **ADRs:** 0002 (R2 is the store of record), 0006 (itemized stays in Parquet), 0007 (gold loads by DuckDB → CSV → `COPY`; written with this spec)
**Blocked by:** NEU-2037, NEU-2038 (merged) and NEU-2068 (silver `committee_transfer`, created alongside this spec; see §1.3).

Planned 2026-10-30. `/implementit NEU-2039` implements straight from this file.

## 1. What and why

Silver Parquet is not servable. Every page reads pre-aggregated gold tables in Postgres, and a weekly rebuild must become visible to readers in one instant, with the Cloudflare edge purged afterwards and a one-command way back if the new build is wrong. This ticket adds the two pipeline steps that do that for the M2 (non-donor) tables:

- `fundlens load --cycle C [--build-id B]` builds the schema `gold_build` from build `B`'s silver partitions: runs `sql/gold/*.sql` in DuckDB, runs `sql/checks/gold_*.sql`, copies every table into Postgres, writes `gold_build.meta`, writes the `loaded` marker.
- `fundlens publish --cycle C` swaps `gold_build` in as `gold` in one transaction (the old `gold` becomes `gold_prev`), waits out the API's build-id cache, purges the Cloudflare zone, writes the `published` marker and prunes silver builds older than the previous live one.
- `fundlens publish --rollback` swaps `gold_prev` back and purges again.

### 1.1 Decisions this spec pins (the project spec deferred them)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Load method | DuckDB computes every gold table from the silver partitions, writes each as a CSV file under `scratch/`, and psycopg streams it into Postgres with `COPY … FROM STDIN (FORMAT csv, HEADER match)` (`match`, not `true`: Postgres checks the CSV's column names against the DDL's, so a model whose columns drift from its DDL fails the load instead of filling the wrong columns). ADR-0007. | DuckDB's `postgres` extension would have to be baked into the image (tests run without network) and gives less control over the ingest than `COPY`, which is Postgres' fastest path. Building both behind a setting was rejected as twice the code for a one-time measurement. |
| Real-cycle measurement | Fixture timing is recorded in §8 of this file by the implementation. The real-cycle timing is the `load seconds` column of the 2024 row NEU-2046 writes to `docs/capacity.md`. | The first real cycle only exists after NEU-2046, which depends on this ticket. |
| Swap transaction | Exactly the statements in §4.2, in that order, with `SET LOCAL lock_timeout = '10s'`, up to 3 attempts. | See §4.2 for why the drop comes first and why the lock timeout matters. |
| Committee-money columns | Filled from silver `committee_transfer` (NEU-2068). The independent-expenditure columns (`ie_support`, `ie_oppose`, `ie_total`, `race_top_committee.kind = 'ie'` rows) are written as `0` / absent until NEU-2057. | Writing every committee column as zero would have moved the parent story's "raised from committees" and "top committees" to M4. Folding the silver into this ticket would have made one PR of silver + gold + publish + purge + pruning. |
| Resolution snapshot at publish | Not in this ticket. | `app.crosswalk` and `app.adjudication` are empty until M3; NEU-2049 adds the snapshot step with the data that fills them. |

### 1.2 Not in scope

Donor gold tables (M3), independent-expenditure values (NEU-2057), the `fundlens run` orchestration (NEU-2061), the dataset snapshot (M6), multi-cycle `gold.meta.cycles` from a manifest (NEU-2059), the rollback runbook (NEU-2063; this ticket only makes the command exist and work).

### 1.3 Prerequisite found while planning

The columns `total_committee` (race, race_candidate, candidate_cycle), `total_from_committees` and `total_to_candidates` (committee_cycle), and every row of `race_top_committee` and `committee_top_recipient` come from FEC `pas2` 24K rows (a committee's contribution to a candidate's committee) and `oth` rows (a committee's receipts from other committees). Those files are extracted but, at the time of planning, no silver table holds them; NEU-2057 (M4) was going to build `committee_transfer`. That silver table is pulled forward into NEU-2068 (M2), which blocks this one; its shape is the one §3 reads: `cycle, source, source_record_id, jurisdiction, from_committee_id, to_committee_id, candidate_id, amount, date, transaction_type, side` where `side` is `receipt` for an `oth` row (recorded by the receiving committee) and `disbursement` for a `pas2` 24K row (recorded by the giving committee). A gift to a candidate's committee appears once on each side; **a gold aggregate sums one side only**, never both (`tests/fixtures/fec/2024/expected.yaml`'s rule).

## 2. Layout

```
sql/gold/NN_<table>.sql        DuckDB SQL: CREATE TABLE <table> AS … over the silver views (§3)
sql/gold/ddl/<table>.sql       Postgres: CREATE TABLE gold_build.<table> (…) — explicit types
sql/gold/index/<table>.sql     Postgres: indexes on gold_build.<table>, run after COPY
sql/checks/gold_*.sql          DuckDB queries over the gold tables that must return no rows
src/fundlens/load/gold.py      load(): the loader (§4.1)
src/fundlens/publish/__init__.py
src/fundlens/publish/gold.py   swap(), rollback(), prune(): Postgres and R2 side of publish (§4.2–§4.5)
src/fundlens/publish/cloudflare.py   purge_zone(): the purge client (§4.3)
src/fundlens/cli.py            `load` and `publish` commands (§5)
src/fundlens/settings.py       CLOUDFLARE_ZONE_ID, CLOUDFLARE_API_TOKEN (§5)
src/fundlens/paths.py          helpers listed in §4.1 step 1 and §4.5
tests/seed.py                  STEPS += load, publish
tests/integration/test_load.py, test_publish.py; tests/unit/test_cloudflare.py (§6)
docs/adr/0007-gold-loads-by-duckdb-csv-and-postgres-copy.md
```

`GoldTable` is a `Literal` in `load/gold.py` naming the eleven M2 tables; `NN_<table>.sql` must name one of them, as `transform.runner._models` does for silver. `meta` is the exception: it has `ddl/meta.sql` but no `NN_meta.sql`; the loader inserts its one row from Python (§4.1 step 7).

The gold SQL is DuckDB SQL (the aggregates); the DDL and index files are Postgres SQL and name `gold_build.` explicitly, since that is the only schema the loader ever creates. Types are written by hand rather than derived from DuckDB's result schema so a change in a silver column's type cannot silently change a served column's type.

## 3. Gold tables (M2 content)

Conventions: every money column is `numeric(16,2)`, nets refunds (negative amounts are summed as they are), and is `0` where there is nothing to sum (`coalesce`, never NULL). `total_individual` is the sum of `contribution.amount` where `NOT is_self_funding`; `self_funding` is the sum where `is_self_funding`; neither includes the other. Top-N is 100, ranked by amount descending then by id ascending for a stable order. `cycles int[]` is `ARRAY[C]` in M2 (NEU-2059 merges cycles). Postgres arrays are written through the DuckDB macro `pg_array(list)` → `'{' || array_to_string(list, ',') || '}'`, which the loader registers before running the SQL, because DuckDB's CSV writer prints a list as `[…]` and Postgres reads `{…}`.

| Table | Postgres key / indexes | Columns and M2 rule |
|---|---|---|
| `meta` | `build_id text PK` | `published_at timestamptz` (NULL in `gold_build`; set by the swap, §4.2, so `gold.meta.published_at` is never NULL), `resolver_version text`, `model_version text` (NULL until M3), `precision numeric`, `recall numeric` (NULL until M3), `cycles jsonb NOT NULL` = `{"<C>": {"build_id": "<B>", "source_dates": {"cm": "YYYY-MM-DD", …}}}` with one entry per file in `fec.files.files_for(C)`, the date taken from the newest bronze key (`paths.bronze_dir`, key order is date order). `api.schemas.Meta.resolver_version` and `.model_version` become `str | None` to match. |
| `cycle` | `cycle int PK` | `race_count` (rows of `race`), `contribution_count bigint` (rows of `contribution`), `total_amount` (sum of every `contribution.amount`, self-funding included: `expected.yaml` `contributions.total_amount`). |
| `race` | `race_id text PK`; `UNIQUE (slug)`; `INDEX (cycle, office, state)` | From silver `race`: `cycle, office, state, district, is_special, slug`; `candidate_count` = rows of `race_candidate` for the race; `total_individual, total_committee, ie_support, ie_oppose` = sums over `race_candidate`. A race with no candidate has `0`s (the fixture's `2024-H-MD-08`). |
| `race_candidate` | `PK (race_id, candidate_id)` | One row per silver `candidate` with a non-null `race_id`: `name, party, incumbent_challenger_open, principal_committee_id`; `total_individual`, `self_funding` from `contribution` by `candidate_id`; `total_committee` = sum of `committee_transfer.amount` where `side = 'disbursement'` and `candidate_id` matches; `ie_support = 0, ie_oppose = 0`. |
| `race_top_committee` | `PK (race_id, rank)` | Top 100 giving committees per race: `committee_transfer` disbursements whose `candidate_id` is in the race, summed by `from_committee_id`, `kind = 'contribution'`, `name` from silver `committee`. No `kind = 'ie'` rows until NEU-2057. |
| `candidate` | `candidate_id text PK` | From silver `candidate`: `name, party, office, state, district`; `cycles = ARRAY[C]`. Every candidate of the cycle, including one with no race (the fixture's `H4MD09109`). |
| `candidate_cycle` | `PK (candidate_id, cycle)`; `INDEX (race_id)` (a race page lists its candidates) | `race_id` (nullable), `total_individual, total_committee, self_funding` as for `race_candidate`, `ie_support = 0, ie_oppose = 0`, `contributor_count int` NULL in M2 (silver `contribution` carries no contributor key before M3; NEU-2051 fills it). |
| `committee` | `committee_id text PK` | From silver `committee`: `name, type, designation, party, connected_org, is_conduit`; `cycles = ARRAY[C]`. |
| `committee_cycle` | `PK (committee_id, cycle)` | `total_individual`, `self_funding` from `contribution` by `recipient_committee_id`; `total_from_committees` = sum of `committee_transfer.amount` where `side = 'receipt'` and `to_committee_id` matches; `total_to_candidates` = sum where `side = 'disbursement'` and `from_committee_id` matches; `ie_total = 0`. **`self_funding` is added to the project spec's §7.1 column list**: a candidate committee's `total_individual` would otherwise either hide or include the candidate's own money (`expected.yaml` already keeps the two apart). |
| `committee_top_recipient` | `PK (committee_id, cycle, rank)` | Top 100 recipients of a committee's disbursements: `recipient_kind = 'candidate'`, `recipient_id = candidate_id`, `name` from silver `candidate`, summed by candidate. Committee-to-committee recipients (`recipient_kind = 'committee'`) arrive with NEU-2057, which owns the rule for not double-counting a 24K row against its `oth` twin. |
| `search_entity` | `PK (kind, id)`; `INDEX … USING gin (name gin_trgm_ops)` | One row per candidate (`weight = total_individual + total_committee`), committee (`weight = total_individual + total_from_committees`) and race (`id = race_id`, `name` = a readable label such as `2024 Senate MD`, `weight = total_individual`). `aliases text` nullable: the race's `slug`, the candidate's principal committee name, the committee's `connected_org`. Donor rows arrive in M3. |

Checks (`sql/checks/gold_*.sql`, each must return no rows): every `race.total_*` equals the sum over its `race_candidate` rows; every `race_candidate.race_id` exists in `race`; `candidate_cycle.total_individual` summed over all candidates with a race equals the sum of `race.total_individual`; every `race_top_committee.committee_id` and `committee_top_recipient.recipient_id` exists in `committee` / `candidate`; `rank` is 1..n without gaps per group; no `search_entity` row has a NULL `name`; `cycle` has exactly one row. The implementer adds any further invariant that falls out of the SQL.

## 4. Behaviour

### 4.1 `load` (`fundlens load --cycle C [--build-id B]`, no Kuma family)

1. **Resolve `B`.** When `--build-id` is omitted, `B` is the newest build with a `transformed` marker for `C` (`paths.markers_dir(cycle)` → list `markers/cycle=C/`, parse `build=` from the keys, keep those whose `transformed.json` exists). None → `typer.Exit(1)` with the hint `run fundlens transform --cycle C`.
2. **Require the inputs.** The `transformed` marker for `B`, and a partition for every silver table the gold SQL reads (`committee`, `candidate`, `contribution`, `committee_transfer`, `race`; not `candidate_committee_link`, whose linkage silver `contribution` already carries as `candidate_id`) under `silver/<table>/cycle=C/build=B/`. The `race` partition is written by `seats` and must be the same build: `seats`, `transform` and `load` share one `--build-id` (as `tests/seed.py` already does; the first-run runbook must too). A missing partition → `Exit(1)` naming the table and the command that writes it. Partitions absent from the local cache are downloaded from R2 to their local path first (ADR-0002); nothing is read from R2 directly.
3. **DuckDB.** Open with `runner.Limits` as `transform` does, `temp_directory` under `scratch/`, work dir `scratch/load-C-B/`. Register one view per silver table over its local partition (`read_parquet('…/*.parquet', hive_partitioning = false)`) as `silver.<table>`, in a schema of their own so the gold tables can carry the same names (`race`, `candidate`, `committee`), register `pg_array`, then run `sql/gold/*.sql` in filename order with `{cycle}` and `{build_id}` parameters.
4. **Checks.** Run `sql/checks/gold_*.sql`; any rows → `ChecksFailed` (the runner's exception type, reused) before Postgres is touched. Nothing is written, no marker.
5. **CSV.** `COPY <table> TO 'scratch/load-C-B/<table>.csv' (FORMAT csv, HEADER true)` per gold table; row counts taken here.
6. **Postgres, one transaction** (an autocommit connection, so psycopg's `conn.transaction()` is one real `BEGIN` … `COMMIT` rather than a savepoint inside an implicit transaction):
   `CREATE EXTENSION IF NOT EXISTS pg_trgm` — created in the default schema, **never** inside `gold_build`: an extension that lived in `gold_build` would be renamed with it and dropped by the next publish's `DROP SCHEMA gold_prev CASCADE`.
   `DROP SCHEMA IF EXISTS gold_build CASCADE; CREATE SCHEMA gold_build;`
   For each table: `ddl/<table>.sql`, then `COPY gold_build.<table> FROM STDIN (FORMAT csv, HEADER match)` streaming the CSV in 1 MiB chunks through `cursor.copy()`, then `index/<table>.sql` where the table has one, then `ANALYZE gold_build.<table>`.
   Commit. DDL is transactional in Postgres, so a failed load leaves no `gold_build` at all rather than a partial one.
7. **`meta`.** Inside the same transaction, after the tables: insert the one row (§3) with `published_at = NULL`.
8. **Marker and output.** Write the `loaded` marker (`row_counts` per gold table, `meta` included as `1`). Remove `scratch/load-C-B/`. Print `<table>: <n> rows` per table and the build id.

Re-running `load` for the same build is allowed and rebuilds `gold_build` from scratch (step 6 drops it).

### 4.2 The swap (`fundlens publish --cycle C`, Kuma family `publish`)

Preconditions: `gold_build` exists and its `meta.cycles` has `C`; otherwise, **resume mode** (§4.4) if it applies, else `Exit(1)` with `run fundlens load --cycle C`.

One transaction, these statements in this order:

```sql
BEGIN;
SET LOCAL lock_timeout = '10s';
UPDATE gold_build.meta SET published_at = now();
CREATE SCHEMA IF NOT EXISTS gold;            -- first publish ever: an empty gold, so the renames below are uniform
DROP SCHEMA IF EXISTS gold_prev CASCADE;
ALTER SCHEMA gold RENAME TO gold_prev;
ALTER SCHEMA gold_build RENAME TO gold;
COMMIT;
```

- **Why the drop comes first.** `DROP SCHEMA … CASCADE` needs an `AccessExclusiveLock` on every table it drops. `gold_prev` holds the build that stopped being live at the *last* publish, which no API query names (every query names `gold.` and resolves it at parse time), so the drop never waits on a reader. Renaming a schema locks only its `pg_namespace` row; a query already running against the old `gold` tables finishes on the OIDs it resolved.
- **Why `lock_timeout`.** A waiting `AccessExclusiveLock` request queues *behind* current readers and *ahead of* new ones, so a single stuck session on a `gold_prev` table would otherwise stall every new API request for as long as it lived. With the timeout the publish fails instead; `publish/gold.swap()` makes up to 3 attempts, 5 s apart, then raises.
- Readers see the old build or the new one, never an error or a half-loaded state: the whole swap commits at once, the API pool is autocommit with `prepare_threshold=None` (NEU-2030), and `tests/integration/test_api.py` already proves a renamed-in `gold` survives a live pool.
- Under psycopg, `SET LOCAL` and the DDL run as plain `conn.execute` calls inside `conn.transaction()`; no string formatting, there is nothing to parameterise.

After the commit the step **waits `PURGE_DELAY_SECONDS` = `api.cache.BUILD_ID_TTL_SECONDS + 15` (75 s)** before purging: the API re-reads the live `build_id` for its `ETag` at most once a minute, and a purge inside that window lets the edge store a new body under the old `ETag` for a week (`api/cache.py` docstring, spec §5.5). The wait is a `sleep` callable injected into `publish()`; the CLI passes `time.sleep`, tests pass a recorder.

### 4.3 The purge (`publish/cloudflare.py`)

`purge_zone(zone_id, token, *, post=…)` sends `POST https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache` with `Authorization: Bearer <token>`, `Content-Type: application/json` and body `{"purge_everything": true}`, over `urllib.request` like `heartbeat.py` (no new dependency; `httpx2` is dev-only). Success is HTTP 200 with `"success": true` in the JSON; anything else raises `PurgeFailed` with the status and the response's `errors`, after up to 3 attempts 5 s apart (a purge is idempotent). The token never reaches a log line: log the zone id and the status only.

Settings: `cloudflare_zone_id: str | None` (`CLOUDFLARE_ZONE_ID`) and `cloudflare_api_token: SecretStr | None` (`CLOUDFLARE_API_TOKEN`), both default `None`. With either unset (or empty: the prod compose file's `${CLOUDFLARE_ZONE_ID:-}` fallback) the purge is **skipped with one log line** (`cloudflare purge skipped: not configured`) and the publish continues without the 75 s wait, which exists only for the purge's sake: dev and CI have no zone, and `task db:seed` would otherwise idle for over a minute. `docker-compose.prod.yml` already passes both to `pipeline`; the token is the purge-only `fundlens-purge` token from `docs/runbooks/cloudflare-setup.md`.

### 4.4 After the purge: marker, prune, resume

- **`published` marker** for `(C, B)` where `B` is `gold.meta.build_id`, `row_counts` copied from the `loaded` marker (or `{}` if it is gone). `started_at` is when the publish command started.
- **Prune** (§4.5).
- **Resume mode.** A `PurgeFailed` (or a crash after the swap) leaves `gold` swapped with no `published` marker. Re-running `fundlens publish --cycle C` detects *no `gold_build`, `gold.meta.cycles[C].build_id = B`, no `published` marker for `(C, B)`* and does only the wait, the purge, the marker and the prune, never a second swap. This mirrors the marker-based resume the spec gives `run` (§5.1).

### 4.5 Pruning silver (spec §3.4: "builds older than the previous live one")

For cycle `C`, `live = gold.meta.cycles[C].build_id` and `prev = gold_prev.meta.cycles[C].build_id` when `gold_prev.meta` exists and names `C`. For every silver table (`paths.SilverTable`), list the builds under `silver/<table>/cycle=C/` (new helper `paths.silver_cycle_dir(table, cycle)`; parse `build=`); delete, in R2 and under `DATA_DIR`, every build **lexically older than `min(live, prev)`**, or older than `live` when there is no `prev` (the first publish ever, so a backfill's trial builds go at once; nothing live or rollback-able is older than `live`) (`build_id`s are `YYYYMMDDTHHMMSSZ`, so key order is time order). Builds newer than the live one are left alone: someone may have transformed the next build and not loaded it yet. Markers are never pruned (small, and the run history). Print how many builds and objects were removed. The API's itemized reader (NEU-2041) resolves its partition from `gold.meta`, so it only ever reads `live`, which is never pruned; `prev` stays for `--rollback`.

### 4.6 Rollback (`fundlens publish --rollback`, Kuma family `publish`)

Requires `gold_prev` with a `meta` row, and `gold` with one to swap out; otherwise `Exit(1)` (`nothing to roll back to` / `from`). One transaction with the same `lock_timeout` and retry:

```sql
ALTER SCHEMA gold RENAME TO gold_rollback;
ALTER SCHEMA gold_prev RENAME TO gold;
ALTER SCHEMA gold_rollback RENAME TO gold_prev;
```

Then the same wait and purge as §4.2–§4.3. Prints the build id now live and the one now in `gold_prev`. **No marker, no prune**: the rolled-back build's `published` marker stays (it was published), and a second `--rollback` swaps forward again, which is the documented way to undo a rollback (NEU-2063's runbook). `published_at` is left as it was. `--cycle` is not needed with `--rollback`.

## 5. CLI and settings

```
fundlens load    --cycle C [--build-id B]          # no Kuma family (hand backfills must not touch `weekly`)
fundlens publish --cycle C                          # family: publish
fundlens publish --rollback                         # family: publish
```

Both go through `cli.step` like the existing commands; `--cycle` is validated with `seat_calendar.check_cycle`; `--cycle` without `--rollback` is required and `--rollback` with `--cycle` is a usage error (exit 2). The CLI functions stay thin: the work is `load.gold.load(...)`, `publish.gold.publish(...)` and `publish.gold.rollback(...)`, each callable from tests without the CLI (spec §5.1).

New settings (`settings.py`, with the existing comment style): `cloudflare_zone_id`, `cloudflare_api_token` (§4.3).

## 6. Tests (spec §12; Postgres and MinIO from the compose stack, no network)

Integration, `tests/integration/test_load.py`, reusing `test_transform.py`'s `put_bronze`, `seats_report`, `transform` helpers with one `BUILD`:

- `load` on the fixture writes every gold table; `race`, `race_candidate`, `candidate_cycle`, `committee_cycle` totals equal `expected.yaml` (`total_individual`, `total_committee`, `self_funding`, `total_from_committees`, `total_to_candidates`, `candidate_count`; `ie_*` are `0`); `cycle.total_amount` equals `contributions.total_amount`; `gold_build.meta` has `published_at IS NULL` and the `cycles` shape of §3; the `loaded` marker's `row_counts` match the tables; the GIN index exists (`pg_indexes`).
- `load` without `--build-id` picks the newest transformed build; without any → exit 1 naming `transform`; with the `race` partition under another build → exit 1 naming `seats`.
- A failing gold check (a check file in a temporary `sql_dir` that always returns a row) leaves no `gold_build` schema and no marker.
- `load` twice for the same build succeeds (rebuilds `gold_build`).

Integration, `tests/integration/test_publish.py`:

- First publish on a database with no `gold`: afterwards `gold.meta.build_id = B`, `published_at` set, `gold_prev` exists and is empty, `gold_build` gone, `published` marker written, the fake purge recorded one `POST` with the right URL, bearer token and body, and the injected sleep was asked for 75 s before it.
- Second publish of a newer build moves the first to `gold_prev`; **a thread polling `SELECT build_id FROM gold.meta` on its own autocommit connection throughout sees only `{B1, B2}` and no exception** (the ticket's DoD).
- Prune: with builds `B0 < B1 < B2 < B3` in silver and `B2` published over `B1`, `B0` is deleted (R2 and local), `B1`, `B2` and `B3` remain.
- `--rollback` restores `B1` as `gold.meta.build_id`, leaves `B2` in `gold_prev`, and the fake purge records a second purge; a second `--rollback` brings `B2` back.
- Purge failure: the fake answers 500 → `PurgeFailed`, exit non-zero, no `published` marker, `gold` swapped; re-running `publish` does not swap again, purges, writes the marker.
- `publish` with no `gold_build` and nothing to resume → exit 1 naming `load`; `--rollback` with no `gold_prev` → exit 1.
- Unconfigured zone/token → publish succeeds, no purge call, the skip is logged.

Unit, `tests/unit/test_cloudflare.py`: request shape; retries then `PurgeFailed`; no token in the exception text. `tests/unit/test_paths.py`: the new helpers. The `test_api.py` seed for `gold.meta` keeps working (`resolver_version`/`model_version` optional).

`tests/seed.py`: `STEPS` gains `("load", "--cycle", …)` and `("publish", "--cycle", …)`, so `task db:seed` ends with a live `gold` (the purge is skipped in dev).

## 7. Acceptance criteria (the ticket's DoD, as amended by this spec)

- [ ] After `fundlens load` + `publish` on the fixture, `gold.race` totals equal `expected.yaml`, and a concurrent connection polling `gold.meta.build_id` through the swap sees either the old or the new build, never an error.
- [ ] `fundlens publish --rollback` restores the previous `build_id` and the fake purge endpoint records a second purge.
- [ ] §8 of this spec records the fixture timings of `load` (DuckDB aggregate + CSV, and `COPY` + indexes, separately). The real-cycle timing is NEU-2046's `load seconds` in `docs/capacity.md`.
- [ ] `task db:seed` leaves `GET /v1/meta` answering 200 with the seeded build.

## 8. Measurements (filled in by the implementation)

Fixture-sized, so these are floors on overhead, not a forecast: 11 gold tables, 1,066 gold rows in all, and `task db:seed`'s `fundlens load` prints both halves (`aggregates … s, copy … s`). The real cycle's `load seconds` lands in `docs/capacity.md` with NEU-2046.

| Where | Rows (contribution) | DuckDB aggregates + CSV | `COPY` + indexes + `ANALYZE` | Whole `load` |
|---|---|---|---|---|
| Fixture 2024, dev container (Apple Silicon, Docker Desktop, 2026-10-30) | 275 | 0.14 s | 0.04 s | 0.21 s (`loaded` marker `duration_s`; `publish` 0.005 s before its wait) |
| Real 2024 on the Robot box | | see `docs/capacity.md` (NEU-2046) | | |

## 9. Open items left to later tickets

- `race_top_committee` `kind = 'ie'` rows, all `ie_*` values, committee-to-committee recipients: NEU-2057.
- `contributor_count`, donor tables, `search_entity` donor rows, `precision`/`recall`/`resolver_version`/`model_version`: M3.
- Multi-cycle `gold.meta.cycles` and `cycles int[]` merging: NEU-2059.
- Whether index creation should move after `COPY` for the large donor tables, and whether `COPY … (FORMAT binary)` beats CSV there: measure in M3 against §8.
