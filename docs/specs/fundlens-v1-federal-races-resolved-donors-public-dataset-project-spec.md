# fundlens v1: federal races, resolved donors, public dataset — project spec

Linear initiative: fundlens (I-16). Project: P-NEU-105. Team: NEU. Glossary: `CONTEXT.md` at the repo root. Decisions and their rationale: `docs/adr/`. Original brief: `docs/campaign-finance-handover.md`.
This spec is the shared reference for every ticket in the project. A ticket needs its own `/planit` spec only where this document is silent.

Reference implementations: upcoming-movies-backend (`~/projects/upcoming-movies/upcoming-movies-backend`) for the Coolify compose, Dockerfile, Taskfile, container-only hooks, OTel + Bugsink wiring and Kuma push deadman; closinglineup (`~/projects/closinglineup/frontend`) for the React + Vite + TypeScript + ECharts frontend toolchain. Where this spec says **"port from"**, copy the file, rename, and change only what this spec calls for.

## 1. Purpose

Build fundlens, from an empty repo, into a free public campaign-finance platform: donor, candidate and committee money for every federal race since 1980, presented by race, with individual donors correctly resolved across name, employer and address variants. **The resolved dataset is the product; the web app is its demo.** v1 proves the whole chain on one machine: FEC bulk → canonical Parquet → entity resolution → gold aggregates in Postgres → atomic publish → cached site, rebuilt weekly for the current cycle, with the resolved tables published as open Parquet snapshots.

The ~2025 attempt failed on cost (per-execution Azure billing) and data quality (no donor rollup, double-counted earmarks). Both are design constraints here, not afterthoughts.

**Non-goals for v1:** state data (the canonical schema anticipates it; no loader is built), paid tier / API keys / SLAs, industry or sector coding, lobbying data, sub-weekly freshness, municipal races, a national cross-cycle donor leaderboard, LLM calls in any request path, Dagster/Prefect.

## 2. Decisions (summary; see ADRs for rationale)

| Area | Decision |
|---|---|
| Shape | Batch ELT on one machine; no queues, no workers, no managed DB (ADR-0001). One scheduled job rebuilds one cycle and republishes. |
| Storage of record | Cloudflare R2 holds bronze, silver, resolution snapshots and the public dataset; the box's NVMe is a cache (ADR-0002). Storage Box keeps pg_dump only. |
| Repo | One public MIT repo `neuroticsasquat-ch/fundlens`: Python package `fundlens` (pipeline + API, one image, per-service entrypoints) and `frontend/` (SPA) (ADR-0003). |
| Runner | v1 runs on the Hetzner Robot box `music-box-dancer` under Coolify. Every step reads/writes R2 so it can move to an ephemeral Hetzner Cloud runner later with no code change. Full-rebuild wall time is measured and recorded (§10.6). |
| Transforms | Plain SQL files under `sql/` executed by a thin Python runner over DuckDB, parameterized by cycle. No dbt. |
| Itemized detail | Served from silver Parquet by in-process DuckDB inside the API; only aggregates and search live in Postgres (ADR-0006). |
| Race universe | A generated seat calendar per cycle; candidates attach to it via `cn`/`ccl`. Filings that match no seat are flagged, never create races. |
| Resolution | Splink 4 (DuckDB backend) over unique contributor keys; crosswalk gives sequential integer `donor_id`s; manual overrides in git; LLM adjudication of high-dollar ambiguous clusters; precision/recall scored against DIME (ADR-0005). |
| Earmarks | Count the recipient side; drop `MEMO_CD='X'` and `24T` rows; keep the conduit as `conduit_committee_id` (ADR-0004). |
| Self-funding | A candidate's own money (incl. loans) is `self_funding` on the candidate, never a top donor. |
| Web app | React + Vite + TypeScript SPA deployed by Cloudflare Workers Builds from `frontend/` (root directory `frontend`, watch paths `frontend/**`). Public read-only FastAPI JSON API on Coolify at `api.fundlens.org`, Cloudflare-proxied, long TTLs, purged on publish. |
| Domain | `fundlens.org` (owned): apex → Worker; `api.fundlens.org` → Coolify; `data.fundlens.org` → public R2 bucket custom domain. |
| Database | Postgres 18, dedicated Coolify service in the fundlens project, own volume, tuned `shared_buffers`/`work_mem`. |
| Deploy | Coolify Docker Compose resource built from GitHub (`docker-compose.prod.yml`): services `api`, `pipeline` (same image, idle; Coolify scheduled task execs the CLI), `postgres`. "Source commit availability" on. |
| Observability | NS standard: Bugsink DSN for crashes (crash, not items), OTel logs/traces to SigNoz, one ops Uptime Kuma push monitor per job family, alerts to Discord. |
| Licenses | Code MIT. Dataset CC BY 4.0 with an 11 CFR 104.15 notice. |
| Toolchain | Python 3.13, uv, ruff, pyright strict, pytest, typer, FastAPI, uvicorn, psycopg 3 (plain SQL, no ORM), Alembic for the `app` schema only, DuckDB, Splink, nameparser, pyarrow, boto3, pydantic-settings, OTel, sentry-sdk. Frontend: pnpm, Vite, React, TypeScript, React Router, TanStack Query, ECharts, oxlint, vitest, Node 24, OpenAPI-generated client types. |
| Local dev | Docker-only compose; every hook and check runs in the container via `docker compose exec -T`; go-task Taskfile per `tbc-localdev-infra/CONVENTIONS.md`. |
| CI | GitHub Actions on every PR (backend: ruff, pyright, pytest incl. the fixture-cycle end-to-end; frontend: tsc, oxlint, vitest). Dependabot → `updates/dependencies` with the standard rulesets and weekly merge workflow. |
| Branch flow | Greenfield: every ticket branches from and PRs into `main`. No release branch. |

## 3. Architecture

### 3.1 Repo layout

```
pyproject.toml  uv.lock  Dockerfile  docker-compose.yml  docker-compose.prod.yml  Taskfile.yml
.pre-commit-config.yaml  .github/workflows/{ci,merge-main-into-dependencies}.yml  .github/dependabot.yml
CLAUDE.md  CONTEXT.md  LICENSE  README.md
docs/  adr/  specs/  plans/  campaign-finance-handover.md  dataset/  (schema docs published with the dataset)
sql/
  silver/   01_committee.sql 02_candidate.sql 03_candidate_committee_link.sql 04_contribution.sql
            05_contributor.sql 06_independent_expenditure.sql
  gold/     01_race.sql … (one file per gold table, numbered in dependency order)
  checks/   *.sql  (assertions run after silver and after gold; a failing check aborts the run)
resolution/
  overrides.yaml            # human merge/split assertions (ADR-0005)
  prompts/adjudicate_v1.md  # versioned adjudication prompt
src/fundlens/
  __init__.py  __main__.py
  cli.py                 # typer: extract | transform | resolve | load | publish | run | seats | dataset | api | health
  settings.py            # pydantic-settings; all env in one place                (port from upmovies)
  logging.py             # JSON log formatter                                      (port)
  telemetry.py           # OTel resource + sentry-sdk → Bugsink                     (port)
  heartbeat.py           # Kuma push client, one URL per job family                 (port, adapt)
  r2.py                  # boto3 S3 client for R2: get/put/list/exists, multipart, atomic rename
  paths.py               # bronze/silver/scratch path layout, local and R2 (§3.4)
  markers.py             # per-step completion markers in R2 (§5.1)
  fec/
    files.py             # bulk file catalogue: name, first cycle, URL pattern, header file, dtypes
    extract.py           # download zips per cycle → bronze in R2; idempotent
    headers.py           # column names from FEC data_dictionaries header CSVs (vendored copies)
  transform/
    runner.py            # executes sql/silver/*.sql and sql/checks/*.sql in DuckDB with params
    seats.py             # seat calendar generator + specials table loader
  resolve/
    normalize.py         # name parsing (nameparser), suffix/punct stripping, ZIP5, employer/occupation canon
    model.py             # Splink settings: blocking rules, comparisons, training
    cluster.py           # predict + connected components → clusters
    crosswalk.py         # contributor_key → donor_id assignment, merges/splits, redirects
    overrides.py         # load + apply resolution/overrides.yaml
    adjudicate.py        # batch LLM adjudication (DeepInfra), writes app.adjudication
    validate.py          # DIME join + precision/recall report
  load/
    gold.py              # build gold_build schema from sql/gold, swap, drop previous (§5.5)
    db.py                # psycopg 3 connection + pool helpers (prepare_threshold=None, §7.3)
  publish/
    cloudflare.py        # zone purge via API
    dataset.py           # snapshot silver + crosswalk + overrides to the public bucket (§9)
  api/
    app.py  deps.py  cache.py
    routers/ cycles.py races.py candidates.py committees.py donors.py search.py meta.py dataset.py
    itemized.py          # DuckDB-over-Parquet reader for row lists (ADR-0006)
    schemas.py           # pydantic response models (the OpenAPI contract)
migrations/              # Alembic, `app` schema only
tests/
  unit/  integration/  e2e/
  fixtures/fec/2024/     # synthetic mini-cycle in FEC bulk format (§12)
  fixtures/dime/         # tiny DIME-shaped file for the validator
frontend/
  package.json  pnpm-lock.yaml  vite.config.ts  tsconfig.json  wrangler.jsonc  .oxlintrc.json
  src/  api/ (generated types + client)  routes/  components/  charts/
```

### 3.2 Services

| Service | Image | Role |
|---|---|---|
| `api` | fundlens (prod target) | `uvicorn fundlens.api.app:app --proxy-headers --forwarded-allow-ips="*"`. Mounts the silver volume read-only. |
| `pipeline` | fundlens (prod target) | Idle (`sleep infinity`). Coolify scheduled tasks `docker exec` the CLI in it. Mounts silver + scratch + bronze volumes read-write. Memory limit 40 GB; DuckDB `memory_limit` 28 GB. |
| `postgres` | postgres:18 | Schemas `app` (authored, migrated), `gold` (live, rebuilt), `gold_prev` (rollback), `gold_build` (in progress). |
| Worker | Cloudflare | Serves the SPA at `fundlens.org`. |
| R2 | Cloudflare | `fundlens-data` (private): bronze, silver, resolution snapshots, markers. `fundlens-public` (public, custom domain `data.fundlens.org`): dataset snapshots. |

### 3.3 Data flow

```
FEC bulk zips ─extract─▶ R2 bronze/<cycle>/<file>/<download_date>.zip  (current cycle also on NVMe)
                 │
            transform (DuckDB reads zips directly) ─▶ silver/<table>/cycle=<c>/build=<build_id>/*.parquet  (NVMe → R2)
                 │
            resolve (Splink over contributor keys) ─▶ app.crosswalk, app.adjudication, silver.contribution.donor_id
                 │
            load  (sql/gold → gold_build) ─▶ swap gold_build → gold
                 │
            publish ─▶ markers, Cloudflare purge, (weekly) dataset snapshot to fundlens-public
```

### 3.4 Storage layout

Local (Coolify volumes, all under `/data/fundlens/`): `bronze/` (current cycle only), `silver/`, `scratch/` (DuckDB `temp_directory`, `max_temp_directory_size` 60 GB), `resolution/` (Splink model + DuckDB working file).

R2 `fundlens-data`:

```
bronze/cycle=2026/indiv/2026-11-02.zip          one object per (cycle, file, download date); historical cycles download once
silver/<table>/cycle=<cycle>/build=<build_id>/part-0000.parquet   zstd, row groups ≤ 1M rows
silver/contribution/cycle=<cycle>/build=<build_id>/bucket=<00..ff>/part-*.parquet   bucket = donor_id % 256, zero-padded hex
resolution/build=<build_id>/{crosswalk,adjudication}.parquet       snapshot taken at publish
markers/cycle=<cycle>/build=<build_id>/{extracted,transformed,resolved,loaded,published}.json
```

`build_id` = `YYYYMMDDTHHMMSSZ` of the run start. Only the rebuilt cycle gets a new build directory; `gold.meta` records the live `build_id` per cycle, and the API resolves silver paths from it. Builds older than the previous live one are pruned at the end of a successful publish.

Disk budget (federal): silver 30–60 GB, gold 10–30 GB, resolution < 5 GB, bronze ~10 GB, scratch ≤ 60 GB. Never keep historical raw locally. Watch ClickHouse (SigNoz) retention on the same disk.

## 4. Canonical schema (silver)

Source-agnostic from day one: every table carries `source` (`fec`) and `jurisdiction` (`US`), so state loaders in a later project write into the same tables. Column names are snake_case; FEC raw column names appear only inside `sql/silver/`.

| Table | Key | Columns (beyond key) |
|---|---|---|
| `committee` | `(cycle, committee_id)` | `name, treasurer, street, city, state, zip, designation, type, party, filing_frequency, org_type, connected_org, candidate_id, is_conduit` |
| `candidate` | `(cycle, candidate_id)` | `name, party, election_year, office (H/S/P), state, district (2-char, '00' for S/P), incumbent_challenger_open, status, principal_committee_id, race_id` |
| `candidate_committee_link` | `(cycle, candidate_id, committee_id)` | `committee_type, designation, linkage_id` |
| `race` | `race_id` | `cycle, jurisdiction, office, state, district, is_special, slug` (from the seat calendar, §5.2) |
| `contributor` | `contributor_key` | `name_raw, name_first, name_last, name_suffix, zip5, city, state, employer_raw, employer_norm, occupation_raw, occupation_norm, contribution_count, amount_total, first_cycle, last_cycle` |
| `contribution` | `(cycle, source, source_record_id)` | `jurisdiction, contributor_key, donor_id, recipient_committee_id, candidate_id (via ccl, nullable), amount, date, transaction_type, entity_type, report_type, amendment_indicator, memo_text, conduit_committee_id (nullable), is_self_funding, image_num, file_num` |
| `committee_transfer` | `(cycle, source, source_record_id)` | from `oth`: `from_committee_id, to_committee_id, amount, date, transaction_type` |
| `independent_expenditure` | `(cycle, source, source_record_id)` | from `pas2` types 24A/24E (and 24C/24F/24N retained with `kind`): `committee_id, candidate_id, race_id, support_oppose (S/O), amount, date, transaction_type, kind` |

Rules applied in `sql/silver/04_contribution.sql`:
- Source files `indiv` (individual contributions). Keep `ENTITY_TP IN ('IND','CAN')`; `CAN` rows whose `NAME` resolves to the recipient's own candidate are `is_self_funding = true`.
- **Earmarks (ADR-0004):** drop rows with `MEMO_CD = 'X'`; drop rows with `TRANSACTION_TP = '24T'`; when the kept row's `MEMO_TEXT` names a conduit (`EARMARK`, `ACTBLUE`, `WINRED` patterns) or `OTHER_ID` is a committee with `is_conduit`, set `conduit_committee_id`.
- Amendments: FEC bulk already contains the latest version of each record per cycle snapshot; no amendment reconciliation in v1. `amendment_indicator` is retained.
- Negative amounts (refunds, type `22Y` etc.) are kept and net out in aggregates.
- `source_record_id` = FEC `SUB_ID`.
- `candidate_id` on a contribution = the candidate linked to `recipient_committee_id` in `ccl` for that cycle, when the committee is a principal or authorized committee (`CMTE_DSGN IN ('P','A')`); else null.

FEC bulk files (`https://www.fec.gov/files/bulk-downloads/<cycle>/<file><yy>.zip`, pipe-delimited, no header; headers from `data_dictionaries/<file>_header_file.csv`, vendored under `src/fundlens/fec/headers/`):

| File | Table | First cycle |
|---|---|---|
| `cm` | committee | 1980 |
| `cn` | candidate | 1980 |
| `ccl` | candidate_committee_link | 2000 (earlier cycles link via `cn.CAND_PCC` and `cm.CAND_ID` only) |
| `indiv` | contribution | 1980 |
| `pas2` | independent_expenditure (+ committee→candidate contributions) | 1980 |
| `oth` | committee_transfer | 1980 |
| `oppexp` | not loaded in v1 (operating expenditures) | 2004 |

`fundlens.fec.files` is the single catalogue; the first ticket that touches a file name adds it there with its first cycle.

## 5. Pipeline

### 5.1 CLI and idempotency

```
fundlens extract   --cycle 2026 [--file indiv]
fundlens transform --cycle 2026
fundlens resolve   [--cycle 2026 | --full]          # incremental by default; --full re-resolves all cycles
fundlens load      --cycle 2026
fundlens publish   --cycle 2026 [--dataset]          # dataset snapshot only on the weekly run
fundlens run       --cycle 2026 [--dataset]          # extract → transform → resolve → load → publish
fundlens seats     --cycle 2026                      # regenerate the seat calendar
fundlens dataset   --snapshot                        # publish a dataset snapshot from the live build
fundlens health                                      # exit 0 iff Postgres + R2 reachable
```

Every step writes a completion marker to R2 (`markers/...`) with `build_id`, row counts and timing. `run` skips a step whose marker exists for this `build_id`; a crashed run is resumed by re-running `run` with `--build-id`. The idempotency check for extract is "does the silver partition for this cycle exist and is the bronze download date unchanged", never "is the zip on disk". Each step is also a Python function so tests call it without the CLI.

Every CLI entry is wrapped: Kuma push `/start` and `/` on success, `/fail` on exception; the exception is reported to Bugsink with `pipeline_mode=<step>` and re-raised (crash, not items).

### 5.2 Seat calendar (`fundlens seats`)

For a cycle: all House districts under the apportionment in force (a vendored `apportionment.csv`: state, seats, first cycle), delegate seats (DC, PR resident commissioner, AS, GU, MP, VI), the Senate class up that cycle (`senate_classes.csv`: state, class), specials from `specials.csv` (cycle, office, state, district, note; hand-maintained), and President every cycle divisible by 4. `race_id` = `{cycle}-{office}-{state}-{district}[-special]`; `slug` = `{cycle}/{house|senate|president}/{STATE}[-{DD}][-special]`. A candidate filing whose `(office, state, district)` matches no seat is written to `app.unmatched_filing` and surfaced in `fundlens seats --report`; it does not create a race.

### 5.3 Transform

`transform.runner` opens DuckDB with `memory_limit`, `temp_directory`, `threads` from settings, registers the bronze zips for the cycle via `read_csv` (pipe delimiter, vendored column names, all-varchar then cast), runs `sql/silver/*.sql` in filename order with `{cycle}` and `{build_id}` parameters, writes each table to the local silver path, runs `sql/checks/*.sql` (every check is a query that must return zero rows), then uploads the partition to R2 and writes the `transformed` marker. Any check failure aborts before upload.

### 5.4 Resolve — see §6.

### 5.5 Load and publish

`load.gold` creates `gold_build`, runs `sql/gold/*.sql` (DuckDB computes the aggregates from silver and writes CSV/Parquet; Postgres `COPY`s them; or DuckDB's postgres extension writes directly, decided in the ticket), creates indexes, runs `sql/checks/gold_*.sql`, writes `gold_build.meta`. `publish` then, in one transaction: `DROP SCHEMA IF EXISTS gold_prev CASCADE; ALTER SCHEMA gold RENAME TO gold_prev; ALTER SCHEMA gold_build RENAME TO gold;` then purges the Cloudflare zone, writes the `published` marker, snapshots `app.crosswalk` and `app.adjudication` to R2, prunes old silver builds, and (with `--dataset`) runs the dataset snapshot (§9). Readers never see a half-loaded state. `gold_prev` is the rollback: `fundlens publish --rollback` swaps it back.

### 5.6 Schedule

One Coolify scheduled task on the `pipeline` service: Sunday 03:00 box time, `fundlens run --cycle <current> --dataset`. The current cycle = the next even year ≥ today's year (2026 until 2027-01-01, then 2028). Historical cycles are built once by `fundlens run --cycle <c>` by hand (the backfill milestone) and never rebuilt unless `--full` resolution changes `donor_id`s, in which case every cycle's gold is reloaded.

## 6. Entity resolution

Only individuals are resolved; committees and candidates carry FEC IDs.

1. **Contributor keys.** `sql/silver/05_contributor.sql` reduces ~400M contribution rows to unique `(name_norm, zip5, employer_norm, occupation_norm)` tuples (tens of millions), each with counts and totals. Resolution runs over these.
2. **Normalization (`resolve.normalize`).** `nameparser` → first/middle/last/suffix; uppercase, strip punctuation and suffixes (JR, SR, III, MD, ESQ); ZIP5; employer and occupation canonicalized by a rule table (`SELF-EMPLOYED`, `RETIRED`, `NOT EMPLOYED`, `N/A` → null; `INC`, `LLC`, `CORP` stripped; a small alias YAML for the top employers). `usaddress`/libpostal are not used in v1 (street is not in `indiv`).
3. **Splink 4** (`resolve.model`), DuckDB backend, `link_type="dedupe_only"`. Blocking rules for prediction: `(last_name_soundex, zip3)`, `(last_name, first_initial, state)`, `(employer_norm, last_name)`. Comparisons: first name (Jaro-Winkler levels), last name (exact / JW), zip5 (exact / zip3), city+state, employer_norm (exact / JW), occupation_norm. `u` by random sampling; `m` by EM on each blocking rule; the trained model is saved as JSON under `resolution/` in R2 and reused by incremental runs.
4. **Clustering.** `predict(threshold_match_probability=0.9)` → `cluster_pairwise_predictions_at_threshold(0.95)`; thresholds are settings with these defaults. Connected components give clusters of contributor keys.
5. **Overrides (`resolution/overrides.yaml`).** Schema: a list of `merge: [contributor_key, …]` and `split: {contributor_key: …, from: donor_id}` entries, each with `reason` and `added`. Applied after clustering, before the crosswalk. A test validates the file.
6. **Crosswalk (`app.crosswalk`: `contributor_key PK, donor_id bigint, assigned_at, build_id`).** For each cluster: if its members already carry donor_ids, the cluster takes the one covering the most contribution dollars; members carrying a different id are re-pointed (a merge) and `app.donor_redirect(old_id → new_id)` records it; a never-seen key gets `nextval(app.donor_id_seq)`. A cluster that splits keeps the id on the larger-dollar half; the other half gets a new id. `donor_id`s are never reused.
7. **Canonical display.** `gold.donor.display_name` = the most frequent `name_raw` variant weighted by amount; employer/occupation/city/state likewise.
8. **Adjudication (`resolve.adjudicate`).** Candidates: clusters (or pairs of clusters that share last name + zip3) whose total ≥ `ADJUDICATE_MIN_AMOUNT` (default $50,000) and whose match probability lies in `[0.6, 0.95)` or whose members disagree on employer. Batched to DeepInfra (OpenAI-compatible; `ADJUDICATE_MODEL` default `deepseek-ai/DeepSeek-V4-Flash`; time a model before changing it) with `resolution/prompts/adjudicate_v1.md`, structured JSON reply `{decision: merge|split|unsure, confidence, reason}`. Results go to `app.adjudication (cluster_fingerprint, model, prompt_version, decision, confidence, reason, decided_at)` and are applied like overrides when `confidence ≥ 0.8`. Never called from the API.
9. **Validation (`resolve.validate`).** Join DIME contributor records (Bonica, Stanford; `bonica.cid`) to FEC `SUB_ID`s by (date, amount, recipient committee, normalized name) and compute pairwise precision/recall of fundlens clusters against `bonica.cid` on the matched subset, overall and for the top 10k contributors by dollars. The report is written to `gold.meta` and shown on the methodology page. DIME covers through 2024; check its terms of use before download.
10. **Incremental weekly.** Only the current cycle's new contributor keys are linked (against the full contributor table, using the saved model); existing keys keep their donor_id. `--full` re-trains and re-clusters everything and is only run when the model or normalization changes.

**Hard cases, each a pytest case on the fixture cycle:** Musk (name/employer/address variants roll up), a conduit earmark pair (counted once), a self-funding loan (not a top donor), an employer-variant rollup (`SPACEX` / `SPACE EXPLORATION TECHNOLOGIES`), two different people sharing a common name in different states (not merged), a merge override, a split override.

## 7. Gold schema and API

### 7.1 Gold tables (Postgres `gold`, rebuilt every run)

| Table | Content |
|---|---|
| `meta` | one row: `build_id, published_at, resolver_version, model_version, precision, recall, cycles jsonb (cycle → live build_id, source download dates)` |
| `cycle` | `cycle, race_count, contribution_count, total_amount` |
| `race` | `race_id, cycle, office, state, district, is_special, slug, candidate_count, total_individual, total_committee, ie_support, ie_oppose` |
| `race_candidate` | `race_id, candidate_id, name, party, incumbent_challenger_open, principal_committee_id, total_individual, total_committee, self_funding, ie_support, ie_oppose` |
| `race_top_donor` | `race_id, rank (≤100), donor_id, display_name, amount, candidates jsonb [{candidate_id, amount}]` |
| `race_top_committee` | `race_id, rank, committee_id, name, amount, kind (contribution/ie)` |
| `candidate` | `candidate_id, name, party, office, state, district, cycles int[]` |
| `candidate_cycle` | `candidate_id, cycle, race_id, total_individual, total_committee, self_funding, ie_support, ie_oppose, contributor_count` |
| `candidate_top_donor` | `candidate_id, cycle, rank, donor_id, display_name, amount` |
| `committee` | `committee_id, name, type, designation, party, connected_org, is_conduit, cycles int[]` |
| `committee_cycle` | `committee_id, cycle, total_individual, total_from_committees, total_to_candidates, ie_total` |
| `committee_top_donor` | `committee_id, cycle, rank, donor_id, display_name, amount` |
| `committee_top_recipient` | `committee_id, cycle, rank, recipient_kind (candidate/committee), recipient_id, name, amount` |
| `donor` | `donor_id, display_name, employer, occupation, city, state, zip5, total_all_cycles, first_cycle, last_cycle, contributor_key_count` |
| `donor_cycle` | `donor_id, cycle, amount, contribution_count` |
| `donor_top_recipient` | `donor_id, rank, recipient_kind, recipient_id, name, amount` (all cycles) |
| `donor_redirect` | `old_donor_id, donor_id` |
| `search_entity` | `kind (donor/candidate/committee/race), id, name, aliases text, weight numeric`; `GIN (name gin_trgm_ops)` |

Top-N = 100 everywhere. All aggregates net refunds. "No on-request aggregation": every endpoint is a primary-key or indexed lookup on these tables, or a single-partition DuckDB row scan.

### 7.2 API (`api.fundlens.org/v1`, public, unauthenticated, read-only)

| Endpoint | Source |
|---|---|
| `GET /v1/meta` | `gold.meta` |
| `GET /v1/cycles` · `GET /v1/cycles/{cycle}/races?office=&state=` | `gold.cycle`, `gold.race` |
| `GET /v1/races/{cycle}/{office}/{state}` · `…/{state}-{district}` · `…?special=1` | `race`, `race_candidate`, `race_top_donor`, `race_top_committee` |
| `GET /v1/candidates/{id}` · `GET /v1/candidates/{id}/contributions?cycle=&cursor=` | gold · DuckDB scan of `contribution` for `candidate_id` (cycle partition) |
| `GET /v1/committees/{id}` · `…/contributions?cycle=&cursor=` | gold · DuckDB |
| `GET /v1/donors/{id}` · `…/contributions?cycle=&cursor=` | gold (301 via `donor_redirect`) · DuckDB scan of `bucket=donor_id % 256` |
| `GET /v1/search?q=&kind=` | `search_entity` trigram, top 20 |
| `GET /v1/dataset` | list of snapshots from the public bucket manifest |
| `GET /healthz` | Postgres + silver volume reachable |

Responses carry `Cache-Control: public, max-age=3600, s-maxage=604800` and `ETag: <build_id>`; Cloudflare caches everything under `api.fundlens.org` and `publish` purges the zone. Cursor pagination on row lists (page size 100). Errors are RFC 9457 problem details. CORS allows `https://fundlens.org`. A Cloudflare rate-limiting rule (ops setting, not code) caps `/v1/*` per IP. The OpenAPI document is the contract: `frontend/src/api/` is generated from it in CI and a drift check fails the build.

### 7.3 Postgres access

psycopg 3 with a small pool; `prepare_threshold=None` so no server-side prepared plan outlives a schema swap; every query names `gold.` explicitly (no reliance on `search_path`). Alembic manages only `app` (`crosswalk`, `donor_redirect`, `adjudication`, `unmatched_filing`, `resolution_quality`, `donor_id_seq`). `gold*` schemas are owned by the pipeline and never migrated.

## 8. Frontend (`frontend/`)

Routes mirror the API: `/`, `/cycles/{cycle}` (race index by office and state), `/race/{cycle}/{office}/{state}[-{district}]`, `/candidate/{id}`, `/committee/{id}`, `/donor/{id}`, `/search?q=`, `/dataset`, `/methodology`. Each page is one or two TanStack queries against the API; tables sort client-side; ECharts for the per-cycle totals and the race split. Visual baseline: port closinglineup's Vite/TS/oxlint/vitest config and layout shell; no component library beyond what closinglineup uses. `wrangler.jsonc` declares a static-assets Worker with SPA fallback; Workers Builds: root directory `frontend`, build command `pnpm install --frozen-lockfile && pnpm build`, watch paths `frontend/**`, production branch `main`, preview deployments on PRs; `VITE_API_BASE_URL` = `https://api.fundlens.org`. Dark/light per system preference. No analytics in v1.

## 9. Public dataset (`data.fundlens.org`)

Produced by `fundlens dataset --snapshot` from the live build. Layout on the public bucket:

```
v1/<snapshot-date>/<table>/cycle=<cycle>/*.parquet    tables: contribution (with donor_id), contributor, donor, committee, candidate, candidate_committee_link, race, independent_expenditure, committee_transfer
v1/<snapshot-date>/crosswalk.parquet  overrides.yaml  manifest.json  (build_id, row counts, sha256 per file, precision/recall)
v1/latest/ → copy of the newest snapshot (R2 has no symlinks; copy within the bucket)
v1/README.md  LICENSE (CC BY 4.0)  CHANGELOG.md  schema/<table>.json (JSON Schema)  (from docs/dataset/)
```

Snapshots are weekly after the Sunday run; the last 8 are kept. The README states the CC BY 4.0 license, the attribution string, and the notice that the FEC's solicitation and commercial-use restrictions (52 U.S.C. §30111(a)(4), 11 CFR 104.15) apply to contributor records independently of this license (not legal advice). The `/dataset` page lists snapshots from `manifest.json` and shows DuckDB and pandas one-liners for reading `latest/` over HTTPS.

## 10. Infrastructure, deploy, observability, backups

### 10.1 Coolify

One Coolify project `fundlens` on `music-box-dancer`, compose resource from `neuroticsasquat-ch/fundlens` `main`, `docker-compose.prod.yml` (port from upmovies: `build: {context: ., target: prod}`, `${VAR:-default}` fallbacks seeded once — see `reference_coolify_compose_env_seed`), "Source commit availability: available during build" on, domain `api.fundlens.org` on `api`. Env: `DATABASE_URL`, `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BUCKET`, `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_API_TOKEN` (purge only), `DEEPINFRA_API_KEY`, `ADJUDICATE_MODEL`, `SENTRY_DSN` (Bugsink), `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_RESOURCE_ATTRIBUTES` (literal, `service.name=fundlens-api` / `fundlens-pipeline`), `KUMA_PUSH_WEEKLY`, `KUMA_PUSH_PUBLISH`, `DUCKDB_MEMORY_LIMIT`, `DUCKDB_THREADS`, `DATA_DIR`. Postgres: `shared_buffers=4GB`, `work_mem=256MB`, `maintenance_work_mem=2GB`, `max_wal_size=4GB` via `command:` flags.

### 10.2 Cloudflare

DNS: apex → Worker custom domain; `api` → Hetzner IP, proxied; `data` → R2 custom domain. Cache rule on `api.fundlens.org`: cache everything, respect origin TTL. Rate-limit rule on `/v1/*`. R2 buckets `fundlens-data` (private) and `fundlens-public` (public access on, custom domain). API token scoped to zone purge; a second scoped to R2.

### 10.3 Observability

`telemetry.py` ported from upmovies: `sentry-sdk` → Bugsink with `release`/`environment` read from OTel resource attributes; `opentelemetry-instrument` wraps both entrypoints; logs via the instrumentation logging handler (never `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED`). Kuma: push monitors `fundlens/weekly` (period 7 d + 12 h grace) and `fundlens/publish`, pushed by name over the tailnet; alerts to Discord `#alerts`. A `fundlens health` command is the Coolify healthcheck for `api`.

### 10.4 Backups

Postgres: the ops `backup-postgres.sh` loop picks up the new container (`REQUIRED_CONTAINERS` updated in the ops repo) → Storage Box, nightly 03:00; a Kuma push per iteration already exists. Only `app.*` matters (crosswalk, adjudication, redirects); gold is reproducible. R2 holds everything else. No separate silver backup: R2 is the copy.

### 10.5 Runbooks (in `docs/runbooks/`, written by their tickets)

Cloudflare setup (zone, R2, tokens, Worker domain), Coolify project setup, first backfill, rollback (`publish --rollback`), re-resolving with `--full`, adding an override, rotating the DIME file.

### 10.6 Capacity record

The backfill milestone records in `docs/capacity.md`: per-cycle transform time, full-resolution wall time and peak RSS, weekly incremental time, silver and gold sizes. The handover's triggers for the ephemeral runner (weekly > 6–8 h; steady-state disk > ~300 GB) are checked against it at the end of v1.

## 11. Local development and conventions

- Docker-only: `docker-compose.yml` with `app` (dev target, bind-mounted `src/`, `sql/`, `resolution/`, `tests/`), `postgres` 18, and a `minio` service standing in for R2 (same boto3 client, `R2_ENDPOINT` pointed at it). Frontend dev server runs on the host or in its own compose service (`node:24`), proxying `/v1` to `app`.
- Taskfile targets per `tbc-localdev-infra/CONVENTIONS.md`: `up down build logs shell ps test test:unit test:integration test:e2e lint format typecheck deps:add deps:add-dev deps:lock db:migrate fe:dev fe:test fe:lint fe:build`.
- Pre-commit: Homebrew `pre-commit` orchestrates; every hook body is `docker compose exec -T app …` (ruff, ruff-format, pyright, pytest-unit) or `docker compose exec -T frontend pnpm …` (oxlint, tsc). Never a host-side tool. `task format && git add <files> && git commit` to dodge the format-then-fail footgun.
- Python style: `X | None`, no `from __future__ import annotations`, `x as x` re-exports, pyright strict.
- Commits: Conventional Commits with the Linear ID parenthetical; no `Co-Authored-By`. PRs carry the Claude Code footer.
- GitHub: public repo, MIT, Dependabot (uv + npm + actions) → `updates/dependencies`, three rulesets and the weekly merge workflow copied from tvbf-backend.

## 12. Testing strategy

- `tests/fixtures/fec/2024/`: a synthetic mini-cycle (hand-written, a few hundred rows per file) in exact FEC bulk layout, zipped by a fixture builder at test time. It contains every hard case in §6 and known expected totals. It is also the local-dev seed (`task db:seed` runs the pipeline against it into MinIO + Postgres).
- `unit/`: normalization, name parsing, seat calendar, crosswalk assignment rules, override parsing, API schemas, cache headers.
- `integration/`: each SQL file against DuckDB on the fixture; gold build + swap against a Postgres service container; API routes against the loaded gold with the DuckDB itemized reader.
- `e2e/`: `fundlens run --cycle 2024` against the fixture end to end in CI (MinIO + Postgres services), asserting markers, totals, dedup, resolution of the fixture's Musk and the DIME score on the fixture DIME file.
- Frontend: vitest for components and route loaders against MSW mocks generated from the OpenAPI document; the OpenAPI drift check.
- No network in tests. FEC downloads and DeepInfra are behind interfaces with fakes.

## 13. Open items deferred (not blockers for v1 tickets)

- Whether gold loads via DuckDB's postgres extension or `COPY` from Parquet: decided in the load ticket by measuring on the fixture and one real cycle.
- Trained Splink thresholds: defaults above; tuned in the DIME validation ticket.
- Exact MinIO-vs-R2 parity edge cases (multipart rename semantics): handled in the R2 client ticket with an integration test against MinIO.
- Hetzner Cloud ephemeral runner: out of v1; the capacity record decides.

## 14. Milestones (outline; detail in Linear)

1. **M1 Groundwork** — repo, toolchain, compose, CI, settings, telemetry, R2 client, Cloudflare + Coolify runbooks.
2. **M2 One cycle, committee-level** — extract, seat calendar, silver transforms with earmark dedup and checks, gold without donors, swap publish, purge, API + SPA for races/candidates/committees, deployed for 2024.
3. **M3 Resolution** — contributor keys, normalization, Splink, crosswalk, overrides, donor gold + pages, adjudication, DIME validation, methodology page.
4. **M4 Backfill + IEs** — all cycles since 1980, independent expenditures in race views, capacity record.
5. **M5 Weekly** — scheduled run for the current cycle, incremental resolution, Kuma deadman, rollback runbook.
6. **M6 Public dataset** — snapshot publisher, public bucket, schema docs, license + notice, `/dataset` page.
