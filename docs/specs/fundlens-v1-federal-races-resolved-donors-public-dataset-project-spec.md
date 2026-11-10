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
| Resolution | Splink 5 (DuckDB backend) over unique contributor keys; crosswalk gives sequential integer `donor_id`s; manual overrides in git; LLM adjudication of high-dollar ambiguous clusters; precision/recall scored against DIME (ADR-0005). |
| Earmarks | Count the recipient side; drop `MEMO_CD='X'` and `24T` rows, and an intermediary's `24I` its recipient itemized too; keep the conduit as `conduit_committee_id` (ADR-0004). |
| Self-funding | A candidate's own money (incl. loans) is `self_funding` on the candidate, never a top donor. |
| Organizations | A giver that is neither an individual nor a committee is an organization: its gifts are `organization_receipt`, grouped by organization key (`normalize_employer`), never resolved, never a contribution, counted on the receiving committee only (ADR-0011). |
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
.pre-commit-config.yaml  .github/workflows/{ci,dependencies}.yml  .github/dependabot.yml
CLAUDE.md  CONTEXT.md  LICENSE  README.md
docs/  adr/  specs/  plans/  campaign-finance-handover.md  dataset/  (schema docs published with the dataset)
sql/
  silver/   01_committee.sql 02_candidate.sql 03_candidate_committee_link.sql 04_contribution.sql
            05_committee_transfer.sql 06_jfc_attribution.sql 07_contributor.sql 08_independent_expenditure.sql
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
    aliases.yaml         # employer alias table for the top employers (§6.2)
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
| `api` | fundlens (prod target) | `fundlens api`: uvicorn serving the `fundlens.api.app:create_app` factory with `--proxy-headers --forwarded-allow-ips="*"`. Mounts the silver volume read-only. |
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
resolution/model/<version>.json                                     the trained Splink model; version = the `resolve --full` build_id
resolution/run/<version>.json                                       what that run applied: release, overrides, adjudications (NEU-2056)
markers/cycle=<cycle>/build=<build_id>/{extracted,transformed,resolved,loaded,published}.json
reference/dime/v<version>/contribDB_<cycle>.csv.gz                  DIME as downloaded, archived (NEU-2054, ADR-0009)
reference/dime/v<version>/cycle=<cycle>/fec_individual.parquet      its FEC individual rows, slimmed: what `validate` reads
```

`build_id` = `YYYYMMDDTHHMMSSZ` of the run start. Only the rebuilt cycle gets a new build directory; `gold.meta` records the live `build_id` per cycle, and the API resolves silver paths from it. Builds older than the previous live one are pruned at the end of a successful publish.

Disk budget (federal): silver 30–60 GB, gold 10–30 GB, resolution < 5 GB, bronze ~10 GB, scratch ≤ 60 GB. Never keep historical raw locally. Watch ClickHouse (SigNoz) retention on the same disk.

## 4. Canonical schema (silver)

Source-agnostic from day one: every table carries `source` (`fec`) and `jurisdiction` (`US`), so state loaders in a later project write into the same tables. Column names are snake_case; FEC raw column names appear only inside `sql/silver/`.

| Table | Key | Columns (beyond key) |
|---|---|---|
| `committee` | `(cycle, committee_id)` | `name, treasurer, street, city, state, zip, designation, type, party, filing_frequency, org_type, connected_org, candidate_id, is_conduit` |
| `candidate` | `(cycle, candidate_id)` | `name, party, election_year, office (H/S/P), state, district (2-char, '00' for S/P), incumbent_challenger_open, status, principal_committee_id, race_id, alias_of` (`alias_of`, NEU-2127: set by `03_candidate_committee_link.sql` on a candidate alias, a person's second id for the same race, to the id holding their money, below) |
| `candidate_committee_link` | `(cycle, candidate_id, committee_id)` | `committee_type, designation, linkage_id` |
| `race` | `race_id` | `cycle, jurisdiction, office, state, district, is_special, slug` (from the seat calendar, §5.2) |
| `contributor` | `contributor_key` | `name_raw, name_first, name_last, name_suffix, zip5, city, state, employer_raw, employer_norm, occupation_raw, occupation_norm, contribution_count, amount_total, attribution_count, first_cycle, last_cycle` (`attribution_count` counts the key's JFC attributions, §6.11) |
| `contribution` | `(cycle, source, source_record_id)` | `jurisdiction, contributor_name, contributor_city, contributor_state, contributor_zip, contributor_employer, contributor_occupation, contributor_key, donor_id, recipient_committee_id, candidate_id (via ccl, nullable), amount, date, transaction_type, entity_type, report_type, amendment_indicator, memo_text, conduit_committee_id (nullable), is_self_funding, is_non_contribution_account, fec_line (nullable), is_other_line, image_num, file_num` (the six `contributor_*` columns are the contributor as reported, NEU-2041: the itemized list shows them, and `contributor` is derived from them) |
| `committee_transfer` | `(cycle, source, source_record_id)` | from `oth` receipts and `pas2` 24Ks: `jurisdiction, from_committee_id, to_committee_id, candidate_id (via ccl, nullable), amount, date, transaction_type, side (receipt/disbursement)`. A receipt's `from_committee_id` is its `OTHER_ID`, or, when that is blank, the designation-J committee its `NAME` names (Trump's campaign filed $32.3M of its 2024 JFC transfers with no `OTHER_ID`; NEU-2124), or, for a row with entity type PAC, COM, CCM or PTY, the one `cm` committee its `NAME` names (NEU-2131, the name-match rule below); its `candidate_id` is its recipient's, by contribution's rule (NEU-2124); a 24K's falls back on the giver's `CAND_ID` (NEU-2075). Every amount is kept as filed, a negative one included: a void or refund of a gift is a negative 24K dated when it happens. Gold sums a giver's 24Ks to each candidate for the cycle, and a pair netting below 0 is a returned gift (NEU-2204), the void of a gift made in an earlier cycle with nothing here to net against (the RNC's two 2023 voids of 2022 gifts made its 2024 gifts to candidates −$2,000): it is in the giver's `committee_cycle.total_returned_by_candidates` and in no `total_to_candidates`, `committee_top_recipient`, `total_committee` or `race_top_committee` (§7.1). A pair netting 0 or more nets its corrections against its gifts, as a same-cycle void should. 2024: 1,283 of 138,765 pairs net below 0, −$3,095,886, 1,119 of them with no gift that cycle (Q11 of `docs/measurements/summary-files-2024.md`) |
| `organization_receipt` | `(cycle, source, source_record_id)` | built by NEU-2131 (ADR-0011): from `indiv` rows with an organization entity type and from `oth` receipts whose giver has no committee id: `jurisdiction, organization_name, organization_key, city, state, zip, recipient_committee_id, amount, date, transaction_type, entity_type, report_type, amendment_indicator, memo_text, image_num, file_num, classified, is_non_contribution_account, fec_line, is_other_line`. `organization_name` is the name as reported; `organization_key` is `normalize_employer` of it; `classified` is true when the entity type was blank and the classifier (NEU-2132) called the name an organization. No `candidate_id`, no `contributor_key`, no `donor_id`: organization money is the committee's only |
| `jfc_attribution` | `(cycle, source, source_record_id)` | built by NEU-2078 (§6.11): from `oth` 15J memo lines, `jurisdiction, participant_committee_id, jfc_committee_id (nullable), candidate_id (via ccl, nullable), contributor_name, contributor_city, contributor_state, contributor_zip, contributor_employer, contributor_occupation, contributor_key, donor_id, amount, date`. Evidence, never money: no total reads `amount` |
| `independent_expenditure` | `(cycle, source, source_record_id)` | from `pas2` types 24A/24E (and 24C/24F/24N retained with `kind`): `committee_id, candidate_id, race_id, support_oppose (S/O), amount, date, transaction_type, kind` |

Rules applied in `sql/silver/04_contribution.sql`:
- Source files `indiv` (individual contributions). Keep `ENTITY_TP IN ('IND','CAN')`, and a blank `ENTITY_TP` (FEC fills it only on electronic filings since April 2002) unless the classifier (NEU-2132, `resolve.normalize.is_organization_name`, the measurement's rule V8) calls the name an organization, in which case the row is an organization receipt with `classified = true`, or, when its name key names exactly one `cm` committee (not its recipient, no `oth` twin), a `committee_transfer` receipt from that committee by the name-match rule below (NEU-2132). A filled entity type is never second-guessed. ORG rows are organization receipts (`08_organization_receipt.sql`, below); PAC, COM, CCM and PTY rows are committees' money, by the name-match rule below, or dropped. The same entity-type rule applies to the 15J `jfc_line` view (§6.11). `is_self_funding = true` on every 15C, FEC's contribution from the candidate, whatever its entity type, name or conduit, and at a committee linked to no candidate too, whose `self_funding` it is (NEU-2194: 2024's 15Cs typed IND or under a variant name were $31.5M of individuals' money, $25.9M of it Ramaswamy's at VIVEK 2024, Q6c3); and on any other type's `CAN` row, not through a conduit, whose `NAME` resolves to the recipient's own candidate.
- **Earmarks (ADR-0004):** drop rows with `MEMO_CD = 'X'`; drop rows with `TRANSACTION_TP = '24T'`; drop an intermediary's 24I that its recipient itemized too (NEU-2203): a 24I whose `OTHER_ID` is a `cm` committee other than a conduit and its filer, when that committee has an `indiv` row of the same name (compared as names are), and amount, not a memo line, refund, 24T or 24I, dated within 30 days of it. Any other 24I is kept: most are a recipient's own receipt of an earmark through a conduit, coded 24I (2024: 136,731 of 138,156 counted 24Is, $4,166,976), and an intermediary's 24I the recipient did not itemize is the only record of the gift (1,162 rows, $261,270). 2024 drops 262, $235,403, at five filers (Q10 of `docs/measurements/summary-files-2024.md`). The same 24Is are dropped from `committee_transfer` and `organization_receipt`'s `indiv` rows, and a silver check fails the build if a counted 24I has such a twin among the contributions; when the kept row's `MEMO_TEXT` names a conduit (`EARMARK`, `ACTBLUE`, `WINRED` patterns) or `OTHER_ID` is a committee with `is_conduit`, set `conduit_committee_id`.
- Amendments: FEC bulk already contains the latest version of each record per cycle snapshot; no amendment reconciliation in v1. `amendment_indicator` is retained.
- Negative amounts (refunds, type `22Y` etc.) are kept and net out in aggregates.
- `source_record_id` = FEC `SUB_ID`.
- `candidate_id` on a contribution = the candidate linked to `recipient_committee_id` in `ccl` for that cycle, when the committee is a principal or authorized committee (`CMTE_DSGN IN ('P','A')`) or the one the candidate's `cn` row names principal (`CAND_PCC`), whatever `ccl` designates it; else null. FEC's files show a committee as it stands today, and a campaign committee turned leadership PAC after the election raised the cycle's money as the campaign: Trump's 2024 `C00828541`, now NEVER SURRENDER, INC., which `ccl` links `N`/`D`, credited none of its money to him until this rule. A `ccl` link is still required, so a leadership PAC that is no one's `CAND_PCC` stays the candidate's in no total. Where `ccl` links one committee to two candidates, the principal link and then the lower `candidate_id` takes it, with one exception: a committee handed from one candidate to another, listed in the vendored, hand-curated `src/fundlens/fec/handoffs.csv` (`committee_id, from_candidate_id, to_candidate_id, handoff_date, source`), is the first candidate's before `handoff_date` and the second's on and after it, judged by each row's own date, and a row with no date is the second's (NEU-2126). Its one row is Biden's 2024 `C00703975`, Harris's from 2024-07-21. The transform loads the rows whose date falls in the cycle, and a silver check fails the build unless `ccl` links each one's committee `P` or `A` to both its candidates. The same rule credits `committee_transfer`'s receipts and 24K gifts and `jfc_attribution`'s candidate.
- **Candidate aliases (NEU-2127).** FEC sometimes registers one person under two candidate ids for one seat and cycle, an old id beside a new one, both linked to the same committee (Hovde's 2024 `S2WI00268` and `S4WI00256`). The rule above credits the committee to one; the other is an alias of it (`candidate.alias_of`) when both are candidates of the same race, both are linked P or A to that committee, and their names share a last name and first given name, compared as the self-funding test compares them. An alias is credited no committee, by contribution's rule or by `committee_transfer`'s (which passes over an id `cn` lacks), and is in no handoff, so no money moves: the canonical id is the one already holding it. A 24K whose giver's `CAND_ID` stands (its recipient linked to no candidate) and is an alias is credited to the id it is an alias of. Silver checks fail the build if an alias names another alias or holds money in `contribution` or `committee_transfer`. Name variants the rule does not catch (`CRAVEN, MICHAEL ANDREW` / `CRAVEN , MIKE`) and ids filed for different seats stay separate candidates.
- **Hybrid PACs' non-contribution accounts (NEU-2192).** A hybrid PAC (`cm.CMTE_TP` V or W) keeps two accounts: a contribution account, limited, which it reports on Form 3X line 11(a)(i), and a non-contribution account, unlimited, whose receipts `indiv` types `10` (`10J` a JFC's share of them, `24I` an earmark through a conduit, NEU-2203) and whose refunds it types `20Y`. A hybrid PAC files a 24I on line 17, for the non-contribution account, under a `MEMO_TEXT` beginning `* NON-CONTRIBUTION ACCOUNT`, and on line 11(a)(i), in its contribution account, without one; the committee type does not tell them apart: on 2024 two W committees' 151 counted 24Is ($22,920) are on line 17 under that memo and four V committees' 21 ($5,740) on 11(a)(i), but on 2026 three W committees' 166 ($37,794) are on 11(a)(i), with no such memo (NEU-2207, Q10j). A counted row typed 10, 10J or 20Y at a V or W committee, or 24I there with that memo, is kept, a contribution or an organization receipt by the rules here, with `is_non_contribution_account` true; every other row is false. A refund is judged by its type, not by its giver: a 22Y refunds an ordinary contribution and stays unmarked even when its giver also gave the other account, and a 20Y is marked even when the committee holds no 10 from that giver in the cycle. Matching a refund to a giver's 10 by `NAME` was tried first and rejected: on 2024 it missed $9.1M of the V and W committees' $9.7M of 20Ys, most naming no one the committee holds a 10 from in the cycle, and marked $1.06M of 22Ys to people who had given both accounts, leaving FF PAC's contribution account at −$28,791. A 10 to any other committee is line 11(a)(i) money and stays unmarked, as does its refund: super PACs (O, U) file theirs as 10s and 20Ys and match FEC's itemized figure (Q5 of `docs/measurements/summary-files-2024.md`). The money is real and donors gave it, so it is never dropped; `committee_cycle` keeps it apart (§7.1). A committee's gift to the account, from `oth`, is a `committee_transfer` receipt, unmarked, in `total_from_committees` as any committee's gift. A silver check fails the build if a row's flag disagrees with this rule. FEC's `INDV_ITEM_CONTB` is receipts before refunds, so a hybrid PAC's contribution-account receipts, not its net `total_individual`, are what match it: on 2024 FF PAC's are $6,250 against FEC's $6,250, Congressional Leadership Fund's $10,100 against $10,100, and House Majority PAC's $7,791,231 against $7,720,883. 2024: 653,370 type-10 rows, $1,696,885,797, at the 344 hybrid PACs more than 1% over FEC's itemized figure (Q6); FF PAC (`C00669259`) counted $481.5M in `total_individual` against FEC's $6,250 itemized.

- **The line each row is filed on, and what `total_individual` counts (NEU-2193).** `fec_line` is the Form 3/3X line FEC files the row's transaction type on at its recipient, by the `fec_line` macro (`src/fundlens/fec/lines.py`), the CASE of Q6 in `docs/measurements/summary-files-2024.md`: `11(a)(i)` for 15, 15E, 15I, 15T, 15Z, 11, 11J, 10 and 10J outside a hybrid PAC, and every 24I but a hybrid PAC's under the non-contribution account's memo; `non-contribution account` for a hybrid PAC's 10, 10J and 20Y and its 24I under that memo (above), the one rule that reads `MEMO_TEXT`; `11(d) candidate` for 15C; `13 loans` for 16C, 16F, 16G, 16H, 16J, 16K, 16L, 16R; `12 transfers` for 18G, 18J, 18K, 18L; `11(c) unregistered committee` for 18U; `15 other receipts` for 18H; `electioneering` for 19, 19J; `party account 30`, `31` or `32` for a national party's convention, headquarters and recount accounts, 30, 31, 32 and their variants (30T, 31E, 32J …) and their refunds 40Y, 41Y and 42Y; `20 refunds` for every other 2nY or 4nY and 22Z; NULL for a type it does not place. Q6's CASE, except that an account's refunds go with its receipts (a hybrid PAC's 20Y, a party's 4nY), where Q6 called every refund `20 refunds`, and that a 24I goes on line 11(a)(i), or where a 10 does when a hybrid PAC files it under the non-contribution account's memo (NEU-2203, NEU-2207, Q10), where Q6 called it an earmark's conduit side: most 24Is are a recipient's earmark receipt on line 11(a)(i), or a hybrid PAC's on line 17 (Q6 found $17,936 of them at FIGHT LIKE HELL PAC, on line 17, and THE SCHOOL BOARD PROJECT, whose $1,000 is on 11(a)(i)). `is_other_line` is true when `fec_line` is set and is none of `11(a)(i)`, `11(d) candidate`, `20 refunds` and `non-contribution account`. **`total_individual`, on `committee_cycle` and `candidate_cycle` alike, counts the rows that are not self-funding, not the non-contribution account and not `is_other_line`: transaction types 15, 15E, 15I, 15T, 15Z, 11, 11J, 15C, 10 and 10J outside a hybrid PAC, 24I but a hybrid PAC's under the non-contribution account's memo, the refunds of these (22Y and every 2nY or 4nY but a hybrid PAC's 20Y and a party's 40Y, 41Y, 42Y, and 22Z), and any type the macro does not place**, which counts as every type did before NEU-2193, since `indiv` is individuals' contributions. The marked rows are kept: donors gave them, so donor figures, top-donor lists and `cycle.total_amount` count them as before, and `committee_cycle.total_other_lines` holds them (§7.1). A candidate's own money is self-funding whatever its line (WHITLOCK's 16C loan is `13 loans` and in `self_funding`). 2024, at the committees more than 1% over FEC's itemized figure (Q6): party accounts $84,163,828 at the six national party committees (RNC, DNC, DCCC, DSCC, NRSC, NRCC), 18U $22,224,103 (a host committee, `C00834978`), 18G $500,000; the RNC was $21.0M over FEC's `INDV_ITEM_CONTB`, the DCCC $18.9M, the DSCC $12.3M. The parties file these accounts' receipts on Form 3X line 17, other federal receipts, whatever the type: 4 of 2024's 10,524 counted 3x receipts are on line 11(a)(i), and they net to −$20,000 (NEU-2202, Q9). After NEU-2193, five parties are 2–8% below `INDV_ITEM_CONTB`. Part of that is refunds, which B nets and FEC's figure does not. Part is FEC's bulk files: the 11(a)(i) rows they omit, the DSCC's June 2024 report they omit, and amounts written in whole dollars. Organizations' 3x receipts, which FEC also files on line 17 ($2,522,786 at the six parties in 2024, Q9i), are marked `is_other_line` in `organization_receipt` by the same rule (NEU-2205), so B (`total_individual + total_from_organizations`) no longer counts them and they no longer offset the gap.

Rules applied in `sql/silver/08_organization_receipt.sql` (NEU-2131, NEU-2132; ADR-0011; figures from `docs/measurements/organization-money-2024.md`, FEC's 2024 files):
- From `indiv`: counted rows (`MEMO_CD` not `X`, `TRANSACTION_TP` not `24T`, no intermediary's 24I its recipient itemized, as `contribution`) with `ENTITY_TP = 'ORG'`, or a blank `ENTITY_TP` the classifier calls an organization (`classified = true`) and the name match did not make a committee's gift (it names no one `cm` committee other than its recipient), to a committee in `cm`. Earmark handling as `contribution`'s (ADR-0004): a conduit-side row is dropped. 2024: 18,233 ORG rows, $2,257,182,796; 70 blank rows the classifier calls organizations, $233,837.
- From `oth`: receipt types (`TRANSACTION_TP` `1x`, `3x`), not memo lines, with `ENTITY_TP = 'ORG'` and an `OTHER_ID` that is blank or not C-prefixed, and whose `NAME` names no JFC (the JFC rule, NEU-2124, is tried first: 4 rows, $183,545, in 2024 are a JFC's transfers); not 15J (evidence, `jfc_attribution`) and not a loan type (16C, 16F, 16G: a loan is not a gift, and a bank's 16F is credit that its 16G repays). A C-prefixed `OTHER_ID` the cycle's `cm` lacks is still a committee's: the filer named one, and the row stays in `committee_transfer` as today (689 rows, $21.3M in 2024), never an organization receipt. A blank entity type in `oth` is not classified: the row stays out (one row, $9,609, in 2024). 2024: 103 rows, $23,073,903.
- An `oth` row that mirrors a counted `indiv` row (same recipient, name key, amount and date; 2 rows, $133,900 in 2024) is read once, from `indiv`. No `oth` organization receipt shares a `SUB_ID` with an `indiv` row, so `SUB_ID` alone would miss both mirrors.
- The refund sign rule and reversal pairing (NEU-2073) and the unknown-recipient rule (NEU-2070) as in `contribution`.
- `organization_key` = `normalize_employer(organization_name)`: cleaned, its legal form stripped (`LEGAL_FORMS`), its employer alias applied (`aliases.yaml`), registered with DuckDB as the contributor normalizers are. A name that normalizes to nothing (`NO_VALUE`) keeps the row with the cleaned name as its key. Exact grouping, no linkage: `KOCH INDUSTRIES INC` and `KOCH INDUSTRIES` are one key, `SPACE EXPLORATION TECHNOLOGIES CORP` and `SPACEX` are one key by alias, and two spellings the rule leaves apart are two organizations.
- `source_record_id` = FEC `SUB_ID`. The key is unique across `contribution`, `committee_transfer` and `organization_receipt`: a silver check fails the build if a `source_record_id` is in two of them.
- `is_non_contribution_account` as `contribution`'s (NEU-2192): an organization's 10 or 10J to a hybrid PAC (V, W), a 24I there under the account's memo (NEU-2207), or a 20Y refund to one from it, is its non-contribution account's money.
- `fec_line` and `is_other_line` as `contribution`'s (NEU-2193, NEU-2205), by the same `fec_line` macro and the same rule: an organization's gift to a national party's convention, headquarters or recount account (30, 31, 32 and their variants, a tribe's 31T in `indiv`, a 32J in `oth`, refunded as 40Y, 41Y, 42Y), an 18U, a transfer, is marked, kept, and in `committee_cycle.total_other_lines`, not `total_from_organizations` (§7.1). An organization's 15 is `11(a)(i)` and unmarked. 2024: $2,522,786 of organizations' 3x receipts at the six national parties, every one filed on line 17 (Q9i).
- `organization_receipt` never feeds `contributor` (§6.1) or resolution, and no total outside `committee_cycle` and `committee_top_organization` (§7.1) reads it.
- Expected 2024 row count before the classifier (NEU-2131's target): 18,336, the 18,233 ORG `indiv` rows plus the 103 `oth` rows, less the mirrors; the classifier (NEU-2132) adds its 70 blank rows on top.

Rules applied in `sql/silver/05_committee_transfer.sql` for rows naming a committee (NEU-2131; measurement Q3, Q7; ADR-0011):
- **PAC/COM/CCM/PTY rows without a committee id.** A counted `indiv` row with entity type PAC, COM, CCM or PTY, or a blank entity type the classifier calls an organization (NEU-2132), and a blank `OTHER_ID`, whose name key (uppercased, letters and digits only, the key `04_contribution.sql` and `05_committee_transfer.sql` compare names by) names exactly one `cm` committee, is a `committee_transfer` receipt from that committee (`from_committee_id` = the named committee, `source_record_id` = its `SUB_ID`). The same applies to an `oth` receipt with a blank `OTHER_ID` that names no JFC (the JFC rule, NEU-2124, is tried first). Not when the named committee is the row's own recipient. Not when `oth` already holds the gift: same recipient, `OTHER_ID` = the named committee, same amount and date (5 `indiv` rows, $70,000 in 2024). Rows naming several committees or none are dropped: they are committees by entity type, so they are not organization receipts either; a classified blank row naming several or none is an organization receipt instead, since nothing says it is a committee's, and one dropped for its `oth` twin is in neither table. Nothing is counted twice.
- 2024: $788,411,601 in 4,052 rows, $778,467,682 of it in `indiv`; $635,589,379 (80.62%) names exactly one committee, in 2,546 `indiv` rows and 9 `oth` rows ($212,303); $152,822,222 names several or none and is dropped (Save America, the Republican Governors Association and Trump 47 Committee are the largest, each naming no single `cm` committee).
- The measurement's pinned 95% all-or-nothing bar got *drop*, which would have dropped all $788.4M. It is amended here because the bar blocked the matched rows with the unmatched ones, and the matched rows are FEC's own committee money: Senate Leadership Fund's PAC-typed rows, $8,934,545, are FEC's `OTHER_POL_CMTE_CONTRIB` ($8,934,548) to within $3, and SMP's rows plus its existing transfers are FEC's figure to within $6.1k.

FEC bulk files (`https://www.fec.gov/files/bulk-downloads/<cycle>/<file><yy>.zip`, pipe-delimited, no header; headers from `data_dictionaries/<file>_header_file.csv`, vendored under `src/fundlens/fec/headers/`):

| File | Table | First cycle |
|---|---|---|
| `cm` | committee | 1980 |
| `cn` | candidate | 1980 |
| `ccl` | candidate_committee_link | 2000 (earlier cycles link via `cn.CAND_PCC` and `cm.CAND_ID` only) |
| `indiv` | contribution, organization_receipt | 1980 |
| `pas2` | independent_expenditure (+ committee→candidate contributions) | 1980 |
| `oth` | committee_transfer, jfc_attribution (§6.11), organization_receipt | 1980 |
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
fundlens dime      --cycle 2024 --import PATH        # archive a DIME file and slim it for the validator (NEU-2054)
fundlens validate  --cycle 2024 [--top 10000]        # precision/recall of the resolved build against DIME (§6.9)
fundlens health                                      # exit 0 iff Postgres + R2 reachable
```

Every step writes a completion marker to R2 (`markers/...`) with `build_id`, row counts and timing. `run` skips a step whose marker exists for this `build_id`; a crashed run is resumed by re-running `run` with `--build-id`. The idempotency check for extract is "does the silver partition for this cycle exist and is the bronze download date unchanged", never "is the zip on disk". Each step is also a Python function so tests call it without the CLI.

Every CLI entry is wrapped: Kuma push `status=up` on success, `status=down` on exception (Kuma has no start signal, so a run that hangs or never starts is caught by the monitor's interval expiring); the exception is reported to Bugsink with `pipeline_mode=<step>` and re-raised (crash, not items).

### 5.2 Seat calendar (`fundlens seats`)

For a cycle: all House districts under the apportionment in force (a vendored `apportionment.csv`: state, seats, first cycle), delegate seats (DC, PR resident commissioner, AS, GU, MP, VI), the Senate class up that cycle (`senate_classes.csv`: state, class), specials from `specials.csv` (cycle, office, state, district, note; hand-maintained), and President every cycle divisible by 4. `race_id` = `{cycle}-{office}-{state}-{district}[-special]`; `slug` = `{cycle}/{house|senate|president}/{STATE}[-{DD}][-special]`. A candidate filing whose `(office, state, district)` matches no seat is written to `app.unmatched_filing` and surfaced in `fundlens seats --report`; it does not create a race.

### 5.3 Transform

`transform.runner` opens DuckDB with `memory_limit`, `temp_directory`, `threads` from settings, registers the bronze zips for the cycle via `read_csv` (pipe delimiter, vendored column names, all-varchar then cast), runs `sql/silver/*.sql` in filename order with `{cycle}` and `{build_id}` parameters, writes each table to the local silver path, runs `sql/checks/*.sql` (every check is a query that must return zero rows), then uploads the partition to R2 and writes the `transformed` marker. Any check failure aborts before upload.

### 5.4 Resolve — see §6.

### 5.5 Load and publish

`load.gold` creates `gold_build`, runs `sql/gold/*.sql` (DuckDB computes the aggregates from silver and writes CSV/Parquet; Postgres `COPY`s them; or DuckDB's postgres extension writes directly, decided in the ticket), creates indexes, runs `sql/checks/gold_*.sql`, writes `gold_build.meta`. `publish` then, in one transaction: `DROP SCHEMA IF EXISTS gold_prev CASCADE; ALTER SCHEMA gold RENAME TO gold_prev; ALTER SCHEMA gold_build RENAME TO gold;` then, at least 60 s after the swap commits (the API reads `gold.meta.build_id` for its `ETag` at most once a minute, `api/cache.py`; a purge inside that window lets the edge keep a new body under the old `ETag` for a week), purges the Cloudflare zone, snapshots `app.crosswalk` and `app.adjudication` to R2 (before the marker, so a resumed publish takes the snapshot again; NEU-2049), writes the `published` marker, prunes old silver builds, and (with `--dataset`) runs the dataset snapshot (§9). Readers never see a half-loaded state. `gold_prev` is the rollback: `fundlens publish --rollback` swaps it back.

### 5.6 Schedule

One Coolify scheduled task on the `pipeline` service: Sunday 03:00 box time, `fundlens run --cycle <current> --dataset`. The current cycle = the next even year ≥ today's year (2026 until 2027-01-01, then 2028). Historical cycles are built once by `fundlens run --cycle <c>` by hand (the backfill milestone) and never rebuilt unless `--full` resolution changes `donor_id`s, in which case every cycle's gold is reloaded.

## 6. Entity resolution

Only individuals are resolved; committees and candidates carry FEC IDs, and organizations are grouped by organization key (§4, ADR-0011), never linked.

1. **Contributor keys.** `sql/silver/04_contribution.sql` gives each contribution its key and `sql/silver/07_contributor.sql` reduces ~400M contribution rows (and the JFC attributions, §6.11; never `organization_receipt`) to unique `(name_norm, zip5, employer_norm, occupation_norm)` tuples (tens of millions), each with counts and totals. Resolution runs over these.
2. **Normalization (`resolve.normalize`).** `nameparser` → first/middle/last/suffix; uppercase, strip punctuation and suffixes (JR, SR, III, MD, ESQ); ZIP5; employer and occupation canonicalized by a rule table (`SELF-EMPLOYED`, `RETIRED`, `NOT EMPLOYED`, `N/A` → null; `INC`, `LLC`, `CORP` stripped; a small alias YAML for the top employers). `usaddress`/libpostal are not used in v1 (street is not in `indiv`).
3. **Splink 5** (`resolve.model`; Splink 4 when this was written, 5.0 by NEU-2048), DuckDB backend, `link_type="dedupe_only"`. Blocking rules for prediction: `(last_name_soundex, zip3)`, `(last_name, first_initial, state)`, `(employer_norm, last_name)`. Comparisons: first name (Jaro-Winkler levels), last name (exact / JW), zip5 (exact / zip3), city+state, employer_norm (exact / JW), occupation_norm. `u` by random sampling; `m` by EM on each blocking rule; the trained model is saved as JSON under `resolution/` in R2 and reused by incremental runs. Amended by NEU-2048: every comparison level carries a prior m and u, and a first name that disagrees outright all but vetoes a match (a nickname was then an override's or adjudication's to merge, not linkage's); the probability two random keys match is always estimated from deterministic `(first_name, last_name, zip5)` matches, but u and m are estimated only from at least `RESOLVE_MIN_TRAINING_KEYS` (default 100,000) keys, and a smaller input, the fixture among them, keeps the priors. The model is saved as `resolution/model/<build_id>.json`, its version the `build_id` of the `resolve --full` run that trained it. Amended by NEU-2188: the first-name comparison's levels are `null, exact, nickname, jw ≥ 0.92, jw ≥ 0.8, initial, else`; the initial level fires only when one name is a single letter sharing the other's first letter, and the nickname level when one name is a prefix of the other at least three letters long or the vendored nickname table (`resolve/nicknames.csv`, Apache-2.0, less `nicknames-excluded.csv`) links the two directly, so a nickname the table or the prefix rule names is linkage's, and one it does not is still an override's. `load` gives each contributor key a `first_name_nicknames` list the rule reads. Per-ticket spec: `docs/specs/NEU-2188-first-name-levels.md`.
4. **Clustering.** `predict(threshold_match_probability=0.9)` → `cluster_pairwise_predictions_at_threshold(0.95)`; thresholds are settings with these defaults. Connected components give clusters of contributor keys. `resolve --full` writes them to the table `cluster(cluster_id, contributor_key, match_probability)` in resolution's DuckDB working file (`resolution/resolve.duckdb`), beside the cross-cycle `contributor` table it linked, and writes a `resolved` marker under each cycle's newest transformed build (NEU-2048). Amended by NEU-2122 (ADR-0010): a connected component ignores every pair it did not link, and across 5.6M keys that chained unrelated people into one donor (2024 precision 0.3657). `cluster()` now keeps the predicted pairs as `edge` and Splink's components as `component` in the working file, and a `recluster` phase, between `cluster` and `overrides`, rebuilds every component that holds a vetoed pair (the first-name comparison's else level, computed with the same `jaro_winkler_similarity`) or more than `RESOLVE_MAX_CLUSTER_KEYS` keys from its own edges, strongest first, refusing any union that would hold a vetoed pair or exceed the cap; other components are untouched. The cap is tuned offline with `fundlens recluster --max-keys N` and `fundlens validate --cycle C --clusters`. Per-ticket spec: `docs/specs/NEU-2122-recluster-chains.md`. Amended by NEU-2188: a vetoed pair is two first names both present, not equal, Jaro-Winkler under 0.8 and neither an initial pair nor a nickname pair, whatever their initials; the veto reads the same SQL fragments as the model's levels.
5. **Overrides (`resolution/overrides.yaml`).** Schema: a list of `merge: [contributor_key, …]` and `split: {contributor_key: …, from: donor_id}` entries, each with `reason` and `added`. Applied after clustering, before the crosswalk. A test validates the file. Built by NEU-2050 (`resolve/overrides.py`): a merge joins every cluster holding one of its keys; a split, applied after the merges, moves its key into a cluster of its own. A test validates the file's own rules (schema, no key in two entries); `resolve --full` checks every key against its `contributor` table and every `from` against the ids the crosswalk has given (`app.crosswalk` or a redirect) once it has loaded the contributors, and stops before training when one is unknown. A split key with more of the donor's dollars than the keys it leaves keeps the donor's id (§6.6). The file is `OVERRIDES_PATH` (default `/app/resolution/overrides.yaml`, copied into the image); the fixture cycle's overrides are `tests/fixtures/resolution/overrides.yaml`. How to add one: `docs/runbooks/adding-an-override.md`.
6. **Crosswalk (`app.crosswalk`: `contributor_key PK, donor_id bigint, assigned_at, build_id`).** For each cluster: if its members already carry donor_ids, the cluster takes the one covering the most contribution dollars; members carrying a different id are re-pointed (a merge) and `app.donor_redirect(old_id → new_id)` records it; a never-seen key gets `nextval(app.donor_id_seq)`. A cluster that splits keeps the id on the larger-dollar half; the other half gets a new id. `donor_id`s are never reused. Built by NEU-2049 (`resolve/crosswalk.py`): `resolve --full` assigns after clustering, writes only rows whose id changed, and points an existing redirect on when its target is merged away, so every redirect resolves in one hop; it then rewrites each cycle's `contribution` (into `bucket=` directories) and `contributor` partitions with `donor_id`, in place under the transformed build.
7. **Canonical display.** `gold.donor.display_name` = the most frequent `name_raw` variant weighted by amount; employer/occupation/city/state likewise.
8. **Adjudication (`resolve.adjudicate`).** Candidates: clusters (or pairs of clusters that share last name + zip3) whose total ≥ `ADJUDICATE_MIN_AMOUNT` (default $50,000) and whose match probability lies in `[0.6, 0.95)` or whose members disagree on employer. Batched to DeepInfra (OpenAI-compatible; `ADJUDICATE_MODEL` default `deepseek-ai/DeepSeek-V4-Flash`; time a model before changing it) with `resolution/prompts/adjudicate_v1.md`, structured JSON reply `{decision: merge|split|unsure, confidence, reason}`. Results go to `app.adjudication (cluster_fingerprint, model, prompt_version, decision, confidence, reason, decided_at)` and are applied like overrides when `confidence ≥ 0.8`. Never called from the API. Built by NEU-2055 (`resolve/adjudicate.py`, `fundlens adjudicate [--dry-run] [--limit N]`): a candidate is two sides of contributor keys. A *pair* is two clusters holding keys of one last name and ZIP3, at least `ADJUDICATE_MIN_AMOUNT` together, whose best pair of such keys the newest saved model scores in the band (scored again, blocking on last name and ZIP3 alone, since `edge` keeps no pair under the match threshold). A *cluster* is one of at least that amount whose keys report two or more employers, side A the keys of its employer with the most dollars and those with none, side B the rest. Employer disagreement picks clusters and the band picks pairs: two clusters apart nearly always disagree on employer, so that test alone would make every same-surname neighbour of a large donor a candidate. A candidate holding a key the overrides name is never asked. `cluster_fingerprint` is the fingerprint of the two sides' fingerprints. `resolve --full` and `recluster` keep the clusters after overrides as `unadjudicated` in the working file, which `adjudicate` chooses from, then find the candidates in them again by fingerprint and apply the configured model's and prompt's confident verdicts: a pair's `merge` joins its clusters, a cluster's `split` moves side B into a cluster of its own, and anything else changes nothing. The prompt's version is its file's stem (`adjudicate_v1`, `ADJUDICATE_PROMPT_PATH`); requests go out `ADJUDICATE_BATCH_SIZE` at a time in DeepInfra's JSON mode, and each batch's verdicts, tokens, cost and p50/p95 latency are written and logged as it returns. How to run it: `docs/runbooks/adjudicating.md`.
9. **Validation (`resolve.validate`).** Join DIME contributor records (Bonica, Stanford; `bonica.cid`) to FEC `SUB_ID`s by (date, amount, recipient committee, normalized name) and compute pairwise precision/recall of fundlens clusters against `bonica.cid` on the matched subset, overall and for the top 10k contributors by dollars. The report is written to `gold.meta` and shown on the methodology page. DIME covers through 2024; check its terms of use before download. Amended by NEU-2054 (ADR-0009): the reference is DIME Public version 4.0 (ODC-BY 1.0), one `contribDB_<cycle>.csv.gz` per cycle, imported by `fundlens dime --cycle C --import PATH` into R2 `reference/dime/v4.0/` (the raw file archived, a slim Parquet of its FEC individual rows read); the join is exact, on DIME's `efec.comid.orig` and `efec.transaction.id.orig` (the filer's `CMTE_ID` and `TRAN_ID`) plus amount (by magnitude and in whole dollars: a refund's sign is the filer's choice, and FEC's bulk file drops the cents DIME keeps) and date against the cycle's bronze `indiv`, then `SUB_ID` to silver; the record scored is the labelled contributor key, one per `(contributor_key, bonica.cid)`; the top scope is the 10,000 `cid`s with the most matched dollars; `fundlens validate --cycle C` writes both scopes to `app.resolution_quality(model_version, cycle, scope, …)` with their pair counts, and `load` copies the live model's figures into `gold.meta` (`precision`, `recall`, `precision_top`, `recall_top`, `matched_rows`, `dime_version`). Per-ticket spec: `docs/specs/NEU-2054-dime-validation.md`.
10. **Incremental weekly.** Only the current cycle's new contributor keys are linked (against the full contributor table, using the saved model); existing keys keep their donor_id. `--full` re-trains and re-clusters everything and is only run when the model or normalization changes. The incremental run re-clusters the new keys' components with the same `resolve.cluster.recluster` (NEU-2122), extending `edge` as NEU-2062's spec says.
11. **JFC attribution lines (NEU-2072).** A joint fundraising committee's participant itemizes the individuals behind each JFC transfer as `oth` 15J memo lines (`MEMO_CD = 'X'`), each the share of one person's gift attributed to that participant. They are evidence about people, never money: the participant's share reaches it as the JFC's transfer in `committee_transfer` (filed mostly as 18G, NEU-2124), and the JFC's own `indiv` row counts the person's gift wherever the JFC itemized it. Measured 2026-10-31 on FEC's public 2024 `oth`, `indiv` and `cm` files, keys built by `resolve.normalize`, and `indiv` filtered by `04_contribution.sql`'s entity-type, memo and 24T rules (not its conduit-side, committee-in-`cm` or refund-sign rules, so the overlaps run slightly high):
    - **The lines.** 17,037,819 memo lines with an individual's entity type, $2,165,892,334. Left out: 1,950 memo lines with another entity type (ORG, PAC, COM, CCM, PTY, CAN) and 762 15J lines not marked memo. Every line has a blank `OTHER_ID`, so none names its JFC by id. `MEMO_TEXT` names a committee in `cm` on 35.0% of lines (`* HARRIS VICTORY FUND`, `JFC ATTRIB: …`, `TRANSFER FROM …`), the one JFC the filing has transfers from, of any type, names it on 18.3% more (build `20261103T175128Z`, NEU-2183), and 46.7% name none. 15.7M of the lines are under $200: participants itemize attributions far below the JFC's own itemization threshold.
    - **Overlap with the same JFC's `indiv` rows**, on the 6,947,180 lines ($912,688,708) whose JFC is known: 71.0% of lines share the exact contributor key and 74.1% the normalized name and ZIP5, 81.3% of the dollars; of (JFC, person) pairs, 61.7%.
    - **Overlap with `indiv` anywhere:** 93.4% of lines carry a key `indiv` already has. 434,469 of the 2,262,143 distinct 15J keys (19.2%) are new, and 294,696 people (normalized name and ZIP5, 14.5%) appear in no `indiv` row those rules keep ($126,724,488 attributed, median $67): most likely gifts the JFC did not itemize, whose money fundlens sees only as the JFC's transfer.
    - **The links.** 1,809,868 of 2,547,245 (person, participant) pairs (71.1%) have no direct `indiv` gift from that person to that participant. 15J is the only evidence that the person's money reached that candidate's or party's committee.

    **Decision: 15J lines feed resolution as contributor evidence and add to no money total.** Built by NEU-2078: `sql/silver/06_jfc_attribution.sql` builds it (§4) from `oth` rows with `TRANSACTION_TP = '15J'`, `MEMO_CD = 'X'` and an IND or blank entity type, to a committee in `cm`. Its contributor columns and key are built exactly as `contribution`'s (the `contributor_*` value tables collect the 15J values too), its `candidate_id` by the same `ccl` rule, and each amount is kept as filed (3,466,023 lines are zero or negative; no refund sign rule applies to evidence). `jfc_committee_id` is best effort: the committee whose `cm` name `MEMO_TEXT` gives once a leading `<year> AGGREGATE;` and a `JFC ATTRIB:`, `TRANSFER FROM`, `JFC-`, `JFC:` or `*` prefix are stripped, a designation-J committee first; else the one designation-J committee the filing (`CMTE_ID` and `FILE_NUM`) has receipts from in `committee_transfer`, of whatever receipt type and by that table's giver rule (NEU-2183: a JFC's transfer is mostly an 18G, some 18J, a few 15J, now and then with `OTHER_ID` blank, NEU-2124), so a receipt from any other committee, such as an authorized committee's 18G, neither names a JFC nor stands in the way of one; else null. The link needs only the participant, which is the filer and always known. `contributor` reduces `contribution` and `jfc_attribution` together, so a key seen only in 15J is linked by Splink and gets a `donor_id`. `contribution_count` and `amount_total` stay counted money only, and a new `attribution_count` counts the key's 15J lines. The crosswalk's dollar rule therefore ranks a 15J-only key at $0. §6.7's display variant is weighted by counted money, and for a donor with none, by line count. The crosswalk rewrites `jfc_attribution` with `donor_id` as it rewrites `contribution`. No top-donor ranking, race total, candidate total or donor total reads `jfc_attribution`, and a donor with only 15J lines is in none of them. Whether and how gold shows a donor's attributed amounts is for NEU-2051 or a later ticket; whatever it shows stays outside every money total.

    Rejected: leaving 15J out of resolution, which drops 71% of the person-to-participant links that run through a JFC and every donor whose only trace is a 15J line. Counting a 15J amount in any total, which counts JFC money twice (ADR-0004's rule, applied to JFCs). Matching each 15J line to its JFC `indiv` row one to one: there is no shared id, a quarter of the known-JFC lines don't match by name and ZIP5, and only allocating JFC money to candidates would need it, which v1 does not do.

**Hard cases, each a pytest case on the fixture cycle:** Musk (name/employer/address variants roll up), a conduit earmark pair (counted once), a self-funding loan (not a top donor), an employer-variant rollup (`SPACEX` / `SPACE EXPLORATION TECHNOLOGIES`), two different people sharing a common name in different states (not merged), a merge override, a split override, and (§6.11) a person known only from a 15J line resolves to a donor whose totals are $0, and a 15J line adds nothing to its participant's or its race's totals.

## 7. Gold schema and API

### 7.1 Gold tables (Postgres `gold`, rebuilt every run)

| Table | Content |
|---|---|
| `meta` | one row: `build_id, published_at, resolver_version, model_version, overrides_count, adjudications_applied, precision, recall, precision_top, recall_top, matched_rows, dime_version, cycles jsonb (cycle → live build_id, source download dates)` (the quality columns since NEU-2054: `precision`/`recall` are the overall scope, `_top` the top-10k scope; since NEU-2056 `model_version` is the newest saved model, and `resolver_version` (the release that resolved, from OTel's `service.version`), `overrides_count` and `adjudications_applied` (merges and splits each applied) come from that run's record, `resolution/run/<version>.json`) |
| `cycle` | `cycle, race_count, contribution_count, total_amount` |
| `race` | `race_id, cycle, office, state, district, is_special, slug, candidate_count, total_individual, total_committee, total_jfc_transfers, ie_support, ie_oppose` |
| `race_candidate` | `race_id, candidate_id, name, party, incumbent_challenger_open, principal_committee_id, total_individual, total_committee, total_jfc_transfers, self_funding, ie_support, ie_oppose` |
| `race_top_donor` | `race_id, rank (≤100), donor_id, display_name, amount, candidates jsonb [{candidate_id, amount}]` |
| `race_top_committee` | `race_id, rank, committee_id, name, amount, kind (contribution/ie)` (a giver's returned gifts, NEU-2204 (§4), are left out before it is summed by race, so the list adds up to the race's `total_committee`) |
| `candidate` | `candidate_id, name, party, office, state, district, cycles int[]` |
| `candidate_redirect` | `old_candidate_id, candidate_id` (NEU-2127: each candidate alias and the id it is an alias of; aliases are in no other gold table, so `race_candidate`, `race.candidate_count` and `search_entity` list each person once) |
| `candidate_cycle` | `candidate_id, cycle, race_id, total_individual, total_committee, total_jfc_transfers, self_funding, ie_support, ie_oppose, contributor_count` (`total_committee` is the committees' 24Ks to the candidate, a giver's returned gifts (§4, NEU-2204) left out, so never below 0; `total_individual` and `contributor_count` leave out `is_other_line` rows, NEU-2193, as `committee_cycle`'s does (§4); `total_jfc_transfers`, NEU-2124: the receipts of the committees raising for the candidate from a designation-J committee, §6.11's JFC transfers, whatever receipt type the filer gave them: 2024's are 18G mostly, some 18J and 15J. Checked against FEC's transfers-in totals on the 2024 build: Harris −0.9%, Trump −0.03%. In neither of the totals before it) |
| `candidate_top_donor` | `candidate_id, cycle, rank, donor_id, display_name, amount` |
| `committee` | `committee_id, name, type, designation, party, connected_org, is_conduit, cycles int[]` |
| `committee_cycle` | `committee_id, cycle, total_individual, self_funding, total_from_committees, total_from_organizations, total_non_contribution_account, total_other_lines, total_to_candidates, total_returned_by_candidates, ie_total` (`total_to_candidates` and `total_returned_by_candidates`, NEU-2204: the giver's 24Ks credited to a candidate, summed per candidate; a candidate they net 0 or more for is in `total_to_candidates`, one they net below 0 for, a returned gift (§4), in `total_returned_by_candidates`, which is 0 or less. Neither is ever on the wrong side of 0, the two add up to the giver's credited 24Ks, and `committee_top_recipient` adds up to `total_to_candidates`. The RNC's 2024 figures are $0 and −$2,000. FEC's `FED_CAND_CMTE_CONTB` (Form 3X line 23) does not reconcile with a giver's 24Ks, gross or net, so it cannot check either (Q11f–h); `total_other_lines`, NEU-2193: the net sum of the `contribution` rows marked `is_other_line` and not self-funding and, since NEU-2205, of the `organization_receipt` rows marked `is_other_line`, individuals' and organizations' money FEC files on a line no `total_individual` counts (§4), a national party's convention, headquarters and recount accounts above all; 0 when none. `committee_top_donor` and `committee_top_organization` list those givers too, as they list a non-contribution account's; `self_funding` added by NEU-2039: a candidate committee's own-money receipts, kept out of `total_individual`; `total_from_organizations`, NEU-2133: the net sum of `organization_receipt.amount` by recipient, less the rows marked `is_non_contribution_account` or `is_other_line` (NEU-2205); 0 when none, never NULL; `total_non_contribution_account`, NEU-2192: a hybrid PAC's non-contribution account, the net sum of the `contribution` and `organization_receipt` rows marked `is_non_contribution_account`, individuals' and organizations' money alike; 0 at every other committee. At a hybrid PAC, `total_individual` and `total_from_organizations` hold the contribution account alone, the money FEC's itemized figure `INDV_ITEM_CONTB` counts, so the two compare like for like; at every other committee they are unchanged. `committee_top_donor` and `committee_top_organization` list both accounts' givers, since they gave both, so a hybrid PAC's top lists can add up to more than its `total_individual`. `cycle.total_amount` and donor figures count the account as they count every contribution; candidate and race figures never see it, since a hybrid PAC raises for no candidate) |
| `committee_top_donor` | `committee_id, cycle, rank, donor_id, display_name, amount` |
| `committee_top_organization` | `committee_id, cycle, rank (≤100), organization_key, name, amount` (NEU-2133: the organizations that gave the committee the most, grouped by `organization_key`, ranked by net amount then key; `name` is the key's most-money reported spelling, as `donor.display_name` is chosen (§6.7); an organization netting to $0 or less is left out, as top-donor lists leave such donors out, and so is a receipt filed with no name, which has no key and counts in `total_from_organizations` only) |
| `committee_top_recipient` | `committee_id, cycle, rank, recipient_kind (candidate/committee), recipient_id, name, amount` (a returned gift, NEU-2204 (§4), is in no list: `amount` is never below 0, and a gold check fails the build if it, `total_to_candidates`, `total_committee` or `race_top_committee.amount` is) |
| `donor` | `donor_id, display_name, employer, occupation, city, state, zip5, total_all_cycles, first_cycle, last_cycle, contributor_key_count` |
| `donor_cycle` | `donor_id, cycle, amount, contribution_count` |
| `donor_top_recipient` | `donor_id, rank, recipient_kind, recipient_id, name, amount` (all cycles) |
| `donor_redirect` | `old_donor_id, donor_id` |
| `search_entity` | `kind (donor/candidate/committee/race), id, name, aliases text, weight numeric`; `GIN (name gin_trgm_ops)`, `GIN (aliases gin_trgm_ops)` (NEU-2040: search matches either) |

Donor tables, built by NEU-2051 (`sql/gold/10_donor.sql` … `15_committee_top_donor.sql`): a donor is every `donor_id` among the build's `contribution` and `jfc_attribution` rows, so a donor known only from 15J lines is in `donor`, `donor_cycle` and `search_entity` with $0 and in no top list (§6.11); no gold table shows attributed amounts yet. Each display column of `donor` is chosen on its own (§6.7: most counted money, then most contributions, then most attributions); `zip5`'s values are the ZIP5s of the lines' contributor keys. A donor's totals include their own money as a candidate; `donor_top_recipient` does too, and names a candidate when the gift reached a committee raising for one (`contribution.candidate_id`), else the committee. Every top-donor list leaves out `is_self_funding` rows and any donor whose gifts net to $0 or less; `race_top_donor.candidates` leaves out a candidate the donor's gifts net to exactly $0, so it always adds up to `amount`. `candidate_cycle.contributor_count` counts the donors with a counted gift in its `total_individual`, whatever it nets to. `donor_redirect` is copied from `app.donor_redirect` in the load's Postgres transaction. A build loaded before `resolve` has no `donor_id`s: its donor tables are empty and `contributor_count` is NULL. Gold checks: every top-donor row's `amount` is the donor's net gifts to its group without the recipient's own money; every listed `donor_id` is in `donor`; ranks contiguous.

Organization money (ADR-0011) is committee-level only: `committee_cycle.total_from_organizations`, `committee_cycle.total_non_contribution_account` (NEU-2192, a hybrid PAC's non-contribution account) and `committee_top_organization` are the only gold readers of `organization_receipt`. It is in no `cycle`, `race`, `race_candidate`, `candidate_cycle` or donor figure, and `committee_top_donor` lists resolved people only. A cycle-wide organization figure is a deliberate amendment, not a side effect.

Top-N = 100 everywhere. All aggregates net refunds. "No on-request aggregation": every endpoint is a primary-key or indexed lookup on these tables, or a single-partition DuckDB row scan.

### 7.2 API (`api.fundlens.org/v1`, public, unauthenticated, read-only)

| Endpoint | Source |
|---|---|
| `GET /v1/meta` | `gold.meta` |
| `GET /v1/cycles` · `GET /v1/cycles/{cycle}/races?office=&state=` | `gold.cycle`, `gold.race` |
| `GET /v1/races/{cycle}/{office}/{state}` · `…/{state}-{district}` · `…?special=1` | `race`, `race_candidate`, `race_top_donor`, `race_top_committee` |
| `GET /v1/candidates/{id}` · `GET /v1/candidates/{id}/contributions?cycle=&cursor=` | gold (301 via `candidate_redirect`) · DuckDB scan of `contribution` for `candidate_id` (cycle partition) |
| `GET /v1/committees/{id}` · `…/contributions?cycle=&cursor=` | gold · DuckDB |
| `GET /v1/donors/{id}` · `…/contributions?cycle=&cursor=` | gold (301 via `donor_redirect`) · DuckDB scan of `bucket=donor_id % 256` |
| `GET /v1/search?q=&kind=` | `search_entity` trigram, top 20 |
| `GET /v1/dataset` | list of snapshots from the public bucket manifest |
| `GET /healthz` | Postgres + silver volume reachable |

Donor routes, built by NEU-2052 (`api/routers/donors.py`): a `donor_id` in `gold.donor_redirect` answers `GET /v1/donors/{id}` and `…/contributions` with a cacheable 301 to the id it became, the rest of the path and the query kept. `…/contributions` takes `cycle` optionally: without it the walk reads the donor's bucket of every live cycle, one directory per cycle, newest cycle first, and the cursor carries the cycle of its last row, so a page may end one cycle and start the next. Every `/contributions` row carries its `cycle`.

A candidate alias in `gold.candidate_redirect` (NEU-2127) answers `GET /v1/candidates/{id}` and `…/contributions` the same way: a cacheable 301 to the id it is an alias of, the rest of the path and the query kept.

Responses carry `Cache-Control: public, max-age=3600, s-maxage=604800` and `ETag: <build_id>`; Cloudflare caches everything under `api.fundlens.org` and `publish` purges the zone. Cursor pagination on row lists (page size 100). Errors are RFC 9457 problem details. CORS allows `https://fundlens.org`. A Cloudflare rate-limiting rule (ops setting, not code) caps `/v1/*` per IP. The OpenAPI document is the contract: `frontend/src/api/` is generated from it in CI and a drift check fails the build.

### 7.3 Postgres access

psycopg 3 with a small pool; `prepare_threshold=None` so no server-side prepared plan outlives a schema swap; every query names `gold.` explicitly (no reliance on `search_path`). Alembic manages only `app` (`crosswalk`, `donor_redirect`, `adjudication`, `unmatched_filing`, `resolution_quality`, `donor_id_seq`). `gold*` schemas are owned by the pipeline and never migrated.

## 8. Frontend (`frontend/`)

Routes mirror the API: `/`, `/cycles/{cycle}` (race index by office and state), `/race/{cycle}/{office}/{state}[-{district}]`, `/candidate/{id}`, `/committee/{id}`, `/donor/{id}`, `/search?q=`, `/dataset`, `/methodology`. Each page is one or two TanStack queries against the API; tables sort client-side; ECharts for the per-cycle totals and the race split. Toolchain baseline: port closinglineup's Vite/TS/oxlint/vitest config and its ECharts wrapper. Visual baseline (amended 2026-10-30 by `NEU-2043-spa-shell-cycle-index-search.md`, ADR-0008): Mantine (`@mantine/core`, `@mantine/hooks`) with its default theme, `primaryColor: "blue"`, `defaultColorScheme="auto"`; responsive, phone up; our own `DataTable`, `QueryStatus` and `EChart` over it; `openapi-react-query` as the query layer; no icon package. The cycle switcher is context-aware through a per-route `handle.cycleTarget`; search is a header typeahead plus `/search?q=`. Both are specified in the NEU-2043 spec, which the page tickets inherit. `wrangler.jsonc` declares a static-assets Worker with SPA fallback; Workers Builds: root directory `frontend`, build command `pnpm install --frozen-lockfile && pnpm build`, watch paths `frontend/**`, production branch `main`, no preview deployments (amended 2026-11-09: a preview's `workers.dev` origin is not in the API's CORS list, so it could show only the shell, and CI's `js` job already builds every frontend PR); `VITE_API_BASE_URL` = `https://api.fundlens.org`. Dark/light per system preference. No analytics in v1.

## 9. Public dataset (`data.fundlens.org`)

Produced by `fundlens dataset --snapshot` from the live build. Layout on the public bucket:

```
v1/<snapshot-date>/<table>/cycle=<cycle>/*.parquet    tables: contribution (with donor_id), contributor, donor, committee, candidate, candidate_committee_link, race, independent_expenditure, committee_transfer, organization_receipt
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

Cloudflare setup (zone, R2, tokens, Worker domain), Coolify project setup, first backfill, rollback (`publish --rollback`), re-resolving with `--full`, adding an override, refreshing the DIME file (`refreshing-dime.md`, NEU-2054), adjudicating the ambiguous high-dollar clusters (`adjudicating.md`, NEU-2055).

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

- ~~Whether gold loads via DuckDB's postgres extension or `COPY` from Parquet~~: decided 2026-10-30 in ADR-0007 (DuckDB → CSV → `COPY`); fixture timing in the NEU-2039 spec, real-cycle timing in `docs/capacity.md` (NEU-2046).
- Trained Splink thresholds: defaults above. NEU-2054 produces the precision/recall figure (2026-11-01: tuning was taken out of its scope); tuning against it is a follow-up ticket once the first real validation has run.
- Exact MinIO-vs-R2 parity edge cases (multipart rename semantics): handled in the R2 client ticket with an integration test against MinIO.
- Hetzner Cloud ephemeral runner: out of v1; the capacity record decides.

## 14. Milestones (outline; detail in Linear)

1. **M1 Groundwork** — repo, toolchain, compose, CI, settings, telemetry, R2 client, Cloudflare + Coolify runbooks.
2. **M2 One cycle, committee-level** — extract, seat calendar, silver transforms with earmark dedup and checks, gold without donors, swap publish, purge, API + SPA for races/candidates/committees, deployed for 2024.
3. **M3 Resolution** — contributor keys, normalization, Splink, crosswalk, overrides, donor gold + pages, adjudication, DIME validation, methodology page.
   - **M3.5 Organization money** — `organization_receipt`, the blank-entity-type classifier, committee organization totals and top organizations, committee pages, 2024 run checked against FEC's committee summaries. Before M4's backfill, which would otherwise count pre-2002 organization gifts as individuals' money.
4. **M4 Backfill + IEs** — all cycles since 1980, independent expenditures in race views, capacity record.
5. **M5 Weekly** — scheduled run for the current cycle, incremental resolution, Kuma deadman, rollback runbook.
6. **M6 Public dataset** — snapshot publisher, public bucket, schema docs, license + notice, `/dataset` page.
