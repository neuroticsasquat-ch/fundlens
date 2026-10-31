# Runbook: first production run (2024)

How to run the pipeline for the first time on real data (NEU-2046; spec §5.1, §5.5, §10.5, §10.6). It runs
the 2024 cycle on `music-box-dancer`, one step at a time, and checks each step: `extract`, `seats`,
`transform`, `load`, `publish`. Then it checks the result at `fundlens.org` against FEC.gov, and starts
the capacity record in [`docs/capacity.md`](../capacity.md). Run it once, top to bottom. Append to the
[Log](#log) at the bottom; never rewrite it.

**Why by hand, one step at a time, and not one script.** The point is to see each step work the first time
on real data. `fundlens run` (NEU-2061) chains them later.

**Not in this runbook:** other cycles (NEU-2060), the schedule and the `fundlens/weekly` monitor
(NEU-2063), resolution and donors (M3).

## Before you start

- [coolify-setup.md](coolify-setup.md) (NEU-2032) and both parts of
  [cloudflare-setup.md](cloudflare-setup.md) (NEU-2033) are done. Both monitors, `fundlens/weekly` and
  `fundlens/publish`, are still paused from coolify-setup step 12.
- The laptop is on the tailnet, `ssh hetzner-01` works, and you can sign in to Kuma
  (`https://kuma.tail1afe5a.ts.net`) and Bugsink (`https://bugsink.neuroticsasquat.ch`).
- Allow half a day. `extract`, `transform` and `load` each take minutes to an hour on a real cycle.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycle | `2024` |
| Step order | `extract` → `seats --report` → `transform` → `load` → `publish` |
| Race to check | `https://fundlens.org/race/2024/senate/MD` (API: `https://api.fundlens.org/v1/races/2024/senate/MD`) |
| Earmark to check | `KELLER, CAREN`, $250.00 on 2024-12-31 to `C00840017` (Alsobrooks for Senate) through ActBlue `C00401224`. FEC lists it twice: the recipient's `15E` and ActBlue's `24T` (checked 2026-10-30) |
| Reconciliation tolerance | ±2 %, for each of the race's two largest candidates: net `total_individual` against FEC's itemized contributions minus its refunds, and gross receipts against FEC's itemized contributions (step 9.3) |

**Why `seats` comes before `transform`.** `transform` reads `app.unmatched_filing`, which `seats --report`
writes, and `load` reads the `race` silver partition, which `seats` writes for one build. (The NEU-2046
ticket lists `seats` after `transform`; the code needs it before.)

**Why one `--build-id` on every step.** Each step otherwise starts a new build named for the moment it
runs, and `load` needs the `transform` and `seats` partitions under the same build. So the build ID is
fixed once, in step 0, and passed to every step but `publish`, which takes the loaded build.

**What the monitors hear.** Only `publish` pushes a Kuma monitor (`fundlens/publish`). `extract`, `seats`,
`transform` and `load` push nothing, so a hand-run step never marks the weekly run healthy (`cli.py`).
A step that crashes reports one Bugsink issue tagged `pipeline_mode=<step>`; a step that succeeds reports
nothing.

**The expected durations below are estimates, not measurements** (asserted from the spec's sizing,
§3.4); this run replaces them. When a step runs well past its range, look at `docker stats` (step 1): a
working step keeps `pipeline` busy, a stuck one leaves it idle with no new log lines.

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
command -v tmux || sudo apt-get install -y tmux
tmux new -s fundlens
```

If SSH drops, reconnect and `tmux attach -t fundlens`. In the tmux session, define the helpers and fix the
build ID:

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
export B=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p ~/fundlens-first-run && cd ~/fundlens-first-run
echo "$B" | tee build-id.txt
```

**Expected:** a build ID like `20261031T140000Z`. Write it in the Log now. If the tmux session is ever
lost, define the helpers again, `cd ~/fundlens-first-run`, and run `export B=$(cat build-id.txt)`.

## 1. Preflight

```bash
# VM
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES
git ls-remote https://github.com/neuroticsasquat-ch/fundlens main
docker exec "$(fl pipeline)" alembic upgrade head
docker exec "$(fl pipeline)" fundlens health; echo "exit=$?"
pg -Atc "select nspname from pg_namespace where nspname like 'gold%' order by 1"
```

**Expected:**

- The `service.version=<sha>` in `OTEL_RESOURCE_ATTRIBUTES` is the SHA `ls-remote` prints. If not:
  Coolify → the `fundlens` resource → *Deploy*, wait for it to finish, and run this step again.
- Alembic reaches head with no error; then `postgres: ok`, `r2: ok`, `exit=0`.
- No `gold*` schema is listed. If one is, note it in the Log: `publish` keeps an existing `gold` as
  `gold_prev`, and step 7's `previous build` line will name it.

Disk before the run:

```bash
# VM
df -h / | tee disk-before.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null' | tee -a disk-before.txt
pg -Atc "select pg_size_pretty(pg_database_size('fundlens'))" | tee -a disk-before.txt
```

**Expected:** at least 150 GB available on `/`: the run needs up to ~10 GB of bronze while a zip is on
disk, up to 60 GB of DuckDB scratch, and the silver and gold (spec §3.4). Less than that: stop and free space first.

Open a second tmux window (`Ctrl-b c`) and leave a memory sampler running there for the rest of the run.
It writes `pipeline`'s and Postgres's memory to `mem.txt` every 10 s; step 10 reads the peak from it.

```bash
# VM, tmux window 1 (a new shell: the helpers are not defined here)
cd ~/fundlens-first-run
while true; do docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | grep -E '^(pipeline|fundlens-postgres)-lvch8zyndujjzkz16ksys8im' | sed "s/^/$(date -u +%H:%M:%S) /"; sleep 10; done | tee mem.txt
```

**Expected:** two lines every 10 s, e.g. `14:00:00 pipeline-lvch8zyndujjzkz16ksys8im-… 1.2GiB / 40GiB`.
Switch back with `Ctrl-b 0`. The limit is 40 GB, with DuckDB held to 28 GB; `pipeline` near 40 GiB during
`transform` or `load` means the step is about to be killed for memory.

## 2. Extract

```bash
# VM
time docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --build-id "$B" 2>&1 | tee extract.log
mk extracted
r2ls bronze/cycle=2024/
```

**Expected:** one `<file>: downloaded bronze/cycle=2024/<file>/<today>.zip` line per FEC bulk file; an
`extracted` marker whose `build_id` is `$B`; the same zips listed in R2 with their sizes and a total, the
bronze GB for the capacity record. `extract` keeps a local copy only of the cycle the calendar puts next
(2026 until 2027-01-01; spec §3.4, §5.6), so for 2024 R2 is where bronze is measured. **Estimated:** 5–30 min, most of it the `indiv` zip (several GB).

On a crash (a traceback here, a Bugsink issue `pipeline_mode=extract`), fix the cause and run the same
command again: files already in R2 come back `unchanged`.

## 3. Seats

```bash
# VM
S=$SECONDS; time docker exec "$(fl pipeline)" fundlens seats --cycle 2024 --report --build-id "$B" 2>&1 | tee seats.log; echo "seats $((SECONDS - S)) s" | tee seats-time.txt
r2ls "silver/race/cycle=2024/build=$B/"
pg -c "select count(*) from app.unmatched_filing where cycle = 2024"
```

**Expected:** `house: 441 races (0 special)` (435 districts and 6 delegate seats), `senate: 35 races
(2 special)` (the 33 class 1 seats and the CA and NE specials), `president: 1 races (0 special)`; then
`wrote silver/race/cycle=2024/build=<B>/…`, the `unmatched:` lines and `N unmatched filings recorded`.
R2 lists the partition, and the count query returns `N`. **Estimated:** under a minute.

`seats` writes no marker, so its seconds go to `seats-time.txt`. Write `N` in the Log. Dozens of unmatched filings
are normal (paper filers, bad district codes). Hundreds mean the seat calendar is wrong: stop and file a
ticket.

## 4. Transform

```bash
# VM
time docker exec "$(fl pipeline)" fundlens transform --cycle 2024 --build-id "$B" 2>&1 | tee transform.log
mk transformed
r2ls silver/ | grep "cycle=2024/build=$B/"
docker exec "$(fl pipeline)" sh -c "du -sh /data/fundlens/silver/*/cycle=2024/build=$B" | tee silver-sizes.txt
docker exec "$(fl pipeline)" sh -c "du -cb /data/fundlens/silver/*/cycle=2024/build=$B | tail -1" | awk '{printf "silver %.2f GB\n", $1/1e9}' | tee -a silver-sizes.txt
```

**Expected:** a `<table>: <n> rows` line each for `committee`, `candidate`, `candidate_committee_link`,
`contribution` and `committee_transfer`, then `wrote …` lines; a `transformed` marker with the same row
counts; R2 keys for those five tables and `race` under `build=$B`; a size per table and a silver total.
`contribution` runs to tens of millions of rows. **Estimated:** 15–90 min.

A failed check aborts before anything is uploaded: the traceback names the `sql/checks/silver_*.sql`
file whose query returned rows, and Bugsink gets an issue `pipeline_mode=transform`. That is the spec
not holding on real data. Stop, file a ticket with the check's name and a few of the rows it returns,
link it from NEU-2046, and continue only once it is fixed.

## 5. Load

```bash
# VM
time docker exec "$(fl pipeline)" fundlens load --cycle 2024 --build-id "$B" 2>&1 | tee load.log
mk loaded
pg -c "select build_id, published_at, cycles from gold_build.meta"
pg -c "select c.relname, c.reltuples::bigint as rows, pg_size_pretty(pg_total_relation_size(c.oid)) as size from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'gold_build' and c.relkind = 'r' order by pg_total_relation_size(c.oid) desc"
```

**Expected:** a `<table>: <n> rows` line per gold table, then `loaded build <B> into gold_build
(aggregates <a> s, copy <c> s)`, kept in `load.log` for step 10. Those two figures are the real-cycle
measurement of the DuckDB → CSV → `COPY` load that ADR-0007 and the NEU-2039 spec §8 left to this run. Then a `loaded`
marker; `gold_build.meta` with `build_id` `<B>`, no `published_at`, and `cycles` of
`{"2024": {"build_id": "<B>", "source_dates": {…}}}` with today's date for each file; and the table
list, `race` at 477 rows (441 + 35 + 1). **Estimated:** 10–60 min.

A failed `sql/checks/gold_*.sql` check leaves no `gold_build` behind. Handle it like a failed transform
check: file a ticket and stop.

## 6. Resume the `fundlens/publish` monitor

Kuma refuses a push to a paused monitor, so without this `publish`'s push is lost and step 8 shows
nothing. Kuma → `fundlens/publish` → *Resume*. Leave `fundlens/weekly` paused: NEU-2063 resumes it when it
schedules the run.

**Check:** `fundlens/publish` is no longer *Paused* in Kuma's list. It may read *Pending* until the first
push.

## 7. Publish

```bash
# VM
time docker exec "$(fl pipeline)" fundlens publish --cycle 2024 2>&1 | tee publish.log
mk published
pg -c "select build_id, published_at, cycles from gold.meta"
pg -Atc "select nspname from pg_namespace where nspname like 'gold%' order by 1"
```

**Expected:** `published build <B> of 2024`, `previous build: none`, `cloudflare purge: done` and
`pruned 0 silver builds (0 objects)` (more only if an abandoned earlier attempt left a build); a
`published` marker; `gold.meta.published_at` set; and the schemas `gold` and `gold_prev`. This first
`gold_prev` is empty: the swap creates an empty `gold` to rename when there is none (`publish/gold.py`),
so `publish --rollback` has nothing to go back to yet. **Estimated:** 75 s to 3 min: the purge waits 75 s
after the swap on purpose (spec §5.5).

`cloudflare purge: skipped (not configured)` means `CLOUDFLARE_ZONE_ID` or `CLOUDFLARE_API_TOKEN` is
empty in `pipeline` (coolify-setup step 6). Set it in Coolify and redeploy, then purge by hand before
step 9:

```bash
# laptop. Paste the token from the vault item `fundlens Cloudflare purge token` at the prompt, and the
# Zone ID from the As built table in cloudflare-setup.md.
read -rs PURGE_TOKEN
ZONE=<zone id>
curl -s -X POST -H "Authorization: Bearer $PURGE_TOKEN" -H "Content-Type: application/json" \
  --data '{"purge_everything":true}' "https://api.cloudflare.com/client/v4/zones/$ZONE/purge_cache"
echo
```

**Expected:** `"success":true`.

## 8. Signals

- **Kuma:** `fundlens/publish` is **up**, its latest message `publish: ok`.
- **Bugsink** → `fundlens`: no new issue since step 2. An issue there is from a step that crashed and
  was run again: note it in the Log, then resolve it.
- **Discord `#alerts`:** nothing from fundlens but Kuma's `fundlens/publish` going up.

Then Kuma → `fundlens/publish` → *Pause* again. Nothing publishes until NEU-2063's schedule, so a running
monitor would go down in 7.5 days. NEU-2063 resumes both.

## 9. Verify

### 9.1 The API serves the build, cached at the edge

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq '{build_id, published_at, cycles}'
for i in 1 2; do curl -sS -D - -o /dev/null https://api.fundlens.org/v1/meta | grep -iE '^HTTP|^etag|^cf-cache-status'; done
for i in 1 2; do curl -sS -D - -o /dev/null https://api.fundlens.org/v1/races/2024/senate/MD | grep -iE '^HTTP|^etag|^cf-cache-status'; done
```

**Expected:** `build_id` and `cycles."2024".build_id` are both `<B>`. Each pair of requests: `HTTP/2 200`
with an `etag` carrying `<B>`, the first `cf-cache-status: MISS` and the second **`HIT`**. That is the
`/v1/meta` HIT [cloudflare-setup.md](cloudflare-setup.md) step 12 left to this run. A first-request `HIT`
with no `<B>` in the `etag` means the purge never reached the zone: purge by hand (the `curl` in step 7)
and repeat.

### 9.2 The race page

Open `https://fundlens.org/race/2024/senate/MD` in a browser.

**Expected:** the race heading; Angela Alsobrooks (`S4MD00327`) and Larry Hogan (`S4MD00483`) among the
candidates, with totals; the totals chart; the top committees. Click Alsobrooks: her candidate page lists
itemized contributions. On a blank page or an error banner, open the browser's network tab and write down
which `/v1/…` request failed.

### 9.3 Totals reconcile with FEC.gov

`total_individual` adds up the itemized individual contributions in FEC's bulk `indiv` file, net of
refunds: a refund (22Y) subtracts (NEU-2073). FEC reports the two apart, as gross itemized contributions
and a separate refunds line. So the check runs twice, and each needs to pass:

- **Net:** fundlens's `total_individual`, from the API, against FEC's itemized figure minus FEC's
  refunds. This proves the netting.
- **Gross:** fundlens's receipts with refunds left out, from silver, against FEC's itemized figure.
  This proves nothing was lost on the way in.

The FEC query asks for the two-year period (`election_full=false`): a Senate candidate's default FEC
total covers all six years of the term.

```bash
# laptop: net
R=$(mktemp)
curl -sS https://api.fundlens.org/v1/races/2024/senate/MD > "$R"
jq -r '.candidates | sort_by(-.total_individual) | .[:2][] | .candidate_id' "$R" | while read -r C; do
  F=$(curl -sS "https://api.open.fec.gov/v1/candidate/$C/totals/?cycle=2024&election_full=false&api_key=DEMO_KEY" | jq -c 'if .results[0] then .results[0] | [.individual_itemized_contributions, .refunded_individual_contributions] else null end')
  if [ "$F" = null ]; then echo "$C: FEC sent no totals"; continue; fi
  jq -r --arg c "$C" --argjson fec "$F" '.candidates[] | select(.candidate_id == $c) | ($fec[0] - $fec[1]) as $net | "\(.candidate_id) \(.name): fundlens net \(.total_individual)  FEC itemized \($fec[0]) - refunds \($fec[1]) = \($net)  diff \(((.total_individual - $net) / $net * 10000 | round) / 100) %"' "$R"
done
```

```bash
# VM: gross, from this build's silver
docker exec -i "$(fl pipeline)" python - "$B" <<'PY'
import sys

import duckdb

path = f"/data/fundlens/silver/contribution/cycle=2024/build={sys.argv[1]}/**/*.parquet"
refund = "regexp_matches(transaction_type, '^[24][0-9]Y$')"
rows = duckdb.execute(
    f"SELECT candidate_id, sum(amount) FILTER (WHERE NOT {refund}) AS gross,"
    f" -sum(amount) FILTER (WHERE {refund}) AS refunds"
    f" FROM read_parquet('{path}')"
    " WHERE candidate_id IN ('S4MD00327', 'S4MD00483') AND NOT is_self_funding"
    " GROUP BY 1 ORDER BY 1"
).fetchall()
for candidate_id, gross, refunds in rows:
    print(f"{candidate_id}: gross {gross}  refunds {refunds}")
PY
```

**Expected:**

- **Net:** two lines, Alsobrooks and Hogan, each with a `diff` inside **±2 %**.
- **Gross:** each gross figure within **±2 %** of FEC's itemized one.

FEC's figures on 2026-10-31:

| Candidate | Itemized | Refunds |
| --- | --- | --- |
| `S4MD00327` Alsobrooks | $15,550,208.26 | $503,954.71 |
| `S4MD00483` Hogan | $4,729,854.29 | $54,311.49 |

A dry run of this build's SQL on the same FEC files gave both candidates about −0.4 % on each check
(NEU-2073). On FEC.gov the figures are on the candidate's page → *Financial summary*, two-year period
*2023–2024*: the itemized line under *Individual contributions*, and *Refunds to individuals*.

FEC's figures come from each report's summary page and fundlens's from the itemized rows, so they rarely
match to the cent. FEC's refunds line also covers refunds of unitemized gifts, so the net check is the
looser of the two. Inside ±2 %: write the figures in the Log. Outside: write them in the Log and file a
ticket with the figures and the candidate's committees (`https://api.fundlens.org/v1/candidates/<id>`).

`FEC sent no totals` in place of a line is almost always `DEMO_KEY`'s rate limit: 40 calls an hour per IP
address, shared with anyone else on it. This runbook makes three FEC calls in all, so wait an hour and run
the block again.

### 9.4 An ActBlue earmark counts once

FEC lists the earmark from [Facts](#facts) twice, the recipient's `15E` and ActBlue's `24T`; fundlens must
count it once, on the recipient (ADR-0004). The API check reads only the first page of `C00840017`'s
contributions, 100 rows newest first. That is enough: FEC shows 6 of its gifts dated 2024-12-31, the
newest date in the cycle (checked 2026-10-30).

```bash
# laptop
curl -sS "https://api.open.fec.gov/v1/schedules/schedule_a/?contributor_name=KELLER%2C+CAREN&two_year_transaction_period=2024&min_date=2024-12-31&max_date=2024-12-31&api_key=DEMO_KEY" | jq -r '.results[] | [.committee_id, .receipt_type, .contribution_receipt_amount, .memo_text] | @tsv'
curl -sS "https://api.fundlens.org/v1/committees/C00840017/contributions?cycle=2024" | jq -r '.contributions[] | select(.contributor_name == "KELLER, CAREN") | [.source_record_id, .date, .amount, .recipient_committee_id, .conduit_committee_id] | @tsv'
```

Then every silver row for the gift, whatever its recipient:

```bash
# VM
docker exec -i "$(fl pipeline)" python - "$B" <<'PY'
import sys

import duckdb

path = f"/data/fundlens/silver/contribution/cycle=2024/build={sys.argv[1]}/**/*.parquet"
rows = duckdb.execute(
    "SELECT recipient_committee_id, conduit_committee_id, amount, date, transaction_type"
    f" FROM read_parquet('{path}')"
    " WHERE contributor_name = ? AND amount = ? AND date = CAST(? AS DATE)",
    ["KELLER, CAREN", 250, "2024-12-31"],
).fetchall()
print(*rows, sep="\n")
print(len(rows), "rows")
PY
```

**Expected:** FEC prints two rows, `C00840017 15E 250.0 …` and `C00401224 24T 250.0 …`. fundlens's API
prints one, recipient `C00840017`, conduit `C00401224`. Silver prints that one `15E` row and `1 rows`. Two
rows in fundlens means the earmark rule did not hold on real data: file a ticket.

## 10. Disk after, and the capacity record

```bash
# VM
df -h / | tee disk-after.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null' | tee -a disk-after.txt
pg -Atc "select pg_size_pretty(pg_database_size('fundlens'))" | tee -a disk-after.txt
pg -Atc "select round(sum(pg_total_relation_size(c.oid)) / 1e9, 2) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'gold' and c.relkind = 'r'" | sed 's/^/gold GB /' | tee -a disk-after.txt
r2ls bronze/cycle=2024/ | tail -1 | sed 's/^/bronze /' | tee -a disk-after.txt
for s in extracted transformed loaded published; do mk "$s" | grep -E '"step"|"duration_s"'; done | tee durations.txt
```

Stop the memory sampler (tmux window 1, `Ctrl-c`), then gather every figure the capacity row needs in one
file:

```bash
# VM, tmux window 0
{
  echo "build $B"
  docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES | sed 's/.*service.version=/sha /'
  grep -E '"step"|"duration_s"' durations.txt | paste - - | tr -d ' ,"'
  cat seats-time.txt
  grep -o 'aggregates [0-9.]* s, copy [0-9.]* s' load.log
  grep -E '^(bronze|gold GB)' disk-after.txt
  tail -1 silver-sizes.txt
  echo "peak pipeline memory $(grep ' pipeline-' mem.txt | awk '{print $3}' | sort -h | tail -1)"
} | tee capacity-2024.txt
```

**Expected:** `/` down by roughly silver + gold (no local bronze for 2024, and scratch is emptied as each
step ends). `capacity-2024.txt` holds the build, the SHA, four `step:<name>  duration_s:<seconds>` lines, the
seats seconds, load's two halves, bronze, gold and silver GB, and the peak memory.

Copy `capacity-2024.txt` to the laptop and fill in the 2024 row of [`docs/capacity.md`](../capacity.md)
from it, in a PR of its own, `docs(capacity): 2024 first-run row (NEU-2046)`:

```bash
# laptop
scp hetzner-01:fundlens-first-run/capacity-2024.txt .
cat capacity-2024.txt
```

## 11. Record the run

Append a Log entry with: the date, the build ID, the deployed SHA, each step's time and anything it
printed that you did not expect, the unmatched-filing count, the reconciliation figures from 9.3, the peak
`pipeline` memory, and every deviation. File each deviation from the spec as a ticket and link it from
NEU-2046.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-10-31 — First run (NEU-2046)

Build `20261031T012553Z`, published at 03:59:41 UTC from `d67cec2`. Every check passed in the end. The
figures are in [`docs/capacity.md`](../capacity.md):

- extract 454 s (bronze 4.77 GB in R2);
- seats 5 s, with 51 unmatched filings (bad district codes, early 2026 Senate filers, DC shadow senators);
- transform 407 s (silver 0.91 GB, 51,014,276 contributions);
- load 4.1 s (aggregates 0.84 s, `COPY` 2.21 s; gold 0.04 GB);
- publish 75 s;
- peak `pipeline` memory 27.2 GiB.

Step 9.3, against FEC's 2023–2024 figures:

| Candidate | Net | Gross |
| --- | --- | --- |
| Alsobrooks | $14,991,464 against $15,046,254 (−0.36 %) | $15,481,706 against $15,550,208 (−0.44 %) |
| Hogan | $4,659,760 against $4,675,543 (−0.34 %) | $4,711,180 against $4,729,854 (−0.39 %) |

Step 9.4: the Keller earmark appeared once in the API and once in silver.

Deviations, each filed and fixed or ticketed before the run went on:

- **Step 4, first try:** `File is not latin-1 encoded`. DuckDB 2.0's latin-1 reader refuses bytes
  0x80–0x9F, and `cn24` holds a UTF-8 name. Fixed by transcoding to UTF-8 on unzip (NEU-2069, PR #32).
- **Step 4, second try:** four silver checks failed.
  - `oth` repeats every `pas2` row and holds disbursements, 15J JFC memo lines and candidate loans.
  - ActBlue's own tips were tagged with ActBlue as their conduit, and its type-15 "EARMARKED FOR" lines were
    the conduit's side of earmarks.
  - A fringe committee is missing from `cm`.

  Fixed in NEU-2070 (PR #33). Follow-ups: loans as self-funding (NEU-2071), 15J for resolution (NEU-2072).
- **Before step 4's third try:** a dry run on FEC's public files found every 22Y refund *added*. Most filers
  write refunds positive and some negative, and voided refund checks mirror a refund. Refunds now subtract
  whatever their sign, and voids add back (NEU-2073, PR #34). 24I rows are left for NEU-2074. Step 9.3 now
  checks net and gross.
- **Step 5, first try:** `gold_committee_top_recipient_candidate` failed. Givers write stale candidate IDs on
  24Ks (Ricketts, Sam Brown, Curtis's old House ID). A gift is now credited through its recipient's `ccl` link
  (NEU-2075, PR #35). Step 4 was re-run on the same build before step 5.
- **Step 5:** David Trone shows `self_funding` 0. His $62.9M is loans (16C), which M2 does not count. Recorded
  on NEU-2071.
- **Step 7:** `pruned 1 silver builds (1 objects)`, not 0. A stray object from an earlier build. The live
  build's six objects were checked intact.
- **Step 9.1:** `/v1/meta` was `HIT` on its first looped request, because the `jq` line before the loop had
  already filled the cache. The race endpoint showed `MISS` then `HIT`.
- **Not run in the dev container:** the full gold build over real data. Building `contribution` needs about
  8–10 GB of DuckDB memory. Prod's `load` was the first full gold check, and it passed.
