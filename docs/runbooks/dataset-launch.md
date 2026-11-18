# Runbook: the dataset launch

How the public dataset goes live on `data.fundlens.org` (NEU-2067; spec §9, §10.2, §5.6;
`docs/specs/NEU-2067-dataset-launch.md`). The steps are done once, top to bottom: re-time a full snapshot with the
copies running several at a time, put `--dataset` on the Sunday task, delete the trial snapshot, make
`fundlens-public` public on its custom domain with CORS, measure the rate limit against the README's one-liner,
check the story's own checks, record the as-built values, and check the first Sunday that publishes a snapshot.
Append to the [Log](#log) at the bottom; never rewrite it.

**Not in this runbook:** the scheduled task itself, its monitors and rollback ([weekly.md](weekly.md), NEU-2063);
the zone, the buckets and the rate-limit rule's creation ([cloudflare-setup.md](cloudflare-setup.md), NEU-2033); the
dataset's documentation (`docs/dataset/`, NEU-2065) and `/dataset` (NEU-2066).

## Before you start

- NEU-2065, NEU-2066 and NEU-2067's implementation PR are merged and deployed. Step 1 checks.
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo on an
  up-to-date `main`, and `curl`, `jq` and the DuckDB CLI are installed (`brew install duckdb`; the one-liner needs
  1.1 or later for `SET VARIABLE`). You can sign in to Coolify and to the Cloudflare account that holds
  `fundlens.org`.
- **When.** Not on a Sunday between 03:00 UTC and the weekly run's end. Not within 45 minutes of 11:00 UTC on any
  day, or on a Saturday from 13:00 UTC: Dependabot's auto-merge runs then, and every merge to `main` redeploys
  `pipeline`, which kills a running `docker exec` (weekly.md, *Facts*). Merge nothing yourself while a snapshot
  runs.
- **Midnight UTC.** A snapshot is dated by the UTC date it starts on. Don't start one in the hour before 00:00
  UTC: a run that crosses midnight is still dated the day before, and the rerun the step may ask for would then be
  dated the same day.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`), resource UUID `lvch8zyndujjzkz16ksys8im` |
| Buckets | `fundlens-data` (private, stays private) and `fundlens-public` (the dataset), both on account `6fa481ae677c7dc06dfe81f4522dfa84` |
| Public address | `https://data.fundlens.org/v1/`: `README.md`, `LICENSE`, `CHANGELOG.md`, `schema/<table>.json`, `<YYYY-MM-DD>/` per snapshot, `latest/` |
| The baseline | 2026-11-17, build `20261117T030329Z`, one copy at a time: 221m18s, 1h45m for the snapshot pass and 1h56m for the latest pass, 6,340 objects (`capacity.md`, *Dataset snapshot*) |
| The two passes | The snapshot pass hashes each live silver file and copies it into `v1/<date>/`; the latest pass copies `v1/<date>/` into `v1/latest/`, its manifest last. Each logs one line when it ends: `hashed and copied <n> objects to v1/<date>/ in <s>s, <w> at a time`, and `copied <n> objects to v1/latest/ in <s>s, <w> at a time` |
| `DATASET_COPY_WORKERS` | The copies each pass runs at once, default 16 (`docker-compose.prod.yml`). R2's client keeps that many connections open |
| Re-time target | A full `fundlens dataset --snapshot` in **30 minutes or less** |
| Rate-limit rule | `api: /v1 per IP`, **URI Path** starts with `/v1/`, 100 requests per 10 s per IP, block 10 s. It matches on path only (the Free plan's one choice), so it covers `data.fundlens.org/v1/…` as well as the API |
| Cache rule on `data.fundlens.org` | None. R2 egress is free, and a cached `latest/` could serve a new manifest beside older parts whose `sha256` no longer matches |
| The launch gate | `fundlens-public` goes public only once `v1/README.md` and `v1/LICENSE` are in it: contributions are never public without the license and the 11 CFR 104.15 notice |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a snapshot running if the SSH session drops.
tmux new -s fundlens-dataset
```

In the tmux session, define the helpers. Paste the whole block:

```bash
# VM, in tmux
mkdir -p ~/fundlens-dataset && cd ~/fundlens-dataset
# Container names change on every deploy: look each one up when it is used.
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# psql in the fundlens database.
pg() { docker exec "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
# psql in Coolify's own database.
cdb() { docker exec -i coolify-db psql -U coolify -d coolify -P pager=off "$@"; }
# Python against the public bucket, as `p`: `pub '<statements>'`.
pub() { docker exec "$(fl pipeline)" python -c "from fundlens.r2 import R2; from fundlens.settings import get_settings; s = get_settings(); p = R2.from_settings(s, bucket=s.r2_public_bucket); $1" 2>&1 | grep -v '^{'; }
# A manifest's summary: `msum v1/latest/` or `msum v1/<date>/`.
msum() { pub "import json; m = json.loads(p.get('$1manifest.json')); c = sorted(m['cycles'], key=int); print(m['snapshot_date'], m['build_id'], c[0], c[-1], len(c)); [print(t, v['rows'], len(v['files'])) for t, v in m['tables'].items()]"; }
# The snapshot directories in the public bucket.
dirs() { pub "print(*p.list_dirs('v1/'), sep='\n')"; }
```

**Expected:** no output.

## 1. Preflight

```bash
# VM
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES
docker exec "$(fl pipeline)" fundlens dataset --help | grep -- --snapshot
docker exec "$(fl pipeline)" python -c 'import inspect; from fundlens.publish import dataset; from fundlens.settings import get_settings; print("workers" in inspect.signature(dataset.snapshot).parameters, get_settings().dataset_copy_workers)' 2>&1 | grep -v '^{'
pg -Atc "SELECT build_id, published_at FROM gold.meta"
dirs
msum v1/latest/
```

**Expected:**

- `service.version=<sha>`: write the SHA in the Log.
- The `--snapshot` option's help line.
- `True 16`. `False` means this ticket's code is not deployed: Coolify → the `fundlens` resource → *Deploy*, wait
  for it to finish, and run this step again.
- The live build `<B>` and when it was published.
- `v1/2026-11-17/` and `v1/latest/`, and `v1/schema/` if a snapshot has run since NEU-2065 deployed (the
  trial snapshot predates the documentation, so it may not be there yet). Nothing else.
- `2026-11-17 20261117T030329Z 1980 2026 24`, then one line per table with its rows and files: the trial
  snapshot.

## 2. Re-time a full snapshot

On any UTC date after 2026-11-17, at the default 16 workers:

```bash
# VM, in tmux
D=$(date -u +%F); echo "$D"
{ time docker exec "$(fl pipeline)" fundlens dataset --snapshot; } 2>&1 | tee "snapshot-$D.log"
grep -v '^{' "snapshot-$D.log"
grep -E 'hashed and copied|objects to v1/latest/' "snapshot-$D.log" | jq -r .message
```

**Expected:** after the run, which should take about 15 minutes:

```
docs: put README.md, LICENSE, CHANGELOG.md, schema/…
took snapshot <D> of build <B>
latest/: copied
removed snapshots: none
real    <m>m<s>s
```

and the two pass lines:

```
hashed and copied 6336 objects to v1/<D>/ in <s1>s, 16 at a time
copied 6340 objects to v1/latest/ in <s2>s, 16 at a time
```

`docs: put …` is the documentation's first upload: the trial snapshot of 2026-11-17 ran before NEU-2065
published any. `docs: unchanged` is fine too: a snapshot since NEU-2065 deployed put it already. The snapshot
pass's 6,336 objects are the silver files only (6,144 `contribution` parts and 24 per other table); the donor and
crosswalk files, `overrides.yaml` and the manifest are written after it, one at a time. If the snapshot pass's
count differs from 6,336, the live build has changed shape since 2026-11-17: note it, and go on.

**Verify:**

```bash
# VM
pg -Atc "SELECT build_id FROM gold.meta"
msum "v1/$D/"
```

**Expected:** the same `<B>` as the run printed; then `<D> <B> 1980 2026 24` and one line per table,
`contribution` first and `crosswalk` last, each with rows above 0.

**Pass:** `real` is **30 minutes or less**. Write `real`, `<s1>`, `<s2>` and the workers in the Log, and add a row
to `docs/capacity.md` → *Dataset snapshot* in step 7's PR.

- **Over 30 minutes:** retry at 32 workers, on the **next UTC date**. Not the same day: a same-day retake after
  deleting the day's directory writes an identical manifest, so `latest/` is not copied again and its pass goes
  untimed.

  ```bash
  # VM, in tmux, the next UTC date
  D=$(date -u +%F); echo "$D"
  { time docker exec -e DATASET_COPY_WORKERS=32 "$(fl pipeline)" fundlens dataset --snapshot; } 2>&1 | tee "snapshot-$D.log"
  grep -v '^{' "snapshot-$D.log"
  grep -E 'hashed and copied|objects to v1/latest/' "snapshot-$D.log" | jq -r .message
  ```

  **Expected:** `took snapshot <D> of build <B>`, `latest/: copied`, `removed snapshots: none`, `real`, then the
  pass lines `hashed and copied 6336 objects to v1/<D>/ in <s1>s, 32 at a time` and `copied 6340 objects to
  v1/latest/ in <s2>s, 32 at a time`. **Pass:** `real` is 30 minutes or less. If it passes, set the resource's variable in Coolify → the `fundlens`
  resource → *Environment Variables* → `DATASET_COPY_WORKERS` = `32`, *Save*, *Deploy*, and check:

  ```bash
  # VM, once the deploy has finished
  docker exec "$(fl pipeline)" python -c 'from fundlens.settings import get_settings; print(get_settings().dataset_copy_workers)' 2>&1 | grep -v '^{'
  ```

  **Expected:** `32`.
- **32 is also over 30 minutes:** stop. Record both runs in the Log and in `capacity.md`, don't edit the scheduled
  task, and open a ticket for skipping the unchanged objects in `latest/` (and for `copy_object` without the
  `HeadObject` that `client.copy` sends first).
- **A run fails with throttling** (`SlowDown`, or 429 or 503 after botocore's retries): retry at 8 workers, on the
  next UTC date, and record it:

  ```bash
  # VM, in tmux, the next UTC date
  D=$(date -u +%F); echo "$D"
  { time docker exec -e DATASET_COPY_WORKERS=8 "$(fl pipeline)" fundlens dataset --snapshot; } 2>&1 | tee "snapshot-$D.log"
  grep -v '^{' "snapshot-$D.log"
  grep -E 'hashed and copied|objects to v1/latest/' "snapshot-$D.log" | jq -r .message
  ```

  **Expected:** as at 16, with `8 at a time` in both pass lines. If it passes, set `DATASET_COPY_WORKERS` = `8` on
  the resource in Coolify → *Environment Variables*, *Save*, *Deploy*, and check that the `get_settings()` command
  above prints `8`.

## 3. Add `--dataset` to the scheduled task

Only once step 2 has passed.

1. Coolify → `fundlens` → `production` → the resource → *Scheduled Tasks* → `fundlens weekly` → *Command*:
   `opentelemetry-instrument fundlens run --scheduled --dataset`. The frequency, the container (`pipeline`) and the
   21600 s timeout stay as they are. *Save*.
2. Read it back from Coolify's database:

   ```bash
   # VM
   cdb -c "SELECT to_jsonb(t) - 'id' - 'uuid' FROM scheduled_tasks t WHERE t.name = 'fundlens weekly'"
   ```

**Expected:** one row with `"command": "opentelemetry-instrument fundlens run --scheduled --dataset"`,
`"frequency": "0 3 * * 0"`, `"enabled": true` and the container `pipeline`. Write the row in the Log, with today's
date.

From the next Sunday the run ends with a snapshot. A snapshot that fails then fails the run: exit 1 and
`fundlens/weekly` down, with that Sunday's build already live. If NEU-2063's two unattended Sundays are still being
counted, say so in the Log: a failed snapshot would spoil one of them. That is an accepted risk (the spec, §1.1).

## 4. Delete the trial snapshot

`v1/2026-11-17/` was taken by the code that copied one object at a time, as NEU-2064's check. Keeping it would open
`/dataset` with two entries. It goes before the bucket is public.

```bash
# VM
msum v1/latest/ | head -1
pub "print(len(p.list_keys('v1/2026-11-17/')))"
```

**Expected:** `latest/` names step 2's date `<D>` and build, **not** 2026-11-17; then about 6,340 objects: write
the count down. If `latest/` still names 2026-11-17, stop: step 2 did not finish its latest pass.

```bash
# VM
pub "print(p.delete_prefix('v1/2026-11-17/'))"
dirs
```

**Expected:** the number of objects deleted, the count you wrote down; then `v1/<D>/`, `v1/latest/` and `v1/schema/`, plus any Sunday
snapshot taken since step 3. If a re-time failed in step 2 and was retried, its date is also there and holds the
same build. Delete it too, so the passing re-time's date is the only one left from step 2:

```bash
# VM. <F> is the failed re-time's date.
pub "print(p.delete_prefix('v1/<F>/'))"
dirs
```

**Expected:** its object count, then the listing without `v1/<F>/`.

## 5. Go public

### 5.1 The gate

```bash
# VM
pub "[print(k, p.exists('v1/' + k)) for k in ('README.md', 'LICENSE', 'CHANGELOG.md')]; print('schemas', len(p.list_keys('v1/schema/')))"
```

**Expected:** `README.md True`, `LICENSE True`, `CHANGELOG.md True`, `schemas 11`. If any is `False` or there are
no schemas, **stop**: the bucket does not go public without them. Every `fundlens dataset --snapshot` puts them, so
step 2's run should have.

### 5.2 Custom domain and CORS

1. Cloudflare → *R2 Object Storage* → `fundlens-public` → *Settings* → *Custom Domains* → *Add* →
   `data.fundlens.org` → *Continue* → *Connect domain*. Cloudflare creates the DNS record. Wait until the domain
   shows **Active**.
2. On the same page, *Public Development URL* (`r2.dev`) stays **Disabled**.
3. *CORS Policy* → *Add CORS policy* → the JSON below, replacing whatever the editor holds → *Save*:

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

   `HEAD` is there because DuckDB in a browser sends `HEAD` before its range reads.
4. Do **not** add a cache rule for `data.fundlens.org` (Facts).
5. `fundlens-data` → *Settings*: *Public Development URL* **Disabled**, no custom domain. Nothing changes there.

**Check:** `fundlens-public` → *Settings* shows `data.fundlens.org` **Active** under *Custom Domains*, *Public
Development URL* **Disabled**, and the CORS policy above under *CORS Policy*; Cloudflare → `fundlens.org` → *DNS*
has a `data` record of type R2; *Caching* → *Cache Rules* still holds only `api: cache everything, respect origin`;
and `fundlens-data` shows no custom domain and *Public Development URL* **Disabled**.

### 5.3 Checks

```bash
# laptop
U=https://data.fundlens.org/v1
dig +short data.fundlens.org
curl -sI -H 'Origin: https://example.org' "$U/latest/manifest.json" | grep -iE '^HTTP|^access-control|^cf-cache-status|^content-type'
curl -sI "$U/latest/manifest.json" | grep -iE '^HTTP|^access-control'
curl -s -o /dev/null -w '%{http_code}\n' -X OPTIONS -H 'Origin: https://example.org' -H 'Access-Control-Request-Method: GET' -H 'Access-Control-Request-Headers: range' "$U/latest/manifest.json"
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' "$U/README.md"
curl -s -o /dev/null -w '%{http_code}\n' "$U/LICENSE"
```

**Expected:**

- `dig` prints Cloudflare addresses.
- With `Origin`: `HTTP/2 200`, `access-control-allow-origin: *`, a `content-type`, and a `cf-cache-status` line if
  Cloudflare sends one. Write the `cf-cache-status` value in the Log.
- Without `Origin`: `HTTP/2 200`. R2 is expected to send CORS headers only to a request that carries an `Origin`:
  record whether this one has `access-control-allow-origin` or not.
- The preflight: `200` or `204`.
- `200 text/markdown; charset=utf-8`, then `200`.

A range read of one Parquet file:

```bash
# laptop
P=$(curl -sS "$U/latest/manifest.json" | jq -r '.tables.race.files[0].path'); echo "$P"
curl -s -o /dev/null -w '%{http_code}\n' -r 0-3 "$U/latest/$P"
curl -s -r 0-3 "$U/latest/$P"; echo
curl -sI "$U/latest/$P" | grep -iE '^cf-cache-status|^accept-ranges'
```

**Expected:** `race/cycle=1980/part-0000.parquet` (or another `race/cycle=…` path), `206`, `PAR1`, and
`accept-ranges: bytes`. Write this file's `cf-cache-status` in the Log beside the manifest's.

A `403` or `404` on everything means the custom domain is not Active yet: wait, and run the checks again.

## 6. The rate limit, measured

The README's DuckDB one-liner reads every 2024 contribution part, 256 files and a few requests each, from one IP,
against a rule that allows 100 requests per 10 s. Run it as the README has it:

```bash
# laptop
cd ~/projects/fundlens && git switch main && git pull
SQL=$(perl -0ne 'print $1 if /^duckdb -c "(.+?)"$/ms' docs/dataset/README.md); echo "$SQL"
duckdb --version
time duckdb -c "$SQL"
```

**Expected:** the SQL as the README prints it; the DuckDB version (write it in the Log); then one row,
`contributions` and `dollars`, and the time. A block shows as an HTTP error from DuckDB naming `429` (or
`HTTP GET error`, `Too Many Requests`).

- **It returns a row with no 429:** run it once more straight away. If that passes too, the rule stays at
  **100**.
- **It is blocked:** Cloudflare → `fundlens.org` → *Security* → *Security rules* → `api: /v1 per IP` → *Edit* →
  *When rate exceeds*: **300** requests per 10 seconds → *Deploy*. Nothing else in the rule changes. Wait 10 s for
  the block to lapse, then run it twice in a row:

  ```bash
  # laptop
  sleep 10; time duckdb -c "$SQL"; time duckdb -c "$SQL"
  ```

  **Expected:** two rows, no 429. Still blocked: edit the rule's count to **1,000**, *Deploy*, and run the same
  `sleep 10; …` line; still blocked, **3,000**, and the same line again. Stop at the lowest count at which both
  runs pass.
- **3,000 is not enough:** stop and bring it back. Don't go higher, and don't change what the rule matches on.

Write the as-built count and both passing runs' rows and times in the Log. The API shares the count.

## 7. The story's checks

The one-liner's count against what fundlens.org shows for 2024:

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/cycles?nocache=$(date +%s)" | jq '.[] | select(.cycle == 2024) | {cycle, contribution_count, total_amount}'
```

**Expected:** `contribution_count` equals the one-liner's `contributions`, and `total_amount` its `dollars`. Both
are counts of the live build's silver contributions for 2024, so they must agree. If they don't, stop: either the
snapshot is not of the live build (check `msum v1/latest/ | head -1` against `gold.meta`), or a publish happened
since the snapshot (a new build waits for the next snapshot).

`/dataset` lists the snapshot:

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/dataset?nocache=$(date +%s)" | jq '{base_url, latest, snapshots: [.snapshots[] | {snapshot_date, build_id, url, tables: (.tables | length)}]}'
```

**Expected:** `base_url` `https://data.fundlens.org/v1/`, `latest` `<D>`, and one snapshot (more if a Sunday
has run since step 3): `<D>`, `<B>`, `https://data.fundlens.org/v1/<D>/`, 11 tables. The API re-reads the list at
most once a minute.

Then open `https://fundlens.org/dataset` in a browser: the newest snapshot is `<D>` with its build and tables; click
the `race` file link for the newest cycle, and it downloads from `data.fundlens.org`. Write what the page shows in
the Log.

## 8. As built, and the README

A docs-only PR into `main`, `docs(runbooks): dataset launch as built (NEU-2067)`. Merge it on a weekday, not while
a snapshot or the Sunday run is going: the merge redeploys `pipeline`.

```bash
# laptop
cd ~/projects/fundlens && git switch main && git pull
git switch -c docs/NEU-2067-as-built
```

1. **This runbook:** the [As built](#as-built) table filled in, and a Log entry for steps 1–7.
2. **`cloudflare-setup.md`:** in its *As built* table, the *R2 buckets* row reads `fundlens-public` (public by
   custom domain `data.fundlens.org`, `r2.dev` disabled, CORS as dataset-launch.md §5.2) in place of "private until
   NEU-2067", and the *Rate-limit rule* row gives the count from step 6. A Log entry saying so. Its "Not in this
   runbook" line points to this runbook.
3. **`weekly.md`:** in *Facts*, the *Scheduled task* row's command is `opentelemetry-instrument fundlens run
   --scheduled --dataset`; the *How long a run takes* row adds the snapshot's wall time from step 2. Its "Not in
   this runbook" paragraph says the task runs with `--dataset` since `<step 3's date>`, and points here.
4. **Project spec §5.6:** the task runs `fundlens run --scheduled --dataset`.
5. **`docs/capacity.md` → *Dataset snapshot*:** a row per step 2 run: date, build, SHA, workers, objects (the two
   pass lines' counts), the two passes' seconds, `real`, notes.
6. **Repo `README.md`:** a *Dataset* section: what it is (every federal cycle since 1980, the silver tables, the
   resolved donors and the crosswalk, as Parquet, weekly); `https://data.fundlens.org/v1/README.md`; the README's
   one-liner, copied as it is; CC BY 4.0 with the attribution string `fundlens (fundlens.org), CC BY 4.0`; and one
   sentence on the notice: FEC's restriction on using contributor names and addresses for soliciting or commercial
   purposes (52 U.S.C. §30111(a)(4), 11 CFR 104.15) applies to the contributions whatever this license says.
   One static badge under the title, linking to the dataset README:

   ```markdown
   [![Dataset: CC BY 4.0](https://img.shields.io/badge/dataset-CC%20BY%204.0-blue)](https://data.fundlens.org/v1/README.md)
   ```

   No GitHub release or tag.

**Check:**

```bash
# laptop
git diff --stat
grep -n 'run --scheduled --dataset' docs/runbooks/weekly.md docs/specs/fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md
grep -n 'data.fundlens.org/v1/README.md' README.md
```

**Expected:** the six files changed; a match in each of the two files; a match for the badge and one for the
section's link.

```bash
# laptop
task format
git add docs/runbooks/dataset-launch.md docs/runbooks/cloudflare-setup.md docs/runbooks/weekly.md docs/capacity.md docs/specs/fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md README.md
git commit -m "docs(runbooks): dataset launch as built (NEU-2067)"
git push -u origin docs/NEU-2067-as-built
gh pr create --base main --title "docs(runbooks): dataset launch as built (NEU-2067)" --fill
```

**Expected:** the PR's `ci` check passes. Once it is merged, the repo's front page shows the badge, and the badge
opens the dataset README.

## 9. The first Sunday

After the first Sunday run with the flag, from about 05:00 UTC or on the Monday:

```bash
# VM
cdb -c "SELECT e.id, e.status, e.created_at, e.updated_at - e.created_at AS took FROM scheduled_task_executions e JOIN scheduled_tasks t ON t.id = e.scheduled_task_id WHERE t.name = 'fundlens weekly' ORDER BY e.created_at DESC LIMIT 3"
```

**Expected:** a row for the Sunday, `success`, created at 03:00 UTC, `took` under `06:00:00` (the task's 21600 s
timeout). Then its output:

```bash
# VM
S=<the Sunday, YYYY-MM-DD>
cdb -At -c "SELECT e.message FROM scheduled_task_executions e WHERE e.id = <id>" | tee "sunday-$S.log" | grep -E '^build |published build|^finished build|^docs:|snapshot|^latest/:|^removed snapshots:'
grep -E 'hashed and copied|objects to v1/latest/' "sunday-$S.log" | jq -r .message
pg -Atc "SELECT build_id FROM gold.meta"
msum "v1/$S/" | head -1
pub "print(p.get('v1/latest/manifest.json') == p.get('v1/$S/manifest.json'))"
dirs
```

**Expected:**

- `build <B> of 2026`, `published build <B> of 2026`, `finished build <B> of 2026: ran …`, then the snapshot's
  lines: `docs: …`, `took snapshot <S> of build <B>`, `latest/: copied`, `removed snapshots: none`.
- The two pass lines, each with its seconds.
- `gold.meta`'s build is `<B>`.
- `<S> <B> 1980 2026 24`: the Sunday's snapshot names the run's build.
- `True`: `latest/` is that snapshot.
- `v1/<D>/`, `v1/<S>/`, `v1/latest/`, `v1/schema/`.

Anything else is weekly.md's [A run missed](weekly.md#a-run-missed). A run that published its build and then
failed in the snapshot can be finished by hand: `docker exec "$(fl pipeline)" fundlens dataset --snapshot` on the
same UTC date.

Record it in a second small docs PR, `docs(runbooks): first Sunday with the dataset snapshot (NEU-2067)`: a Log
entry here (the run's total time from `took`, the two passes' seconds), and a row in `capacity.md` → *Dataset
snapshot*.

## As built

Filled in by step 8. IDs and names only: **no token value or secret goes in this file.**

| What | Value |
| --- | --- |
| Re-time | 2026-11-18, release `6bd0db0`, build `20261117T030329Z`: **16m26.675s** at 16 workers (snapshot pass 6,336 objects in 363 s, latest pass 6,340 in 495 s), against the 221m18s baseline. Passed first time |
| `DATASET_COPY_WORKERS` | 16, the compose default; not set in Coolify |
| Scheduled task command | `opentelemetry-instrument fundlens run --scheduled --dataset`, `0 3 * * 0`, timeout 21600, container `pipeline` (`coolify-db` `updated_at` 2026-11-18T18:57:17) |
| Trial snapshot deleted | `v1/2026-11-17/`, 6,340 objects, 2026-11-18, after `latest/` named 2026-11-18 and before the domain was connected |
| Custom domain | `data.fundlens.org` on `fundlens-public`, **Active**; DNS record `data`, type R2, created by Cloudflare. `fundlens-data` has none |
| `r2.dev` | Disabled on both buckets |
| CORS policy | As §5.2: any origin, `GET` and `HEAD`, `Range` allowed, `Content-Length`, `Content-Range`, `Accept-Ranges`, `ETag` exposed, max age 86400 |
| CORS without `Origin` | R2 sends `access-control-allow-origin: *` and the exposed headers on requests with no `Origin` too. Preflight `OPTIONS` returns `204` |
| `cf-cache-status` (manifest, Parquet) | `DYNAMIC` for both: nothing cached at the edge. No cache rule added |
| `manifest.json` type | Served with no `Content-Type`: the publisher puts the manifest untyped (the docs are typed). DuckDB and `fetch().json()` read it regardless |
| Rate-limit rule's count | **100** per 10 s, unchanged: the one-liner passed twice in a row with no 429 |
| One-liner (DuckDB version, rows, dollars, time) | DuckDB v2.0.0 (d54cbbe3df): 50,104,322 contributions, $9,973,281,141.00, in 1:48.98 then 1:27.42 |
| `/v1/cycles` 2024 | `contribution_count` 50,104,322, `total_amount` 9,973,281,141.0: equal to the one-liner |
| `/dataset` | `latest` 2026-11-18, one snapshot (2026-11-18, `20261117T030329Z`, 11 tables); a file downloaded from the page |
| First Sunday with the snapshot | Pending (2026-11-22), step 9 |

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-18 — Runbook written (NEU-2067)

Written with the implementation: the copies of both passes run `DATASET_COPY_WORKERS` (default 16) at a time, and
every partition is checked before the first copy. The README's one-liner is NEU-2065's, which builds its file list
from `manifest.json` because DuckDB cannot glob over `https://`.

**Pending:** steps 1–9.

### 2026-11-18 — Launched (NEU-2067)

Steps 1–7 walked from the laptop and `music-box-dancer`, release `6bd0db0` (PR #181) in production. Values in
[As built](#as-built).

- **Step 1.** Found an unfinished `v1/2026-11-18/` (82 `contribution/cycle=1980` keys, no manifest) beside
  `v1/2026-11-17/`, `v1/latest/` and `v1/schema/`. Both were most likely left by a snapshot started after NEU-2065
  deployed and stopped part way: it put the documentation, then copied 82 objects. Not traced further. Step 2's
  snapshot cleared and retook it, as it does any unfinished snapshot.
- **Step 2.** 16m26.675s at 16 workers, first try: `docs: unchanged`, `took snapshot 2026-11-18 of build
  20261117T030329Z`, `latest/: copied`, `removed snapshots: none`. Every table's rows and files equal to
  2026-11-17's. The two passes are 858 s of it; the rest is the docs check, `gold.donor`'s export, the crosswalk
  copy and retention.
- **Step 3.** `--dataset` on the task at 18:57 UTC. NEU-2063's two unattended Sundays are still being counted
  (accepted risk, spec §1.1): the first Sunday with the flag is 2026-11-22.
- **Step 4.** `v1/2026-11-17/` deleted, 6,340 objects; `v1/` holds `2026-11-18/`, `latest/` and `schema/`.
- **Step 5.** Gate passed (README, LICENSE, CHANGELOG, 11 schemas). `data.fundlens.org` connected and Active,
  CORS set, no cache rule. Unlike this runbook's guess, R2 sends the CORS headers without an `Origin` too.
  `manifest.json` is served with no `Content-Type`.
- **Step 6.** The one-liner read 2024's 256 contribution parts twice with no 429, so the rule stays at 100.
- **Step 7.** `/v1/cycles` 2024 and the one-liner agree exactly; `/dataset` lists the snapshot.

**Pending:** step 9, the first Sunday.
