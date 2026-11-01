# Runbook: first resolved production run (2024)

How to resolve donors on real data for the first time and put the donor routes live (NEU-2079; spec
§6.3–§6.6, §5.5, §7.1–§7.2, §10.5, §10.6). It runs on `music-box-dancer`, one step at a time, and
checks each one: `resolve --full` over the 2024 build NEU-2078 transformed, then `load` and `publish`.
Then it checks a well-known donor at `api.fundlens.org`, checks that no race total moved, and adds the
resolution figures to [`docs/capacity.md`](../capacity.md). Run it once, top to bottom. Append to the
[Log](#log) at the bottom; never rewrite it.

**Why by hand, one step at a time, and not one script.** Nobody has run `resolve --full` on real
contributor keys: 5,620,495 of them in 2024, against a fixture of a few dozen. How long it takes and how
much memory it needs are unknown, and this run measures both. `fundlens run` (NEU-2061) chains the steps later.

**Why no fresh `extract` and `transform`.** NEU-2078's build `20261031T202003Z` already has all seven
silver tables, `jfc_attribution` and `contributor` among them. No commit since `47e3dd5`, the SHA that
transformed it, touches `sql/silver`, `src/fundlens/transform`, `src/fundlens/fec`, `src/fundlens/resolve`
or `resolution/` (checked 2026-10-31; step 1 checks again). A fresh transform would cost about 30 minutes
and tell us nothing new.

**Not in this runbook:** adjudication (NEU-2055), DIME precision and recall (NEU-2054),
`gold.meta.resolver_version` and `model_version`, which nothing writes yet (NEU-2056), other cycles
(NEU-2060), incremental weekly resolution (NEU-2062), and the donor page in the frontend (NEU-2053).

## Before you start

- [first-run.md](first-run.md) (NEU-2046) is done: build `20261031T012553Z` is live, and both
  monitors, `fundlens/weekly` and `fundlens/publish`, are paused again after its step 8.
- The PRs for NEU-2051 (donor gold tables) and NEU-2052 (donor API) are merged and deployed. Step 1 checks this.
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this
  repo, and you can sign in to Kuma (`https://kuma.tail1afe5a.ts.net`) and Bugsink
  (`https://bugsink.neuroticsasquat.ch`).
- Allow an afternoon. `resolve --full` has no estimate: nothing has measured it on real data.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycle | `2024` |
| Transformed build | `20261031T202003Z` (NEU-2078, SHA `47e3dd5`; [`capacity.md`](../capacity.md)): 5,620,495 `contributor` rows |
| Live build before this run | `20261031T012553Z` (NEU-2046): no donor tables, so `GET /v1/donors/{id}` answers 500 |
| Step order | (`seats --report`, only if the build has no `race` partition) → `resolve --full` → `load` → `publish` |
| Donor to check | Elon Musk. FEC's 2023–2024 itemized rows give him more than a dozen spellings (checked 2026-10-31): `MUSK, ELON`, `MUSK, ELON MR.`, `MUSK, ELON R MR`, `MUSK, ELON REEVE`; employers `SPACE EXPLORATION TECHNOLOGIES CORP`, `… CORP.`, `SPACE EXPLORATION TECH`, `SPACEX`, `SPACE X`, `SPACE X - TESLA MOTORS`, `SELF-EMPLOYED`; cities `AUSTIN`, `LAKEWAY`, `DALLAS`, `HAWTHORNE`. Most of the dollars are in ZIP `78734`. The same search also finds `MUSKETT, ELONA` (FL) and `MUSKMOUTH, ELON` (MD), who are other contributors |
| Race to check | `https://api.fundlens.org/v1/races/2024/senate/MD`. NEU-2046's net `total_individual`: Alsobrooks (`S4MD00327`) $14,991,464, Hogan (`S4MD00483`) $4,659,760 ([first-run.md](first-run.md) Log) |

**`--build-id` on `resolve` is the model version, not the silver build.** `resolve --full` reads the
newest transformed build of every cycle it finds markers for, and writes each cycle's `resolved` marker
under that build (`resolve/runner.py`). `--build-id` only names the run: the trained model is saved as
`resolution/model/<it>.json`, and `app.crosswalk.build_id` records it. So the model version `M` is a new
timestamp, fixed in step 3, and step 1 checks that the build resolution will read is `20261031T202003Z`.
(The NEU-2079 ticket writes `resolve --full --build-id <B>`. That would also run, but it would save the
model under the silver build's name.)

**Why the money check comes before `publish`.** After `load`, Postgres holds both builds: `gold` is
NEU-2046's and `gold_build` is this one. Resolution only adds a `donor_id` to each contribution row,
and `resolve` stops if any row loses its key (`crosswalk.onto_silver`). So every race, candidate,
committee and cycle total must be identical in the two. Step 5 compares them before anything goes live.

**What the monitors hear.** `resolve` and `load` push nothing; only `publish` pushes `fundlens/publish`.
A step that crashes reports one Bugsink issue tagged `pipeline_mode=<step>`.

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-resolve
```

If SSH drops, reconnect and `tmux attach -t fundlens-resolve`. In the tmux session, define the helpers
and fix the build ID:

```bash
# VM, in tmux
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# One step's completion marker for this build, or MISSING.
mk() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; m = markers.read(sys.argv[1], R2.from_settings(get_settings()), cycle=2024, build_id=sys.argv[2]); print(m.model_dump_json(indent=2) if m else "MISSING")' "$1" "$B"; }
# The R2 objects under a prefix with their sizes in bytes, then the count and total GB.
r2ls() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens.r2 import R2; from fundlens.settings import get_settings; s = R2.from_settings(get_settings()); objs = [o for p in s.client.get_paginator("list_objects_v2").paginate(Bucket=s.bucket, Prefix=sys.argv[1]) for o in p.get("Contents", [])]; [print(o["Key"], o["Size"]) for o in objs]; print(len(objs), "objects,", round(sum(o["Size"] for o in objs) / 1e9, 2), "GB")' "$1"; }
# psql in the fundlens database.
pg() { docker exec "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
# A query from stdin against resolution's working file, read-only; `$surname` in it is the first argument.
rq() { docker exec -i "$(fl pipeline)" python -c 'import sys, duckdb; duckdb.connect("/data/fundlens/resolution/resolve.duckdb", read_only=True).sql(sys.stdin.read(), params={"surname": sys.argv[1]}).show(max_width=250, max_rows=200)' "$1"; }
export B=20261031T202003Z
mkdir -p ~/fundlens-resolved-run && cd ~/fundlens-resolved-run
```

**Expected:** no output. If the tmux session is ever lost, define the helpers again,
`cd ~/fundlens-resolved-run`, `export B=20261031T202003Z`, and from step 3 on also
`export M=$(cat model-version.txt)`.

## 1. Preflight

### 1.1 The deployed code

```bash
# VM
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES
git ls-remote https://github.com/neuroticsasquat-ch/fundlens main
docker exec "$(fl pipeline)" alembic upgrade head
docker exec "$(fl pipeline)" fundlens health; echo "exit=$?"
```

**Expected:** the `service.version=<sha>` in `OTEL_RESOURCE_ATTRIBUTES` is the SHA `ls-remote` prints.
If not: Coolify → the `fundlens` resource → *Deploy*, wait for it to finish, and run this step again.
Alembic reaches head with no error; then `postgres: ok`, `r2: ok`, `exit=0`.

Then check that nothing since the build's transform changes what resolution reads. `SHA` is read from
the VM, the same `service.version` as above:

```bash
# laptop
cd ~/projects/fundlens
git fetch origin
SHA=$(ssh hetzner-01 'docker exec "$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)" printenv OTEL_RESOURCE_ATTRIBUTES' | sed 's/.*service.version=//; s/,.*//')
echo "$SHA"
git merge-base --is-ancestor 7629c3e "$SHA" && echo "donor API deployed"
git log --oneline 47e3dd5.."$SHA" -- sql/silver src/fundlens/transform src/fundlens/fec src/fundlens/resolve resolution
```

**Expected:** the SHA from the VM, then `donor API deployed` (NEU-2052's merge, `7629c3e`, is in the deployed code), then no commits
listed. A commit listed means build `$B`'s silver predates a change to how silver is built or resolved.
Stop: transform a fresh build with [first-run.md](first-run.md) steps 0–4 and resolve that one instead.

### 1.2 The build resolution will read

```bash
# VM
docker exec "$(fl pipeline)" python -c 'from fundlens.r2 import R2; from fundlens.settings import get_settings; from fundlens.resolve.runner import transformed_builds; print(transformed_builds(R2.from_settings(get_settings())))'
r2ls silver/ | grep "/cycle=2024/build=$B/" | cut -d/ -f2 | sort | uniq -c
r2ls "silver/contribution/cycle=2024/build=$B/" | grep -c 'bucket='
docker exec "$(fl pipeline)" sh -c "du -sh /data/fundlens/silver/*/cycle=2024/build=$B"
mk transformed | tee transformed.json
```

**Expected:**

- `{2024: '20261031T202003Z'}`. Resolution reads every cycle listed and rewrites its silver. If another
  cycle is listed, or 2024 names another build, stop and find out who transformed it.
- A count per table for `candidate`, `candidate_committee_link`, `committee`, `committee_transfer`,
  `contribution`, `contributor`, `jfc_attribution`, and maybe `race`. Note whether `race` is listed:
  step 2 depends on it.
- `0`: the contribution partition has no `bucket=` directories yet.
- A local size per table: the build is cached on the volume. A table missing locally is not an error:
  `resolve` and `load` download it from R2.
- A `transformed` marker whose `row_counts` has `contributor: 5620495`. Write down its `contribution`
  count: step 3 checks the `resolved` marker against it.

### 1.3 Resolution has never run here

```bash
# VM
pg -Atc "select (select count(*) from app.crosswalk), (select count(*) from app.donor_redirect), (select last_value from app.donor_id_seq), (select is_called from app.donor_id_seq)"
pg -Atc "select build_id from gold.meta"
pg -Atc "select coalesce(to_regclass('gold.donor')::text, 'no gold.donor')"
docker exec "$(fl pipeline)" python -c 'from fundlens.settings import get_settings; p = get_settings().overrides_path; print(p, p.exists())'
docker exec "$(fl pipeline)" sh -c 'grep -v "^#" /app/resolution/overrides.yaml'
docker exec "$(fl pipeline)" sh -c 'ls -la /data/fundlens/resolution 2>&1'
```

**Expected:**

- `0|0|1|f`: an empty crosswalk, no redirects, and a `donor_id_seq` never drawn from, so the first donor
  gets id 1. If the crosswalk has rows, something already resolved on prod. Stop and find out what
  before going on: this run would keep those ids, which is right, but the Log must say so.
- `20261031T012553Z`, then `no gold.donor`.
- `/app/resolution/overrides.yaml True`, then `[]`: the overrides file is in the image and empty.
- An empty directory (`resolution` is a named volume, so it always exists): no earlier working file.

### 1.4 Disk and memory before

```bash
# VM
df -h / | tee disk-before.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null' | tee -a disk-before.txt
pg -Atc "select pg_size_pretty(pg_database_size('fundlens'))" | tee -a disk-before.txt
docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' | grep -E '^(pipeline|api|fundlens-postgres)-lvch8zyndujjzkz16ksys8im' | tee stats-before.txt
```

**Expected:** at least 100 GB available on `/`. `resolve` can spill up to 60 GB of DuckDB scratch
(`DUCKDB_MAX_TEMP_DIRECTORY_SIZE`), and its working file and the rewritten contribution partition add a
few GB. With less free space, stop and free some first. `stats-before.txt` shows `pipeline` idle, at a few
hundred MiB.

Open a second tmux window (`Ctrl-b c`) and leave a memory sampler running there for the rest of the run.
It writes `pipeline`'s and Postgres's memory to `mem.txt` every 10 s; step 10 reads the peaks from it.

```bash
# VM, tmux window 1 (a new shell: the helpers are not defined here)
cd ~/fundlens-resolved-run
while true; do docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' | grep -E '^(pipeline|fundlens-postgres)-lvch8zyndujjzkz16ksys8im' | sed "s/^/$(date -u +%H:%M:%S) /"; sleep 10; done | tee mem.txt
```

**Expected:** two lines every 10 s, e.g. `14:00:00 pipeline-lvch8zyndujjzkz16ksys8im-… 0.5% 410MiB / 40GiB`.
Switch back with `Ctrl-b 0`. The container limit is 40 GB and DuckDB is held to 28 GB.

## 2. Seats, only if the build has no `race` partition

`load` reads the `race` partition of the same build. Skip this step if step 1.2 listed `race`.

```bash
# VM
S=$SECONDS; docker exec "$(fl pipeline)" fundlens seats --cycle 2024 --report --build-id "$B" 2>&1 | tee seats.log; echo "seats $((SECONDS - S)) s" | tee seats-time.txt
r2ls "silver/race/cycle=2024/build=$B/"
```

**Expected:** `house: 441 races (0 special)`, `senate: 35 races (2 special)`, `president: 1 races
(0 special)`, `wrote silver/race/cycle=2024/build=20261031T202003Z/…`, and about 51 unmatched filings
recorded, as in NEU-2046. R2 lists the partition. Under a minute.

## 3. Resolve

Fix the model version, mark the start, and run it:

```bash
# VM, tmux window 0
export M=$(date -u +%Y%m%dT%H%M%SZ)
echo "$M" | tee model-version.txt
date -u +%H:%M:%S | tee resolve-start.txt
time docker exec "$(fl pipeline)" fundlens resolve --full --build-id "$M" 2>&1 | tee resolve.log
date -u +%H:%M:%S | tee resolve-end.txt
```

While it runs, a JSON log line `resolve <phase>: <seconds> s` marks the end of each phase, in this order:
`load` (download and merge the contributor partitions, check the overrides), `train` (Splink estimates u
and m), `cluster` (predict pairs, connected components), `overrides`, `save` (the model JSON), `crosswalk`
(donor_ids into Postgres, one transaction), `silver` (each table rewritten with `donor_id`, uploaded to
R2). `train` and `cluster` can go a long time with no log line. In window 1, `pipeline` with high CPU is
working. A `pipeline` idle for 10 minutes or more, with no new log line, is stuck. **No estimate:** this
run is the measurement.

**Expected,** after the log lines (`<C>` is the cluster count):

```
2024: build 20261031T202003Z
5620495 contributor keys in <C> clusters
overrides: 0 merges joining 0 clusters into others, 0 splits
crosswalk: <C> new donors, 0 keys re-pointed, 0 redirects
model <M>: trained, wrote resolution/model/<M>.json
load <s> s, train <s> s, cluster <s> s, overrides <s> s, save <s> s, crosswalk <s> s, silver <s> s
DuckDB memory limit: <about 26 GiB>
```

- `<C>` is below 5,620,495: some keys were joined. On an empty crosswalk every cluster is a new donor,
  so the two `<C>` are the same number.
- `trained`, not `priors (too few keys to train on)`: 5.6M keys is far above `RESOLVE_MIN_TRAINING_KEYS`.
- The memory limit is the 28 GB `DUCKDB_MEMORY_LIMIT`, printed in GiB.

**If it fails.**

- **Killed for memory** (`pipeline` reaches about 40 GiB in window 1, then the command ends with exit 137
  and no traceback), or **a traceback**: write down the last phase logged and the peak, and check
  Bugsink for an issue `pipeline_mode=resolve`. File a ticket and stop. Don't tune limits on the fly:
  memory use is what this run is measuring.
- **What a failed run leaves.** Before `crosswalk`: nothing but the working file and the model JSON,
  so run the same command again. During `crosswalk`: its transaction rolls back, so run it again.
  During `silver`: R2 may hold a half-rewritten contribution partition marked `_rewriting`. Run the same
  command again: it reads the local copy, rewrites, and clears the marker. It then prints
  `crosswalk: 0 new donors, 0 keys re-pointed, 0 redirects`, because the ids were already written.

Then check what it wrote:

```bash
# VM
mk resolved | tee resolved.json
docker exec "$(fl pipeline)" sh -c "ls -d /data/fundlens/silver/contribution/cycle=2024/build=$B/bucket=* | wc -l"
r2ls "silver/contribution/cycle=2024/build=$B/" | grep -o 'bucket=[0-9a-f]*' | sort -u | wc -l
r2ls "silver/contribution/cycle=2024/build=$B/" | grep -c '_rewriting'
r2ls "resolution/model/$M.json"
pg -Atc "select count(*), count(distinct donor_id), min(donor_id), max(donor_id), min(build_id), max(build_id) from app.crosswalk"
pg -Atc "select count(*) from app.donor_redirect"
docker exec "$(fl pipeline)" sh -c 'ls -la /data/fundlens/resolution'
```

**Expected:**

- A `resolved` marker with `build_id` `20261031T202003Z`, its `row_counts` `cluster: 5620495` and the
  same `contribution` count as `transformed.json`, and a `duration_s`.
- `256` and `256`: the contribution partition is in one `bucket=` directory per `donor_id % 256`, both
  in the volume (where the API reads it) and in R2.
- `0`: no `_rewriting` marker left.
- The model, one object, a few KB.
- `5620495|<C>|1|<C>|<M>|<M>`: every key has a donor_id, the ids run 1 to `<C>`, and every row is from this run.
- `0` redirects.
- `resolve.duckdb`, its size in bytes. Step 9 records it.

### 3.1 Look at the donor

Before loading anything, check that resolution put the check donor's spellings together. Use the working
file's `contributor` and `crosswalk` tables, as
[adding-an-override.md](adding-an-override.md) step 1 does:

```bash
# VM
rq MUSK <<'SQL'
SELECT x.donor_id, k.contributor_key, k.city, k.state, k.contribution_count, k.amount_total
FROM contributor AS k
JOIN crosswalk AS x USING (contributor_key)
WHERE k.last_name = $surname AND k.first_name = 'ELON'
ORDER BY x.donor_id, k.amount_total DESC
SQL
export D=$(docker exec -i "$(fl pipeline)" python - <<'PY'
import duckdb

con = duckdb.connect("/data/fundlens/resolution/resolve.duckdb", read_only=True)
row = con.execute(
    "SELECT x.donor_id FROM contributor AS k JOIN crosswalk AS x USING (contributor_key)"
    " WHERE k.last_name = 'MUSK' AND k.first_name = 'ELON'"
    " GROUP BY 1 ORDER BY sum(k.amount_total) DESC LIMIT 1"
).fetchone()
print(row[0] if row else "none")
PY
)
echo "$D" | tee donor-id.txt
```

**Expected:** a dozen or so keys (a key is the normalized name, ZIP5, employer and occupation joined by
`|`). Most of them, and nearly all the dollars, are under one `donor_id`: the 78734 keys with `SPACE
EXPLORATION TECHNOLOGIES`, `SPACEX` and the self-employed investor rows. `donor-id.txt` holds that id,
`D`. **Not measured:** whether linkage joins every spelling is what this step finds out.

- Most dollars under `D`, and more than one key under it: go on. Write in the Log how many keys are
  under `D` and which keys sit under other ids. For example, the 90245 `SPACE X` key or the Dallas row
  may be left apart. A key left apart is a finding for an override ([adding-an-override.md](adding-an-override.md))
  or for tuning (NEU-2054). Neither is part of this run.
- Only one key under `D`, or `none`: linkage joined none of his spellings. Stop, file a ticket with
  this output, and don't load: the donor routes would go live with a resolution that does not resolve.

## 4. Load

```bash
# VM
time docker exec "$(fl pipeline)" fundlens load --cycle 2024 --build-id "$B" 2>&1 | tee load.log
mk loaded
pg -c "select build_id, published_at, cycles from gold_build.meta"
pg -c "select c.relname, c.reltuples::bigint as rows, pg_size_pretty(pg_total_relation_size(c.oid)) as size from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'gold_build' and c.relkind = 'r' order by pg_total_relation_size(c.oid) desc"
pg -c "select (select count(*) from gold_build.donor) as donors, (select count(*) from gold_build.search_entity where kind = 'donor') as donor_search_rows, (select count(*) from gold_build.donor_redirect) as redirects, (select count(*) from gold_build.race_top_donor) as race_top_donors, (select count(*) from gold_build.candidate_top_donor) as candidate_top_donors, (select count(*) from gold_build.committee_top_donor) as committee_top_donors, (select count(*) from gold_build.candidate_cycle where contributor_count is null) as null_contributor_counts"
```

**Expected:** a `<table>: <n> rows` line per gold table, then `loaded build 20261031T202003Z into
gold_build (aggregates <a> s, copy <c> s)`. That line means every `sql/checks/gold_*.sql` passed: a
failed check stops the load, leaves no `gold_build`, and names the check. File a ticket with its rows and
stop. Then:

- a `loaded` marker;
- `gold_build.meta` for build `20261031T202003Z`, with no `published_at`;
- the table list, now with `donor`, `donor_cycle`, `donor_top_recipient`, `race_top_donor`,
  `candidate_top_donor` and `committee_top_donor` among the largest;
- `donors` `<C>`: every cluster holds at least one 2024 key, so every one is a donor. `donor_search_rows`
  `<C>` or a few fewer: a donor with no display name gets no search row (`16_search_entity.sql`). `redirects` `0`; the three top-donor counts above 0; `null_contributor_counts` `0`.

NEU-2046's load took 4 s without donors. Donor tables over 5.6M keys take longer, and this run measures it.

## 5. Check that no money moved

Both builds are in Postgres now. Compare every total:

```bash
# VM
pg -c "
select 'race' as tbl, count(*) as differing from gold.race o full join gold_build.race n using (race_id) where row(o.*) is distinct from row(n.*)
union all select 'race_candidate', count(*) from gold.race_candidate o full join gold_build.race_candidate n using (race_id, candidate_id) where row(o.*) is distinct from row(n.*)
union all select 'committee_cycle', count(*) from gold.committee_cycle o full join gold_build.committee_cycle n using (committee_id, cycle) where row(o.*) is distinct from row(n.*)
union all select 'cycle', count(*) from gold.cycle o full join gold_build.cycle n using (cycle) where row(o.*) is distinct from row(n.*)"
pg -c "select race_id, candidate_id, name, total_individual from gold_build.race_candidate where race_id = (select race_id from gold_build.race where slug = '2024/senate/MD') order by total_individual desc limit 2"
```

**Expected:** `0` on all four rows. Then Alsobrooks at 14991464.xx and Hogan at 4659760.xx, NEU-2046's
figures to the dollar.

A difference means this build's money is not NEU-2046's. Resolution cannot cause that, so the cause is
in the silver built since `d67cec2`. Stop here, before `publish`. List the rows that differ:

```bash
# VM
pg -c "select race_id, candidate_id, o.total_individual as live_individual, n.total_individual as new_individual, o.total_committee as live_committee, n.total_committee as new_committee from gold.race_candidate o full join gold_build.race_candidate n using (race_id, candidate_id) where row(o.*) is distinct from row(n.*) order by abs(coalesce(n.total_individual, 0) - coalesce(o.total_individual, 0)) desc limit 20"
```

File a ticket with that output and link it from NEU-2079. `gold` stays NEU-2046's build. `gold_build`
does no harm where it is: the next `load` replaces it.

## 6. Resume the `fundlens/publish` monitor

Kuma refuses a push to a paused monitor. Kuma → `fundlens/publish` → *Resume*. Leave `fundlens/weekly`
paused.

**Check:** `fundlens/publish` is no longer *Paused* in Kuma's list. It may read *Pending*.

## 7. Publish

```bash
# VM
time docker exec "$(fl pipeline)" fundlens publish --cycle 2024 2>&1 | tee publish.log
mk published
pg -c "select build_id, published_at from gold.meta"
pg -Atc "select build_id from gold_prev.meta"
pg -Atc "select coalesce(to_regclass('gold.donor')::text, 'no gold.donor'), (select count(*) from gold.donor)"
```

**Expected:** `published build 20261031T202003Z of 2024`, `previous build: 20261031T012553Z`,
`cloudflare purge: done`, `wrote resolution/build=20261031T202003Z/crosswalk.parquet` and `pruned 0
silver builds (0 objects)`. Prune deletes only builds older than the previous live one, and NEU-2046's
publish already pruned those. NEU-2047's `20261031T164731Z` stays until the next publish. Then:

- a `published` marker;
- `gold.meta` naming `20261031T202003Z` with `published_at` set;
- `gold_prev` holding `20261031T012553Z`. This is the first `gold_prev` with a build in it, so
  `publish --rollback` now has somewhere to go back to;
- `gold.donor|<C>`.

About 75 s to 3 min: the purge waits 75 s after the swap on purpose (spec §5.5).
`cloudflare purge: skipped (not configured)`: purge by hand as in [first-run.md](first-run.md) step 7.

## 8. Signals

- **Kuma:** `fundlens/publish` is **up**, its latest message `publish: ok`.
- **Bugsink** → `fundlens`: no new issue since step 2. An issue there is from a step that crashed and was
  run again: note it in the Log, then resolve it.
- **Discord `#alerts`:** nothing from fundlens but Kuma's `fundlens/publish` going up.

Then Kuma → `fundlens/publish` → *Pause* again. Nothing publishes until NEU-2063's schedule.

## 9. Verify

All on the laptop. Fetch the donor id from the VM first:

```bash
# laptop
export D=$(ssh hetzner-01 cat fundlens-resolved-run/donor-id.txt)
echo "$D"
```

### 9.1 The API serves the build

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq '{build_id, published_at, resolver_version, model_version, cycles}'
```

**Expected:** `build_id` and `cycles."2024".build_id` both `20261031T202003Z`. `resolver_version` and
`model_version` are `null`: nothing writes them yet (NEU-2056). That is not a deviation.

### 9.2 Search finds the donor

```bash
# laptop
curl -sS 'https://api.fundlens.org/v1/search?q=musk%20elon&kind=donor' | jq -r '.[] | [.id, .name, .score, .aliases] | @tsv' | head -5
```

**Expected:** the first row's id is `$D` and its name a `MUSK, ELON` spelling. Its aliases list his
other spellings, most money first.

### 9.3 The donor page, and its cache

The cache check comes first, so that nothing earlier has already filled the cache for this URL (the
deviation first-run.md step 9.1 recorded):

```bash
# laptop
for i in 1 2; do curl -sS -D - -o /dev/null "https://api.fundlens.org/v1/donors/$D" | grep -iE '^HTTP|^etag|^cf-cache-status'; done
curl -sS -o /dev/null -w '%{http_code}\n' "https://api.fundlens.org/v1/donors/$D"
curl -sS "https://api.fundlens.org/v1/donors/$D" | jq '{donor_id, display_name, employer, occupation, city, state, zip5, total_all_cycles, contributor_key_count, cycles, top_recipients: .top_recipients[:5]}'
```

**Expected:**

- `HTTP/2 200` twice, each with an `etag` carrying `20261031T202003Z`, the first `cf-cache-status:
  MISS` and the second **`HIT`**.
- `200`.
- `display_name` a `MUSK, ELON` spelling, `state` `TX`, `contributor_key_count` above 1 (at least the number
  of keys step 3.1 found under `D`: it also counts the cluster's keys under other name spellings), one row in `cycles` for 2024, and `top_recipients` led by the committees
  that took his largest gifts. Write `contributor_key_count` and `total_all_cycles` in the Log.

### 9.4 The donor's contributions

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/donors/$D/contributions?cycle=2024" | jq -r '.contributions[] | [.date, .amount, .contributor_name, .contributor_employer, .contributor_city, .contributor_state, .contributor_zip, .recipient_committee_id] | @tsv' | head -20
curl -sS "https://api.fundlens.org/v1/donors/$D/contributions?cycle=2024" | jq -r '[.contributions[] | [.contributor_name, .contributor_employer, .contributor_city] | @tsv] | unique[]'
```

**Expected:** the first 20 of the page's rows (a page holds up to 100), newest first. The second
command lists the spellings on the whole page. More than one name or employer spelling, all in Texas or in California ZIPs
starting `902`, and no `MUSKETT` or `MUSKMOUTH`: the same donor under several spellings.
A row that is plainly someone else is a wrong merge. Write it in the Log and file it for an override.

### 9.5 Race totals did not move

```bash
# laptop
curl -sS https://api.fundlens.org/v1/races/2024/senate/MD | jq -r '.candidates | sort_by(-.total_individual) | .[:2][] | [.candidate_id, .name, .total_individual] | @tsv'
```

**Expected:** `S4MD00327` Alsobrooks at 14991464.xx and `S4MD00483` Hogan at 4659760.xx, the figures in
[first-run.md](first-run.md)'s Log and in step 5. Step 5 already compared every race. This check
confirms the API serves the same figures through the edge.

### 9.6 The race page still renders

Open `https://fundlens.org/race/2024/senate/MD` in a browser.

**Expected:** as in first-run.md step 9.2: the heading, both candidates with totals, the chart, the top
committees. The page shows no donors yet (NEU-2053, NEU-2080).

**If a check fails after publish.** Roll back to NEU-2046's build, and the donor routes answer 500
again:

```bash
# VM
docker exec "$(fl pipeline)" fundlens publish --rollback
```

**Expected:** `rolled back: build 20261031T012553Z is live`, then `build 20261031T202003Z is now gold_prev`.
The crosswalk keeps its donor_ids, and the next `resolve --full` reuses them. File a ticket with the
failed check's output.

## 10. Disk after, and the capacity record

```bash
# VM
df -h / | tee disk-after.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null' | tee -a disk-after.txt
pg -Atc "select pg_size_pretty(pg_database_size('fundlens'))" | tee -a disk-after.txt
pg -Atc "select round(sum(pg_total_relation_size(c.oid)) / 1e9, 2) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'gold' and c.relkind = 'r'" | sed 's/^/gold GB /' | tee -a disk-after.txt
docker exec "$(fl pipeline)" sh -c "du -cb /data/fundlens/silver/*/cycle=2024/build=$B | tail -1" | awk '{printf "silver GB %.2f\n", $1/1e9}' | tee -a disk-after.txt
docker exec "$(fl pipeline)" sh -c 'du -b /data/fundlens/resolution/resolve.duckdb' | awk '{printf "working file GB %.2f\n", $1/1e9}' | tee -a disk-after.txt
for s in resolved loaded published; do mk "$s" | grep -E '"step"|"duration_s"'; done | tee durations.txt
```

Stop the memory sampler (tmux window 1, `Ctrl-c`), then gather every figure the capacity record needs in
one file. If the run crossed midnight UTC, the resolve peak line below compares clock times wrongly. In
that case, read the peak from `mem.txt` by eye between the two times.

```bash
# VM, tmux window 0
{
  echo "build $B"
  echo "model $M"
  docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES | sed 's/.*service.version=/sha /'
  grep -E '^[0-9]+ contributor keys in|^crosswalk:|^model |^load [0-9.]* s, train|^DuckDB memory limit' resolve.log
  grep -E '"step"|"duration_s"' durations.txt | paste - - | tr -d ' ,"'
  [ -f seats-time.txt ] && cat seats-time.txt
  grep -o 'aggregates [0-9.]* s, copy [0-9.]* s' load.log
  grep -E '^(gold GB|silver GB|working file GB)' disk-after.txt
  echo "resolve $(cat resolve-start.txt)-$(cat resolve-end.txt) UTC"
  echo "peak pipeline memory in resolve $(awk -v s="$(cat resolve-start.txt)" -v e="$(cat resolve-end.txt)" '$1 >= s && $1 <= e && $2 ~ /^pipeline-/ {print $4}' mem.txt | sort -h | tail -1)"
  echo "peak pipeline memory overall $(awk '$2 ~ /^pipeline-/ {print $4}' mem.txt | sort -h | tail -1)"
} | tee capacity-2024-resolved.txt
```

**Expected:** the build, the model version, the SHA, resolve's summary lines with every phase's seconds, three `step:<name>` lines, each with its `duration_s:<seconds>`, load's two halves, the gold, silver and
working-file GB, the resolve window, and two peaks.

Copy the file to the laptop:

```bash
# laptop
scp hetzner-01:fundlens-resolved-run/capacity-2024-resolved.txt .
cat capacity-2024-resolved.txt
```

Then, in one PR, `docs(runbooks): record the first resolved run (NEU-2079)`:

- in [`docs/capacity.md`](../capacity.md), a row in **Resolution** from the resolve lines, and a 2024 row
  in **Per cycle**: `Load s` and `Publish s` from their markers, `Silver GB` and `Gold GB`, peak memory
  overall, `—` for the steps not run, and `Seats s` if step 2 ran. Its note says it is the first
  resolved build;
- any finding in **Findings**: at least whether memory or time is now the limit;
- the Log entry from step 11.

## 11. Record the run

Append a Log entry with: the date, the build, the model version, the deployed SHA, resolve's output
(keys, clusters, every phase's seconds, the peak memory), load's and publish's times, step 3.1's keys
for the check donor and which sat apart, step 9's donor id, `contributor_key_count` and
`total_all_cycles`, the step 5 comparison, and every deviation. File each deviation from the spec as a
ticket and link it from NEU-2079.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-01 — First resolved run (NEU-2079)

Build `20261031T202003Z`, model `20261101T024736Z`, published at 03:15:31 UTC from `a4c82b8`. Every check passed, and
nothing was rolled back. The figures are in [`docs/capacity.md`](../capacity.md):

- seats 6 s (step 2 ran: NEU-2078's transform-only build had no `race` partition), with 441 + 35 + 1 races and 51
  unmatched filings, as in NEU-2046;
- resolve 762 s: 5,620,495 contributor keys in 3,816,141 clusters, trained, with no overrides. Phases: load 10.08 s,
  train 190.33 s, cluster 111.11 s, overrides 0.00 s, save 0.12 s, crosswalk 101.13 s, silver 346.49 s. Peak `pipeline`
  memory 24.54 GiB at 02:55:01, in `silver`. Working file 9.91 GB. 256 buckets in the volume and in R2;
- load 169 s (aggregates 73.08 s, `COPY` 93.51 s): 3,816,141 donors, 3,816,003 donor search rows (138 donors have no
  display name), gold 2.61 GB;
- publish 91 s. NEU-2046's `20261031T012553Z` is now `gold_prev`; 0 silver builds pruned;
- free space on `/` went from 231 GB to 215 GB.

Step 5: `race`, `race_candidate`, `committee_cycle` and `cycle` were identical in the two builds. Alsobrooks
$14,991,464 and Hogan $4,659,760, NEU-2046's figures, and the API served the same in step 9.5.

Steps 3.1 and 9: Elon Musk is donor `2441073`, with 10 of his 11 contributor keys. That is $212,230,236 net over 24
counted contributions, in eight name and employer spellings, all in Austin or Lakeway, TX. Five of the ten keys are known
only from 15J lines and carry $0. His top recipient is America PAC (`C00879510`), $197,662,036. Search finds him first.
`/v1/donors/2441073` gave `MISS` then `HIT` with the build in its `etag`, and `contributor_key_count` 10. His
`/contributions` page lists the 24 rows, which sum to his total.

Findings, none of them a deviation from the spec:

- **One Musk key sat apart.** `MUSK, ELON|90250|SPACE X TESLA MOTORS|CEO CHIEF TECHNOLOGY OFFICER` (Hawthorne, CA,
  $825,000) is donor `2441074`, so search shows two `MUSK, ELON` donors. Its ZIP, state and employer all differ, so
  linkage kept it apart; joining it is an override's job ([adding-an-override.md](adding-an-override.md)), filed as
  NEU-2121.
- **FEC lists more Musk money to America PAC than fundlens counts, all of it memo lines.** FEC's API lists 26 rows from
  him to `C00879510`. fundlens counts the 16 that are not memos, $197,662,036, matching row for row. The other 10 are
  in-kind "ATTRIBUTION" memo lines, $52,092,950, which silver leaves out by its memo rule.
- **Cents are gone before fundlens reads the bulk file.** His in-kind travel row is $112,036.50 in FEC's API and
  $112,036 in fundlens. Silver reads `TRANSACTION_AMT` as `DECIMAL(14,2)` (`fec/files.py`), so the bulk file carried
  whole dollars. That fits NEU-2046's race totals, which also came out to whole dollars.
- **The ticket's `resolve --full --build-id <B>`** is run as `--build-id <model version>`, for the reason in
  [Facts](#facts).
