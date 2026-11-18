# NEU-2067 — snapshot copies run several at a time, and the dataset goes public on data.fundlens.org

**Ticket:** [NEU-2067](https://linear.app/neuroticsasquatch/issue/NEU-2067) · **Story:** NEU-2024 · **Milestone:** M6 Public dataset
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §9, §10.2, §5.6, §10.1 (amended by this spec, §6)
**Blocked by:** NEU-2065 (dataset docs), NEU-2066 (`/v1/dataset` and the page), NEU-2063 (the scheduled task), NEU-2060 (backfill, Done). **Related:** NEU-2064 (the publisher, Done), NEU-2033 (Cloudflare runbook, Done).

Planned 2026-11-17. `/implementit NEU-2067` implements straight from this file, **after NEU-2065 and NEU-2066 have merged** (§1.2). One implementation PR (code, tests, the runbook, spec amendments), then one docs-only as-built PR once the runbook has been walked. The runbook's steps are the user's; Done is set by hand.

## 1. What and why

Two things stand between the snapshot publisher (NEU-2064) and a public dataset.

**The snapshot is too slow to join the Sunday run.** The first production snapshot (2026-11-17, build `20261117T030329Z`, 24 cycles) took 221m18s: 1h45m for the dated snapshot (hash and copy) and 1h56m for the `latest/` copy (copy only). It holds 6,340 objects: 6,338 Parquet files (6,144 of them `contribution` parts), `overrides.yaml` and `manifest.json`. The copy-only pass was the slower of the two, so the time is in the server-side copies, about 1.1 s each, run one at a time by `R2.copy_from` in `_silver_table` and `_refresh_latest` (`src/fundlens/publish/dataset.py`). `latest/` is recopied in full every week.

**The bucket is private.** `fundlens-public` has no public access, no custom domain and no CORS policy, and the Sunday task runs without `--dataset`.

This ticket runs the copies in a thread pool, re-times a snapshot on prod, and then launches: custom domain, CORS, the shared rate limit checked against a real read, `--dataset` on the Sunday task, the README, and the first unattended Sunday confirmed.

### 1.1 Decisions this spec pins (grilled 2026-11-17)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| How far the speed-up goes | A thread pool around the per-object work in both passes. Nothing else. | Skipping files in `latest/` that match the newest snapshot would cut the weekly `latest/` work to about 1/24, but adds a rule that depends on a server-side copy keeping its source's ETag. At 16 workers both passes should already be minutes. It becomes a follow-up ticket only if the re-time misses its target (§5.2). |
| Pool size | A setting, `DATASET_COPY_WORKERS`, default 16. | The right number is only known after the prod re-time, and every merge to `main` redeploys `pipeline`. A constant would cost a PR per try. |
| Re-time target | A full `fundlens dataset --snapshot` in **30 minutes or less**. | "Well under 3h41m" is not checkable. Linear scaling at 16 workers predicts about 15 minutes; 30 leaves room. A looser 60 minutes was rejected. |
| The 2026-11-17 trial snapshot | Deleted by hand after the re-time succeeds and before the bucket is public. | It was taken by the sequential code as NEU-2064's check. Keeping it would open `/dataset` with two entries that may hold the same build. |
| When this is implemented | After NEU-2065 and NEU-2066 merge. | The runbook must quote the README's real one-liner and the real `/dataset` output, and NEU-2065 edits `publish/dataset.py` too. Implementing now with gated steps risks stale commands and a merge conflict. Splitting the speed-up into its own ticket was also rejected. |
| When `--dataset` goes on the task | As soon as the re-time passes, whatever the state of NEU-2063's two-Sunday count. | The user's call. **Accepted risk:** a snapshot that fails under `run --dataset` fails the run (exit 1, `fundlens/weekly` down) with the build already live, and that could spoil a Sunday NEU-2063 is counting. |
| Proof of the weekly snapshot | A DoD box: the first Sunday run with the flag is checked (§5.9). | Reading the task row back proves the edit, not that a snapshot is published unattended. |
| Cache rule on `data.fundlens.org` | None at launch. | R2 egress is free and reads cost $0.36 per million after 10 million free a month (Cloudflare's R2 pricing page, read 2026-11-17). A rule on `latest/` would let a reader get a new manifest with older cached parts whose `sha256` no longer matches. |
| The zone's rate-limit rule | Kept as one rule for both hosts. Its count is raised only as far as a real read needs (§5.6). | `api: /v1 per IP` matches on path alone (`/v1/`, 100 requests per 10 s per IP), and every dataset path starts with `/v1/`. Scoping it to API routes would remove the per-IP cost cap on the dataset. Leaving it at 100 would likely block the story's own one-liner (256 files in one cycle). |
| Announcement | A dataset section and one badge in the repo `README.md`, landed in the as-built PR. **No GitHub release.** | The repo has no tags or releases, and its code is not versioned. Landing the README change in the implementation PR would link to a domain that is not serving yet. |
| Public access | The custom domain only. The bucket's `r2.dev` URL stays disabled. | `r2.dev` is rate-limited and not meant for production. |
| Launch gate | The bucket goes public only once `v1/README.md` and `v1/LICENSE` are in it. | Contributor records must not be public without the license and the 11 CFR 104.15 notice. |
| CORS | Any origin; `GET` and `HEAD`; `Range` allowed; the range headers exposed. | The ticket says `GET`. `HEAD` is added because DuckDB in a browser issues `HEAD` before its range reads. |

### 1.2 Before implementing

NEU-2065 and NEU-2066 must be merged. Read what they shipped, not their ticket text:

- the README's DuckDB one-liner, as written in `docs/dataset/README.md`;
- how and when the publisher uploads `docs/dataset/*` to `v1/` (on every run, or only with a new snapshot);
- what `/v1/dataset` returns and what the `/dataset` page shows for a snapshot.

A comment on NEU-2065 (2026-11-17) warns that DuckDB probably cannot expand a glob over plain `https://`, so the story's one-liner may have changed shape. The runbook uses whatever NEU-2065 shipped.

## 2. Definitions

`CONTEXT.md` already defines **Snapshot** (one dated release of the public dataset; `latest` points at the newest) and **Live build**. No glossary change and no ADR: nothing here is hard to reverse.

In this spec a **pass** is one of the snapshot's two bulk copies: the *snapshot pass* (private bucket to `v1/<date>/`, with hashing) and the *latest pass* (`v1/<date>/` to `v1/latest/`).

## 3. The code change

### 3.1 Setting

`Settings.dataset_copy_workers: int = Field(default=16, ge=1, alias="DATASET_COPY_WORKERS")`, documented where its siblings are (`.env.example` if present, spec §10.1's env list). `docker-compose.prod.yml` passes it through the way it passes `DUCKDB_THREADS`, so Coolify can set it.

`R2.from_settings` sizes botocore's pool from it: `max_pool_connections=max(10, settings.dataset_copy_workers)`. A pool smaller than the worker count is not an error (urllib3 opens and discards extra connections, with a warning), but it wastes a TLS handshake per copy.

### 3.2 One pool helper

One private helper in `publish/dataset.py` runs a function over a sequence of items with a `ThreadPoolExecutor(max_workers=workers)`:

- results come back **in input order**, so the manifest's `files` stay in key order and a manifest taken at 1 worker is byte-identical to one taken at 16;
- on the first exception it cancels what has not started (`shutdown(cancel_futures=True)`), lets the copies in flight finish, and re-raises that exception;
- `workers=1` goes through the same path.

`snapshot()` gains a keyword `workers: int` and passes it down. The CLI's `_snapshot` passes `settings.dataset_copy_workers`.

### 3.3 The snapshot pass

Today `_silver_table` lists, checks, hashes and copies one cycle at a time. Per-cycle pooling would leave the eight one-file-per-cycle tables (192 objects) sequential. So the pass becomes two phases:

1. **List and check, sequentially.** For every table in `DATASET_TABLES` and every cycle in `live.cycles`: list the partition, raise `BuildNotReady` for a rewrite sentinel or a table with no parts, and collect one job per Parquet object (source `Listed`, destination path, table). `BuildNotReady` is now raised **before anything is copied**.
2. **Hash and copy, pooled.** One pool run over every job of every table. A job is today's per-object body unchanged: `_digest`, then `public.copy_from(store, key, dest, if_match=obj.etag)`, returning the `ManifestFile` and its rows. The results are grouped back into one `ManifestTable` per table, in `DATASET_TABLES` order.

`CopySourceIfMatch` still guarantees the manifest names only bytes that were hashed, however long a job waited in the queue.

**Download fallback.** `_digest` downloads to `work / "object.parquet"` when no local copy matches. Under a pool that path is shared. Each job gets its own file under `work`, named from its destination path (`_flat` of it is unique per object). It is still deleted in `finally`.

`_donor`, `_crosswalk`, the two `_put`s and the manifest stay on the calling thread, in today's order. The psycopg connection is never used from a worker.

### 3.4 The latest pass

`_refresh_latest` copies every key but the manifest through the pool, then the manifest alone, then deletes stale keys, as today. The manifest-last rule is unchanged: a `latest/manifest.json` naming a snapshot still means its files are all there.

### 3.5 Logging

One `log.info` per pass when it ends: the number of objects, the destination prefix, the seconds it took and the worker count. The runbook reads the two lines to split a re-time into its passes, as NEU-2064's baseline was split.

### 3.6 Not changed

Idempotency per date, the manifest's shape (M6 shared contract), retention, `R2.atomic_publish`, and `R2.copy_from` itself (still `client.copy`, which issues a `HeadObject` before each copy).

## 4. Tests

All in `tests/integration/test_dataset.py` against MinIO, reusing the module-scoped `published` fixture. No test rebuilds pipeline state of its own. After the commit, read the hook's slowest-tests list: a new test near the top is a defect.

Concurrency is asserted on **observed in-flight copies, never on elapsed time** (NEU-2340's rule). The mechanism is the implementer's, but it must not hang when the object count is odd.

- **The snapshot pass copies several objects at a time.** With `workers=4`, a wrapped `copy_from` sees at least two calls in flight together.
- **The latest pass copies several objects at a time.** The same assertion on `_refresh_latest`'s copies.
- **One worker and many give the same manifest.** A snapshot taken with `workers=1` and one with `workers=4` have equal `tables`, files in the same order.
- **A failed copy fails the snapshot and leaves no manifest.** `copy_from` raising on one key makes `snapshot` raise; the snapshot root has no `manifest.json`; a rerun takes it.
- **Hashing from downloads works concurrently.** With an empty local cache and `workers=4`, the manifest's `tables` equal the cached run's. This extends the existing download-versus-cache comparison and is what exercises §3.3's per-job download path.
- **A build that is not ready copies nothing.** Extends `test_a_build_having_its_donor_ids_rewritten_is_not_snapshotted`: after the refusal nothing exists under the snapshot root.
- **The setting rejects zero.** A unit test: `DATASET_COPY_WORKERS=0` fails validation.

Every existing test in the file passes unchanged apart from passing `workers`.

## 5. The runbook: `docs/runbooks/dataset-launch.md`

Written in the shape of `weekly.md` and `cloudflare-setup.md`: *Before you start*, a *Facts* or *As built* table, numbered steps each with **Expected** or **Check**, and a *Log* that is appended to and never rewritten.

**Every step carries its exact commands and expected output inline.** It never says "run step N of another runbook": the `fl` and `cdb` helpers and the tmux setup are pasted in, as `weekly.md` §0 has them. IDs and names only; no token or secret.

Steps, in this order:

### 5.1 Before you start

- NEU-2065 and NEU-2066 are merged and deployed, and so is this ticket's PR. The first step checks: `fundlens dataset --help` in the `pipeline` container, and the setting's value read back from the container.
- Not on a Sunday between 03:00 UTC and the weekly run's end, and no merge to `main` while a snapshot runs (a merge redeploys `pipeline` and kills a `docker exec`).
- A snapshot is dated by the UTC date when it starts. Don't start one in the hour before midnight UTC.

### 5.2 Re-time a full snapshot

`time docker exec … fundlens dataset --snapshot` in tmux, on any UTC date after 2026-11-17, at the default 16 workers.

- **Expected:** `took snapshot <date> of build <B>`, `latest/: copied`, `removed snapshots: none`, and the two per-pass log lines (§3.5).
- **Verify:** `<B>` is `gold.meta`'s build; the manifest summary shows 24 cycles, 1980 to 2026, and a non-zero row count for every table (NEU-2064's check, command pasted in).
- **Pass:** `real` is 30 minutes or less.
- **If it is over 30 minutes:** retry on the **next UTC date** with `docker exec -e DATASET_COPY_WORKERS=32`. Not the same day: a same-day retake after deleting the day's directory writes an identical manifest, so `latest/` is not recopied and its pass is not timed. If 32 passes, set `DATASET_COPY_WORKERS=32` on the resource in Coolify and redeploy before §5.3.
- **If 32 is also over 30 minutes:** stop. Record both runs, do not edit the task, and open a ticket for skipping unchanged objects in `latest/` (and for `copy_object` without the `HeadObject`).
- **If it fails with throttling** (`SlowDown`, 429 or 503 after botocore's retries): retry at 8 on the next UTC date and record it.

Each run gets a row in `docs/capacity.md` (§6).

### 5.3 Add `--dataset` to the scheduled task

Only once §5.2 has passed. Coolify → the resource → *Scheduled Tasks* → `fundlens weekly` → Command `opentelemetry-instrument fundlens run --scheduled --dataset`. Frequency, container and the 21600 s timeout stay. Read the row back from `coolify-db` with the query `weekly.md` §4 uses, pasted in.

**Expected:** one row with the new command, `"frequency": "0 3 * * 0"`, `"enabled": true`.

NEU-2063's two-Sunday count may still be open when this runs (§1.1). Say so in the Log, with the date.

### 5.4 Delete the trial snapshot

1. Check `v1/latest/manifest.json` names the re-timed date, not 2026-11-17.
2. List `v1/2026-11-17/` and print its object count.
3. Delete it with `R2.delete_prefix` from the `pipeline` container (the command pasted in).
4. List the snapshot directories.

**Expected:** only the re-timed date (and any Sunday snapshot taken since) and `latest/`.

### 5.5 Go public

1. **Gate:** `v1/README.md`, `v1/LICENSE`, `v1/CHANGELOG.md` and at least one `v1/schema/*.json` exist in the bucket. If not, stop: the bucket does not go public without them.
2. R2 → `fundlens-public` → *Settings* → *Custom Domains* → connect `data.fundlens.org`. Cloudflare creates the DNS record. Wait for *Active*. The *Public Development URL* (`r2.dev`) stays **Disabled**.
3. *CORS Policy* → the JSON below.

```json
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["Range"],
    "ExposeHeaders": ["Content-Length", "Content-Range", "Accept-Ranges", "ETag"],
    "MaxAgeSeconds": 86400
  }
]
```

**Checks**, each with its command and expected output:

- `curl -sI -H 'Origin: https://example.org' https://data.fundlens.org/v1/latest/manifest.json` returns `200` with `access-control-allow-origin: *`. The `Origin` header is in the command because R2 is expected to send CORS headers only when a request carries one. Record what a request without it returns.
- A range read of one Parquet file returns `206` and its first four bytes are `PAR1`.
- `https://data.fundlens.org/v1/README.md` returns `200`.
- `fundlens-data` still shows *Public access: Disabled* and no custom domain.
- No cache rule is added. Record `cf-cache-status` for a Parquet file and for `manifest.json` as built.

### 5.6 The rate limit, measured

Run the README's DuckDB one-liner for cycle 2024, as NEU-2065 shipped it, from the laptop.

- If it returns a count with no 429, the rule stays at 100 per 10 s.
- If it is blocked, raise the count of `api: /v1 per IP` to **300**, then **1,000**, then **3,000**, stopping at the lowest value at which the one-liner **passes twice in a row**. Nothing else in the rule changes.
- If 3,000 is not enough, stop and bring it back to the user. Don't go higher or rewrite the rule.

Record the as-built count. The API shares it.

### 5.7 The story's checks

- The one-liner's count equals the counted contribution count `/cycles/2024` shows on fundlens.org. The runbook gives the API call that returns that number and the field to read.
- `/dataset` on fundlens.org lists the snapshot: its date, build and tables, with download links on `data.fundlens.org`.

### 5.8 As built, and the README

A docs-only PR, `docs(runbooks): dataset launch as built (NEU-2067)`:

- this runbook's As built table and Log;
- `cloudflare-setup.md`: the As built row for the buckets (`fundlens-public` public by custom domain `data.fundlens.org`) and the rate-limit rule's count, plus a Log entry; its "Not in this runbook" line now points here;
- `weekly.md`: the Facts row for the task's command, how long a run takes with the snapshot, and its "Not in this runbook" paragraph;
- project spec §5.6: the task now runs with `--dataset`;
- `docs/capacity.md`: the re-time rows (§6);
- repo `README.md`: a *Dataset* section (what it is, `https://data.fundlens.org/v1/README.md`, the one-liner, CC BY 4.0, the 104.15 notice in one sentence) and one static badge linking to the dataset README.

### 5.9 The first Sunday

After the first Sunday run with the flag:

- its row in `scheduled_task_executions` shows success, and its output ends with the three snapshot lines;
- `v1/<that Sunday>/manifest.json` exists and its `build_id` is the run's build;
- `v1/latest/manifest.json` is the same manifest;
- the run finished inside the 21600 s timeout. Record its total time and the two passes' seconds in the Log and in `capacity.md`.

The commands are pasted in. Append the result to the Log (a second small docs commit).

## 6. Docs changed in the implementation PR

- **Project spec §9:** "Amended by NEU-2067": the readiness checks run for every table and cycle before the first copy; the copies of both passes run `DATASET_COPY_WORKERS` (default 16) at a time; the manifest is the same at any worker count.
- **Project spec §10.1:** `DATASET_COPY_WORKERS` joins the env list.
- **Project spec §10.2:** `fundlens-public` is public by custom domain only, `r2.dev` off; the CORS policy; no cache rule on `data.fundlens.org` and why; the rate-limit rule covers both hosts because it matches on path.
- **Project spec §10.5:** `dataset-launch.md` (NEU-2067) joins the runbook list.
- **`docs/capacity.md`:** a new *Dataset snapshot* section. One row per full snapshot timed by hand or on a Sunday: date, build, SHA, workers, objects, snapshot pass s, latest pass s, wall time, notes. Its first row is NEU-2064's baseline (2026-11-17, sequential, 221m18s, 1h45m + 1h56m). The re-time rows come with the as-built PR.

`CONTEXT.md` and `docs/adr/` are not changed.

## 7. Definition of done

- [ ] The copies of both passes run through the pool: the two "several at a time" tests of §4 pass, and so does every other test in `tests/integration/test_dataset.py`.
- [ ] A full prod `fundlens dataset --snapshot` took 30 minutes or less, and its row sits beside the 3h41m baseline in `docs/capacity.md`, before `--dataset` went on the scheduled task.
- [ ] `v1/2026-11-17/` was deleted before the bucket went public.
- [ ] `curl -sI -H 'Origin: https://example.org' https://data.fundlens.org/v1/latest/manifest.json` returns 200 with `access-control-allow-origin: *`.
- [ ] The README's DuckDB one-liner returns the same count as `/cycles/2024` on fundlens.org, twice in a row with no 429, and the rate-limit rule's as-built count is recorded.
- [ ] `/dataset` lists the first real snapshot.
- [ ] The `fundlens weekly` task's row in `coolify-db` reads `opentelemetry-instrument fundlens run --scheduled --dataset`.
- [ ] The first Sunday run with the flag exited 0 inside the task timeout, `v1/<that Sunday>/manifest.json` names its build, and `v1/latest/manifest.json` matches it.
- [ ] The repo `README.md` has its *Dataset* section and badge.

## 8. Out of scope

- Skipping unchanged objects in `latest/`, and `copy_object` without the `HeadObject`: a follow-up ticket only if §5.2 fails at 32 workers.
- Any cache rule on `data.fundlens.org`. Revisit if R2's Class B operations approach the free 10 million a month.
- A GitHub release or tag.
- The README's one-liner and the dataset docs (NEU-2065), `/v1/dataset` and the page (NEU-2066).
- Changing what the rate-limit rule matches on, or a second rule.
- Anything on the Robot box beyond the commands the runbook gives.
- Waiting for NEU-2063's two unattended Sundays before editing the task (§1.1).
