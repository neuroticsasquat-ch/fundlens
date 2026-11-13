# Runbook: backfill every cycle since 1980

How to put every federal cycle from 1980 to 2026, the one FEC is still filing, live on `music-box-dancer`, and measure what it costs
(NEU-2060; spec §3.4, §5.6, §10.5, §10.6). Each cycle is extracted, transformed, loaded and published on its own,
oldest first. Then one `fundlens resolve --full` links every cycle's contributor keys at once, and one last load and
publish puts the donors live. The figures go into [`docs/capacity.md`](../capacity.md), and its closing section
checks them against the handover's triggers for an ephemeral runner. Run it one cycle at a time, with the disk
and memory checks between cycles. Append to the [Log](#log) at the bottom; never rewrite it.

**Why not `fundlens run --cycle C` per cycle.** `run` resolves after every transform, and only `--full`
resolution exists (incremental is NEU-2062). So a `run` per cycle would retrain the model over every cycle
transformed so far, 23 times over, each run larger than the last. This runbook runs `run`'s other steps by hand
under one build ID per cycle. The commands are the ones `run` calls, and they write the same markers. Resolution
runs once, in step 5. Step 6 is a real `fundlens run`, resuming the 2026 build from `load`. Like `run` without
`--scheduled`, no command here pushes the `fundlens/weekly` monitor. `publish` pushes `fundlens/publish`, which
stays paused (Facts).

**Why each cycle is published before it is resolved.** `load` rebuilds all of gold from every cycle's live build
(`markers/live.json`), so a cycle reaches gold only by being published. A cycle loaded before resolution has no
donor IDs: its committee, candidate and race figures are complete, and it has no donors. That lets each cycle be
checked on fundlens.org as soon as it is built. 2024 keeps its donors throughout, because its live build is
resolved already.

**Why the oldest first.** The cycles grow over time, so the early ones test the per-cycle procedure cheaply, and
step 1.4 shows where memory becomes a question. 2026 is last because FEC still amends its files every
week. It goes through the same steps, and its build is the one step 6 resumes.

**Why 2024 is not rebuilt.** Its live build `20261112T211727Z` was transformed on 2026-11-12. The only change to
silver since then is NEU-2059's `ccl` fallback, which applies before 2000 only. Step 1.2 checks this. If any other
silver change has merged since, 2024 is transformed again with the others, and published only in step 6
(step 3.5).

**Not in this runbook:** adjudicating the clusters the other cycles add (an [adjudicating.md](adjudicating.md) run
of its own, afterwards), scoring cycles other than 2024 against DIME (DIME is imported for 2024 only,
[refreshing-dime.md](refreshing-dime.md)), the scheduled weekly run and resuming the Kuma monitors (NEU-2063).

## Before you start

- NEU-2059 and NEU-2061 are merged, and so is this runbook. Step 1.1 checks that the deployed code includes them.
- **Nothing merges to `main` from step 1.1 until step 8.** Every merge redeploys `pipeline` and kills a running
  `docker exec`. On 2026-11-02 a docs merge killed a `publish` part way. A merge between cycles is just as bad:
  it changes the code the remaining cycles are built with. Step 1.1 turns off the `dependencies` workflow, which
  auto-merges Dependabot's PRs; step 8 turns it back on.
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo, `gh`
  and `jq` are installed, and you can sign in to Coolify, Bugsink (`https://bugsink.neuroticsasquat.ch`) and
  SigNoz (tailnet).
- Allow two or three days of sessions. The 2024 transform took 22–31 min (`capacity.md`), and the cycles before it
  are smaller. Each load rebuilds all of gold, so loads get slower as cycles go live: 2024's alone took about
  3 min. Resolving every cycle at once has never been measured. A cycle can be left between any two steps: step
  3.4 resumes it.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycles to build | 1980, 1982, …, 2022, then 2026: 23 cycles, in that order. `ccl` starts in 2000; before that the transform links candidates through `cn.CAND_PCC` and `cm.CAND_ID` (NEU-2059) |
| Live before this run | `gold.meta.cycles` = {2024: `20261112T211727Z`}, and `markers/live.json` the same (NEU-2059's manual steps, 2026-11-12) |
| `pipeline` memory | `mem_limit: 40g` (40 GiB), `docker-compose.prod.yml`. DuckDB's `memory_limit` is `DUCKDB_MEMORY_LIMIT`, by default `28GB` (26.08 GiB; DuckDB's GB is 10⁹ bytes) |
| 2024's memory, the reference | Transform peaked at 24.34 GiB of `pipeline` under the 28 GB limit, after NEU-2076's fix; the first run peaked at 27.2 GiB. `resolve --full` peaked at 24.54 GiB (`capacity.md`) |
| Raised limit | `DUCKDB_MEMORY_LIMIT=32GB` (29.80 GiB), set before the first cycle whose `indiv` is larger than 2024's (step 2). That leaves 10.2 GiB of the container for Python and Parquet buffers: 2024's transform used up to 1.1 GiB above DuckDB's limit. 32 GB is the top of the handover's 24–32 GB rule |
| Disk floor | **Stop if free disk on `/` drops under 60 GB**, at any time. Start a cycle only with at least 130 GB free: up to 60 GB of DuckDB scratch (`DUCKDB_MAX_TEMP_DIRECTORY_SIZE`), about 10 GB of unzipped bronze, and the floor |
| Other tenants on `/` | SigNoz's ClickHouse, which grows with every trace and log, so its retention decides how fast it grows (handover §5). Step 4 is the pause for it |
| Monitors | `fundlens/weekly` and `fundlens/publish` stay **paused** until NEU-2063. So every `publish` ends with `kuma push (up) failed: HTTPError: HTTP Error 404: Not Found`. That is the paused monitor refusing the push, not a fault: leave both paused |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-backfill
```

In the tmux session, define the helpers. Paste the whole block:

```bash
# VM, in tmux
mkdir -p ~/fundlens-backfill && cd ~/fundlens-backfill
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# psql in the fundlens database.
pg() { docker exec "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
# A step's completion marker, or MISSING: `mk <step> <cycle> <build>`.
mk() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; m = markers.read(sys.argv[1], R2.from_settings(get_settings()), cycle=int(sys.argv[2]), build_id=sys.argv[3]); print(m.model_dump_json(indent=2) if m else "MISSING")' "$1" "$2" "$3"; }
# Each cycle's live build, from markers/live.json.
live() { docker exec "$(fl pipeline)" python -c 'from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; print(markers.read_live(R2.from_settings(get_settings())))'; }
# Free disk on / in decimal GB, as capacity.md counts sizes.
free_gb() { df -BGB --output=avail / | tail -1 | tr -dc '0-9'; }

# One cycle's steps under one build, as `fundlens run` orders them but without `resolve`.
#   cycle_run <cycle>                          a new build, extract to publish
#   cycle_run <cycle> <build> <from> [<to>]    resume that build from step <from>, up to step <to>
# Steps: extract seats transform load publish. Stops at the first step that fails. Each step's
# output is in <cycle>/<step>.log, with `time`'s figures at its end.
cycle_run() {
  local c=$1 b=${2:-$(date -u +%Y%m%dT%H%M%SZ)} from=${3:-extract} to=${4:-publish} on= s extra rc
  mkdir -p "$c" && echo "$b" > "$c/build-id.txt"
  echo "$(date -u +%FT%TZ) start $c $b $from-$to" | tee -a "$c/window.txt"
  for s in extract seats transform load publish; do
    [ "$s" = "$from" ] && on=1
    if [ -n "$on" ]; then
      extra=; [ "$s" = seats ] && extra=--report
      echo "== $s $c $b $(date -u +%FT%TZ), free $(free_gb) GB"
      ( set -o pipefail; { time docker exec "$(fl pipeline)" fundlens "$s" --cycle "$c" $extra --build-id "$b"; } 2>&1 | tee -a "$c/$s.log" )
      rc=$?
      if [ "$rc" -ne 0 ]; then
        echo "$(date -u +%FT%TZ) STOPPED $c $b at $s, exit $rc" | tee -a "$c/window.txt"
        return 1
      fi
    fi
    [ "$s" = "$to" ] && break
  done
  echo "$(date -u +%FT%TZ) end $c $b" | tee -a "$c/window.txt"
}

# The peak `pipeline` memory while a cycle ran, and the least free disk: `cycle_peak <cycle>`.
cycle_peak() {
  local from to
  from=$(awk '$2 == "start" { print $1; exit }' "$1/window.txt")
  to=$(awk '$2 == "end" || $2 == "STOPPED" { t = $1 } END { print t }' "$1/window.txt")
  awk -v from="$from" -v to="$to" '$1 >= from && $1 <= to {
      f = $NF; sub(/^free=/, "", f); f += 0
      if (low == "" || f < low) low = f
      if ($2 !~ /^pipeline-/) next
      n = $3 + 0; u = $3; sub(/^[0-9.]+/, "", u)
      g = (u == "GiB") ? n : (u == "MiB") ? n / 1024 : (u == "KiB") ? n / 1048576 : n / 1073741824
      if (g > max) { max = g; at = $1 }
    } END { printf "%.2f GiB at %s; least free disk %s GB\n", max, at, low }' ~/fundlens-backfill/mem.txt
}

# The last log line any step of a cycle wrote at or before a UTC time: which step held the peak.
# `where <cycle> <time>`, the time as cycle_peak prints it.
where() {
  cat "$1"/*.log | docker exec -i "$(fl pipeline)" python -c '
import json, sys
at, last = sys.argv[1][:19], None
for line in sys.stdin:
    if line.startswith("{"):
        entry = json.loads(line)
        if entry["ts"][:19] <= at and (last is None or entry["ts"] >= last["ts"]):
            last = entry
print(*((last["ts"], last["message"]) if last else ("no log line before it",)))' "$2"
}
```

**Expected:** no output. If the tmux session is lost, run `tmux attach -t fundlens-backfill`. If the session
itself is gone, `cd ~/fundlens-backfill` and paste the block again. Every build ID is saved in
`<cycle>/build-id.txt`, and the model version in `model-version.txt` from step 5.

Then save the script that writes a cycle's capacity row (step 3.3):

```bash
# VM, in tmux
cat > record.py <<'PY'
"""One cycle's row of capacity.md's Backfill table, from its markers, bronze, silver and gold."""

import os
import re
import sys

import psycopg

from fundlens import markers, paths
from fundlens.fec.extract import Source
from fundlens.fec.files import files_for
from fundlens.r2 import R2
from fundlens.settings import get_settings

cycle, build, seats, peak, free, halves = int(sys.argv[1]), *sys.argv[2:7]
settings = get_settings()
store = R2.from_settings(settings)


def seconds(step):
    marker = markers.read(step, store, cycle=cycle, build_id=build)
    return "—" if marker is None else f"{marker.duration_s:.0f}"


def zip_bytes(name):
    """The size FEC served for the newest bronze zip of one file; None when bronze lacks it."""
    keys = sorted(store.list_keys(paths.bronze_dir(cycle, name)))
    source = Source.from_metadata(store.metadata(keys[-1])) if keys else None
    return source.size if source else None


def gb(size):
    return "—" if size is None else f"{size / 1e9:.2f}"


timed = re.fullmatch(r"(\d+)m([\d.]+)s", seats)
seats_s = f"{int(timed[1]) * 60 + float(timed[2]):.0f}" if timed else "—"
zips = [zip_bytes(file.name) for file in files_for(cycle)]
bronze = None if None in zips else sum(zips)
silver_dir = settings.data_dir / "silver"
silver = sum(
    p.stat().st_size for p in silver_dir.glob(f"*/cycle={cycle}/build={build}/**/*") if p.is_file()
)
with psycopg.connect(settings.database_url) as conn:
    [(gold,)] = conn.execute(
        "SELECT coalesce(sum(pg_total_relation_size(c.oid)), 0)::bigint FROM pg_class AS c"
        " JOIN pg_namespace AS n ON n.oid = c.relnamespace"
        " WHERE n.nspname = 'gold' AND c.relkind IN ('r', 'm')"
    ).fetchall()
# capacity.md writes a load as `<total> (<aggregates> + <copy>)`.
load = seconds("loaded") + ("" if halves == "—" else f" ({halves})")
transformed = markers.read("transformed", store, cycle=cycle, build_id=build)
day = transformed.finished_at.date() if transformed else "—"
release = re.search(r"service\.version=([0-9a-f]{7})", os.environ.get("OTEL_RESOURCE_ATTRIBUTES", ""))
sha = release[1] if release else "unknown"
print(
    f"| {cycle} | {day} | `{build}` | `{sha}` | {gb(zip_bytes('indiv'))}"
    f" | {seconds('extracted')} | {seats_s} | {seconds('transformed')} | {load}"
    f" | {seconds('published')} | {gb(bronze)} | {gb(silver)} | {gb(gold)}"
    f" | {peak} | {settings.duckdb_memory_limit} | {free} | |"
)
PY
# A cycle's capacity row, in <cycle>/row.md: `cycle_record <cycle> "<peak, at step>"`.
cycle_record() {
  local c=$1 seats halves
  seats=$(awk '$1 == "real" { print $2 }' "$c/seats.log" | tail -1)
  halves=$(grep -o 'aggregates [0-9.]* s, copy [0-9.]* s' "$c/load.log" 2>/dev/null | tail -1 | awk '{ print $2 " + " $5 }')
  docker exec -i "$(fl pipeline)" python - "$c" "$(cat "$c/build-id.txt")" "${seats:-—}" "$2" "$(free_gb)" "${halves:-—}" < record.py 2>&1 | grep -v '^{' | tee "$c/row.md"
}
```

**Expected:** no output.

Open a second tmux window (`Ctrl-b c`) and leave a sampler running there until step 8. Every 10 s it writes
`pipeline`'s and Postgres's memory, and the free disk, to `mem.txt`. `cycle_peak` reads it.

```bash
# VM, tmux window 1 (a new shell: the helpers are not defined here)
cd ~/fundlens-backfill
while true; do
  t=$(date -u +%FT%TZ); f=$(df -BGB --output=avail / | tail -1 | tr -dc '0-9')
  docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | grep -E '^(pipeline|fundlens-postgres)-lvch8zyndujjzkz16ksys8im' | sed "s/^/$t /; s/\$/ free=${f}G/"
  sleep 10
done | tee -a mem.txt
```

**Expected:** two lines every 10 s, e.g. `2026-11-14T14:00:00Z pipeline-lvch8zyndujjzkz16ksys8im-… 1.2GiB / 40GiB
free=812G`. Switch back with `Ctrl-b 0`. Glance at this window during long steps:

- **`free=` under 60G: stop the step now.** `docker restart "$(fl pipeline)"` ends whatever runs in it. A
  transform or load killed this way uploads and swaps nothing. Then step 4.
- **`pipeline` above 38 GiB:** the step is about to be killed for memory. Let it run; step 3.4 says what to do if
  it is.

## 1. Preflight

### 1.1 The deployed code, and the merge freeze

```bash
# VM
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES DUCKDB_MEMORY_LIMIT DUCKDB_THREADS
git ls-remote https://github.com/neuroticsasquat-ch/fundlens main
docker exec "$(fl pipeline)" alembic upgrade head
docker exec "$(fl pipeline)" fundlens health; echo "exit=$?"
```

**Expected:** the `service.version=<sha>` in `OTEL_RESOURCE_ATTRIBUTES` is the SHA `ls-remote` prints. If not:
Coolify → the `fundlens` resource → *Deploy*, wait for it to finish, and run this step again. Then `28GB` and `6`.
Alembic reaches head with no error; then `postgres: ok`, `r2: ok`, `exit=0`.

```bash
# laptop
cd ~/projects/fundlens
git fetch origin
SHA=$(ssh hetzner-01 'docker exec "$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)" printenv OTEL_RESOURCE_ATTRIBUTES' | sed 's/.*service.version=//; s/,.*//')
echo "$SHA"
git merge-base --is-ancestor 6790bc8 "$SHA" && echo "multi-cycle deployed"
git merge-base --is-ancestor 5182a75 "$SHA" && echo "run deployed"
gh pr list --repo neuroticsasquat-ch/fundlens --state open
gh workflow disable dependencies --repo neuroticsasquat-ch/fundlens
gh workflow list --repo neuroticsasquat-ch/fundlens --all
```

**Expected:** the SHA, `multi-cycle deployed`, `run deployed`, the open PRs, then `dependencies` listed as
`disabled_manually`. Write the SHA in the Log: every cycle in this run is built from it. None of the open PRs
merges until step 8.

### 1.2 The live state

```bash
# VM
pg -c "select build_id, published_at, model_version, precision, recall, precision_top, recall_top, cycles from gold.meta" | tee meta-before.txt
live | tee live-before.txt
docker exec "$(fl pipeline)" python -c 'from fundlens.r2 import R2; from fundlens.settings import get_settings; from fundlens.resolve.runner import transformed_builds; print(transformed_builds(R2.from_settings(get_settings())))' | tee transformed-before.txt
mk transformed 2024 20261112T211727Z | grep -E '"finished_at"|"contributor"'
```

**Expected:**

- `gold.meta` with build `20261112T211727Z`, a `model_version`, the four figures, and `cycles` holding 2024 only.
- `{2024: '20261112T211727Z'}`, twice. A second cycle, or another 2024 build, means someone published or
  transformed since the Facts were written. Stop and find out what it is.
- The marker's `finished_at` (2026-11-12) and its `contributor` count. Write both in the Log.

Then check that nothing since that transform changed 2024's silver:

```bash
# laptop
git log --first-parent --oneline --since=2026-11-12T21:17:27Z origin/main -- sql/silver src/fundlens/transform src/fundlens/fec src/fundlens/resolve/normalize.py
```

**Expected:** exactly one merge, `6790bc8` (NEU-2059). Its silver change, the empty `ccl` and the link SQL's
fallback, applies to cycles before 2000 only. **Another merge here means 2024's live build is out of date:**
2024 joins step 3 (step 3.5).

### 1.3 Disk and ClickHouse

```bash
# VM
df -h / | tee disk-before.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null' | tee -a disk-before.txt
pg -Atc "select pg_size_pretty(pg_database_size('fundlens'))" | tee -a disk-before.txt
CH=$(docker ps --format '{{.Names}}' | grep -i clickhouse | head -1); echo "$CH"
docker exec "$CH" du -sh /var/lib/clickhouse | tee clickhouse-before.txt
```

**Expected:** at least 200 GB available on `/`. 130 GB is the gate for one cycle, and the cycles' silver accumulates
on top of it. The spec budgets 30–60 GB of silver for every cycle (§3.4). Then the four `/data/fundlens`
directories, the database's size (about 4 GB), the ClickHouse container's name and its data size. Write the
ClickHouse size in the Log: step 4 compares against it. If no ClickHouse container is listed, find SigNoz's with
`docker ps` and use its name.

### 1.4 Each cycle's `indiv` beside 2024's

The transform's memory follows the `indiv` file, the largest by far. FEC's `Content-Length` for each cycle's zip
is the size `extract` will store in bronze. 2024's comes from bronze itself:

```bash
# VM
docker exec -i "$(fl pipeline)" python - <<'PY' 2>&1 | grep -v '^{' | tee indiv-sizes.txt
from urllib.request import Request, urlopen

from fundlens import paths
from fundlens.fec.extract import USER_AGENT, Source
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.settings import get_settings

settings = get_settings()
store = R2.from_settings(settings)
indiv = CATALOGUE["indiv"]
newest = sorted(store.list_keys(paths.bronze_dir(2024, "indiv")))[-1]
reference = Source.from_metadata(store.metadata(newest)).size
print(f"2024: {reference / 1e9:.2f} GB, bronze {newest}")
print("| Cycle | indiv GB | Of 2024's | |\n| --- | ---: | ---: | --- |")
for cycle in [*range(1980, 2024, 2), 2026]:
    head = Request(indiv.url(settings.fec_bulk_url, cycle), method="HEAD", headers={"User-Agent": USER_AGENT})
    with urlopen(head, timeout=60) as response:
        size = int(response.headers["Content-Length"])
    print(f"| {cycle} | {size / 1e9:.2f} | {size / reference:.0%} | {'LARGER' if size > reference else ''} |")
PY
```

**Expected:** 2024's size, then a row per cycle, 1980 to 2022 and 2026. The early cycles are a small fraction of
2024's. Write in the Log the first cycle marked `LARGER`, or `none`. **Step 2 runs before that cycle**, and the
limit stays raised for every cycle after it, for step 5 and for step 6.

If no cycle is `LARGER`, step 2 still runs before step 5. Resolution loads every cycle's contributor keys at once
(spec §6.10), several times 2024's.

## 2. Raise DuckDB's memory limit

Run this once, between two cycles: before the first `LARGER` cycle, or before step 5 if none is. A deploy kills any
running `docker exec`, so check first that no step is running: the last line of the cycle's `window.txt` reads `end`.

1. Coolify → *Projects* → `fundlens` → *production* → the `fundlens` resource → *Environment Variables*.
2. If `DUCKDB_MEMORY_LIMIT` is listed, write its current value in the Log and set it to `32GB`. If it is not
   listed, *+ Add*: name `DUCKDB_MEMORY_LIMIT`, value `32GB`. Either way leave *Build Variable* unticked, *Save*.
   This entry overrides the compose file's `28GB` fallback until step 8 removes it
   ([coolify-setup.md](coolify-setup.md) §6).
3. *Deploy* (top right). Wait for the deployment log to end, and for `api` to show healthy.

```bash
# VM
docker exec "$(fl pipeline)" printenv DUCKDB_MEMORY_LIMIT OTEL_RESOURCE_ATTRIBUTES
```

**Expected:** `32GB`, and the same `service.version` as step 1.1. The redeploy built the same commit, so nothing
else changed. `pipeline` is a new container, so the sampler's lines now show its new name; `fl` finds it. Write
the time in the Log. Every row after it shows `32GB` in its DuckDB limit column.

## 3. One cycle

Repeat steps 3.1–3.3 for each cycle in order: 1980, 1982, …, 2022, then 2026. Set the cycle first:

```bash
# VM, in tmux
C=1980
```

### 3.1 Before the cycle

```bash
# VM, in tmux
free_gb; grep -E "^\| $C \|" indiv-sizes.txt
```

**Expected:** at least `130`, and the cycle's `indiv` row.

- Under 130: step 4, then come back.
- The first row marked `LARGER`, and step 2 has not run: step 2 now.

### 3.2 Run it

```bash
# VM, in tmux
cycle_run "$C"
```

**Expected,** each step's output and then its `time` lines, ending with a `… end <C> <build>` line:

- `extract`: a `<file>: downloaded bronze/cycle=<C>/<file>/<date>.zip` line per file, or `unchanged` for a zip bronze
  already holds (2026's may be). That is five files before 2000 and six from 2000, when `ccl` starts. The
  historical zips are deleted from local disk once they are in R2.
- `seats`: `house: <n> races`, `senate: <n> races`, a `president` line in years divisible by 4, `wrote
  silver/race/cycle=<C>/build=<B>/…`, and the unmatched filings recorded.
- `transform`: a `<table>: <n> rows` line per silver table, then `wrote …` lines. Every count is above 0 except
  perhaps `jfc_attribution`, `organization_receipt` and `independent_expenditure` in the early cycles.
- `load`: a `<table>: <n> rows` line per gold table. `quality: not validated for model …` or the 2024 figures are
  both fine here. Then `loaded build <B> into gold_build (aggregates <a> s, copy <c> s)`, which means every gold
  check passed.
- `publish`: `published build <B> of <C>`, `previous build: none` (the cycle had no live build before),
  `cloudflare purge: done`, `wrote resolution/build=<B>/crosswalk.parquet`, `pruned <n> silver builds`, then the
  expected Kuma 404 (Facts).

Then check it:

```bash
# VM, in tmux
B=$(cat "$C/build-id.txt")
for s in extracted transformed loaded published; do printf '%s ' "$s"; mk "$s" "$C" "$B" | grep -c '"duration_s"'; done
live
pg -c "select cycle, race_count, contribution_count, total_amount from gold.cycle order by cycle"
curl -sS "https://api.fundlens.org/v1/cycles" | jq -c '[.[] | {cycle, races: .race_count, contributions: .contribution_count}]'
```

**Expected:** `1` after each of the four steps. `live` lists every cycle published so far, with `<C>` at `<B>` and
2024 still at `20261112T211727Z`. `gold.cycle` has a row for `<C>`, and its `race_count`, `contribution_count`
and `total_amount` are all above 0. The rows for the cycles before it are unchanged. The API lists the same.

Open `https://fundlens.org/cycles/<C>` in a browser. **Expected:** the cycle's races by office and state, with
non-zero totals.

### 3.3 Record it

```bash
# VM, in tmux
cycle_peak "$C"
```

It prints the peak and when it happened, e.g. `24.34 GiB at 2026-11-14T17:45:03Z; least free disk 702 GB`. Name the
step that held it:

```bash
# VM, in tmux
where "$C" <the time cycle_peak printed>
cycle_record "$C" "<peak> GiB, <step>"
```

**Expected:** `where` prints the last log line written before the peak, such as `silver check
silver_contribution_key.sql` or `write contribution 2016`. Its message is the step in the peak column: `24.34 GiB,
write contribution`. Then `cycle_record` prints the cycle's row of `capacity.md`'s Backfill table into
`<C>/row.md`. Step 9 collects the rows. Next cycle: step 3.1.

### 3.4 When a step fails

`cycle_run` stops at the failed step and prints `STOPPED <C> <B> at <step>`. Bugsink gets an issue tagged
`pipeline_mode=<step>`. Nothing later in the cycle ran, and the live gold is the last cycle's.

| What failed | What to do |
| --- | --- |
| `transform` stops with exit 1 and an `Out of Memory Error` from DuckDB (Bugsink gets it too) | DuckDB reached its `memory_limit` and could not spill. Nothing was uploaded. If step 2 has not run, run it now, then run the cycle again under a new build: `cycle_run "$C"`. If the limit was raised already, stop: file a ticket with the peak and the step `where` names, and link it from NEU-2060 |
| A step stops with `exit 137`, and the sampler showed `pipeline` near 40 GiB | The container killed it for memory: what outgrew the 40 GiB was outside DuckDB's limit, so raising that limit would make it worse. Nothing was uploaded or swapped. Stop: file a ticket with the peak, the step `where` names and the DuckDB limit, and link it from NEU-2060 |
| `transform` names a `sql/checks/silver_*.sql` | A check returned rows, so nothing was uploaded. Stop, file a ticket with the check's name and a few of its rows, and link it from NEU-2060. The cycles after it wait for the fix, because they are built from one SHA |
| `extract` fails on FEC (a timeout, a `DownloadError`) | It retried five times already. Wait ten minutes, then resume the build: `cycle_run "$C" "$(cat $C/build-id.txt)" extract` |
| `load` names a `sql/checks/gold_*.sql`, or `publish` fails | No `gold_build` was kept, or the swap rolled back, and the live gold is unchanged. A gold check that fails on an old cycle is a ticket, as above. Resume with `cycle_run "$C" "$(cat $C/build-id.txt)" load`: the transform is not repeated |
| The SSH session or tmux died | `docker exec` stopped with it, but the step may not have. Check `docker top "$(fl pipeline)"` for a `fundlens` process and wait until it is gone. Then compare the markers (step 3.2's loop) and resume from the first step without one |

A rerun under a new build leaves the failed build's files behind, without a `transformed` marker. `resolve` and
`load` read only builds with one. `publish` prunes the old silver builds.

### 3.5 2024, if step 1.2 found another silver change

Transform 2024 again after 2022 and before 2026, but do not load or publish it. Its live build keeps its donors
until step 6, which publishes the new build:

```bash
# VM, in tmux
C=2024
cycle_run "$C" "$(date -u +%Y%m%dT%H%M%SZ)" extract transform
```

**Expected:** extract, seats and transform as in step 3.2, then `end`. Record it as in step 3.3. Its row has `—`
for load and publish.

## 4. Pausing for disk

If free disk is under 130 GB before a cycle, find out what grew before going on:

```bash
# VM
df -h /
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null'
pg -Atc "select pg_size_pretty(pg_database_size('fundlens'))"
docker exec "$CH" du -sh /var/lib/clickhouse
```

**Expected:** the free disk, the four `/data/fundlens` directories, the database and ClickHouse. Compare each with
`disk-before.txt` and `clickhouse-before.txt`:

- **ClickHouse grew by more than 10 GB since step 1.3:** SigNoz → *Settings* → *General* → lower the retention
  period of logs and traces, e.g. to 7 days. *Save*. ClickHouse drops expired data in the background. Run the
  ClickHouse line again every 15 minutes until free disk is back above 130 GB, then continue at step 3.1. Write the
  old and new retention in the Log, and set it back in step 8.
- **`/data/fundlens/scratch` is above 1 GB:** a killed step left DuckDB spill behind. Remove it, with no step
  running: `docker exec "$(fl pipeline)" sh -c 'rm -rf /data/fundlens/scratch/*'`.
- **Otherwise the growth is fundlens's own:** silver, or Postgres's gold, beyond the spec's budget. Stop. File a
  ticket with the sizes, linked from NEU-2060. It is the steady-state disk trigger (step 9).

## 5. Resolve every cycle once

### 5.1 What resolution will read

Resolution reads each cycle's newest transformed build. Every one of them must be the build that cycle is live
from, except a 2024 rebuilt in step 3.5:

```bash
# VM, in tmux
docker exec -i "$(fl pipeline)" python - <<'PY' 2>&1 | grep -v '^{' | tee resolve-inputs.txt
from fundlens import markers
from fundlens.r2 import R2
from fundlens.resolve.runner import transformed_builds
from fundlens.settings import get_settings

store = R2.from_settings(get_settings())
live = markers.read_live(store)
total = 0
for cycle, build in transformed_builds(store).items():
    keys = markers.read("transformed", store, cycle=cycle, build_id=build).row_counts.get("contributor", 0)
    total += keys
    state = "live" if live.get(cycle) == build else f"NOT LIVE (live: {live.get(cycle)})"
    print(f"{cycle} {build} {state} contributor {keys}")
# 2024's working file was 9.91 GB for 5,620,495 keys (capacity.md, Resolution).
print(f"contributor keys, summed over cycles: {total}; working file about {total * 9.91 / 5_620_495:.0f} GB")
PY
free_gb
```

**Expected:** 24 lines, 1980 to 2026, each `live`. 2024 is `NOT LIVE` only if step 3.5 rebuilt it. Any other
`NOT LIVE` line means that cycle has a newer transformed build than its live one: resolution would resolve
that build, and step 6 would load the other. Stop and find out where it came from in its `window.txt`. Then
the summed key count and the working file it implies. The sum counts a key once per cycle it appears in, so the
real count is lower. **Free disk must be at least the working file plus 120 GB**: 60 GB of scratch and the 60 GB
floor. Resolution also rewrites every cycle's `contribution` into buckets and uploads it, so silver grows by about
each cycle's `contribution` size while it runs. With less free disk: step 4.

### 5.2 Run it

```bash
# VM, in tmux
export M=$(date -u +%Y%m%dT%H%M%SZ)
echo "$M" | tee model-version.txt
echo "$(date -u +%FT%TZ) start resolve" | tee -a resolve-window.txt
{ time docker exec "$(fl pipeline)" fundlens resolve --full --build-id "$M"; } 2>&1 | tee resolve.log
echo "$(date -u +%FT%TZ) end resolve" | tee -a resolve-window.txt
```

**Expected:**

```
<cycle>: build <B>                  one line per cycle, 1980 to 2026: resolve-inputs.txt's builds
<k> contributor keys in <C> clusters
recluster: …
overrides: <o> merges joining <j> clusters into others, <s> splits
adjudications: <v> verdicts: <a> merges joining <j> clusters into others, <s> splits
crosswalk: <n> new donors, <r> keys re-pointed, <d> redirects
model <M>: trained, wrote resolution/model/<M>.json
load <s> s, train <s> s, cluster <s> s, recluster <s> s, overrides <s> s, adjudications <s> s, save <s> s, crosswalk <s> s, silver <s> s
DuckDB memory limit: 29.8 GiB
```

- Each `<cycle>: build` line names that cycle's build from step 5.1.
- `<k>` is below step 5.1's sum: a key found in several cycles is one key.
- `crosswalk:` holds many new donors, the people only the other cycles know, and some keys re-pointed. Every 2024
  donor ID is kept by the crosswalk's rules. Write all three numbers in the Log.
- The phase times. `silver` rewrites every cycle's `contribution`, so expect it to be the longest.

Never measured at this scale. If it fails part way, run the same command again with the same `M`, as
[first-resolved-run.md](first-resolved-run.md) step 3 describes. If it is killed for memory twice, stop. File a
ticket with the peak and the phase it was in (the last `resolve` log line before the peak), and link it from
NEU-2060. Resolution over every cycle does not fit the box, and that is the ephemeral runner's case (step 9).
The cycles stay live without donors meanwhile.

Then the peak:

```bash
# VM, in tmux
mkdir -p resolve && cp resolve-window.txt resolve/window.txt && cp resolve.log resolve/resolve.log
cycle_peak resolve
where resolve <the time cycle_peak printed>
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/resolution/resolve.duckdb'
docker exec "$(fl pipeline)" python -c 'from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; from fundlens.resolve.runner import transformed_builds; store = R2.from_settings(get_settings()); [print(c, b, "resolved" if markers.exists("resolved", store, cycle=c, build_id=b) else "NOT RESOLVED") for c, b in transformed_builds(store).items()]'
```

**Expected:** the peak, the phase it fell in, the working file's size, and a `<cycle> <build> resolved` line for
every cycle, 1980 to 2026.

### 5.3 Validate 2024

`load` copies only the newest model's DIME figures into `gold.meta`. Without this step, `/v1/meta` and the
methodology page would lose their resolution quality ([refreshing-dime.md](refreshing-dime.md) §5):

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens validate --cycle 2024 | tee validate.txt
```

**Expected:** the `scope precision recall …` table, `matched <m> of <n> counted contributions (<pct>%)` and
`model <M>, DIME v4.0, build <2024's build>`. Compare with `meta-before.txt`. Keys from other cycles can join two
2024 clusters through a contributor key that two different people share, so precision may fall and recall rise. **If overall precision falls by
more than 0.02, stop before step 6.** File a ticket with both sets of figures, linked from NEU-2060: cross-cycle
chaining is what NEU-2122's re-clustering guards against. The live gold still holds the old model's donors, so
nothing is lost by waiting. About 4 min.

## 6. Load and publish every cycle with its donors

One `fundlens run`, resuming a build from `load`. Without step 3.5, that is the 2026 build. Gold is rebuilt from
every cycle's live build, now resolved:

```bash
# VM, in tmux
export F=2026    # 2024 if step 3.5 rebuilt it
B=$(cat "$F/build-id.txt")
echo "$(date -u +%FT%TZ) start final $F $B" | tee -a final-window.txt
{ time docker exec "$(fl pipeline)" fundlens run --cycle "$F" --build-id "$B" --from load; } 2>&1 | tee final.log
echo "$(date -u +%FT%TZ) end final" | tee -a final-window.txt
mk loaded "$F" "$B" | grep -E '"finished_at"|"duration_s"'
mk published "$F" "$B" | grep -E '"finished_at"|"duration_s"'
```

**Expected:** `build <B> of <F>`, then load's output: a `<table>: <n> rows` line per gold table, `quality:
precision …` with step 5.3's figures (not `quality: not validated …`), a `resolution: release <sha>, <o>
overrides, <a> adjudications applied` line and `loaded build <B> into gold_build …`. Then publish's lines, with
`previous build: <B>`, since the build was live already and only its gold changes. Then the Kuma 404, `extract: skipped, done already`, `transform: skipped, done already`, `resolve: skipped, done already` and
`finished build <B> of <F>: ran load, publish`. The two markers have today's `finished_at`.

## 7. Verify

### 7.1 The API

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq '{build_id, model_version, overrides_count, adjudications_applied, precision, recall, precision_top, recall_top}'
curl -sS "https://api.fundlens.org/v1/cycles?nocache=$(date +%s)" | jq -r '.[] | [.cycle, .race_count, .contribution_count, .total_amount] | @tsv' | tee cycles.tsv
jq -n --rawfile t cycles.tsv '$t | split("\n") | map(select(length > 0) | split("\t")) | {cycles: length, empty: map(select(.[1] == "0" or .[2] == "0" or (.[3] | tonumber) <= 0) | .[0])}'
for c in $(seq 1980 2 2026); do printf '%s ' "$c"; curl -sS "https://api.fundlens.org/v1/cycles/$c/races?nocache=$(date +%s)" | jq '[length, ([.[] | .total_individual + .total_committee] | add)] | @tsv' -r; done | tee races.tsv
```

**Expected:** `/v1/meta` names `<B>` and `<M>` with step 5.3's figures. Then 24 cycles, 2026 first, each with
races, contributions and a total above 0, and `{"cycles": 24, "empty": []}`. Then a line per cycle: its race
count and the sum of its races' money, both above 0. Copy `cycles.tsv` into the Log.

### 7.2 The pages

In a browser, open `https://fundlens.org/cycles/1980`, `/cycles/1990`, `/cycles/2000`, `/cycles/2010`,
`/cycles/2026`, and the cycle list on the home page.

**Expected:** every cycle from 1980 to 2026 is listed. Each page lists races with non-zero totals. Open one race in
1980 and one of its candidates: the candidate page lists top donors, since donors now exist for every cycle.

### 7.3 Signals

- **Bugsink** → `fundlens`: every `pipeline` issue since step 3 comes from a step that failed and was run again
  (step 3.4). Write each in the Log, then resolve it. An `api` issue since step 6 means a route fails on an old
  cycle: file a ticket with it.

## 8. Restore

```bash
# laptop
gh workflow enable dependencies --repo neuroticsasquat-ch/fundlens
gh workflow list --repo neuroticsasquat-ch/fundlens --all
```

**Expected:** `dependencies` listed as `active`. Then:

1. Leave `DUCKDB_MEMORY_LIMIT` at `32GB` in Coolify. Until incremental resolution (NEU-2062), every weekly run does
   step 5's `resolve --full` over every cycle, so it needs whatever step 5 needed. File a ticket in the fundlens v1
   project, related to NEU-2060: set the compose file's `DUCKDB_MEMORY_LIMIT` fallback from the peaks this run
   recorded, then delete the Coolify entry so the fallback is in force again ([coolify-setup.md](coolify-setup.md)
   §6). Name the ticket in the Log.
2. If step 4 lowered SigNoz's retention, set it back.
3. Stop the sampler: `Ctrl-b 1`, `Ctrl-c`, `Ctrl-b 0`.

```bash
# VM
docker exec "$(fl pipeline)" printenv DUCKDB_MEMORY_LIMIT
df -h / | tee disk-after.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null; du -sc /data/fundlens | tail -1' | tee -a disk-after.txt
pg -Atc "select pg_size_pretty(pg_database_size('fundlens')), round(pg_database_size('fundlens') / 1e9, 2)" | tee -a disk-after.txt
docker exec "$CH" du -sh /var/lib/clickhouse | tee -a disk-after.txt
```

**Expected:** `32GB`, then the disk after the backfill: each `/data/fundlens` directory and their total in KB,
the database in GB, and ClickHouse. From here, merging to `main` is safe again.

## 9. Record the run

Gather the rows and the run's figures:

```bash
# VM
cat $(ls -d [12][0-9][0-9][0-9] | sort -n | sed 's|$|/row.md|') > backfill-rows.md
{
  echo "resolve: model $M"
  grep -E '^[0-9]+ contributor keys in|^recluster:|^overrides:|^adjudications:|^crosswalk:|^load [0-9.]+ s,|^DuckDB memory limit|^real' resolve.log
  cycle_peak resolve
  grep -E '^(overall|top)|^matched' validate.txt
  grep -E 'loaded build|published build|^real' final.log
  mk resolved 2026 "$(cat 2026/build-id.txt)" | grep -E '"duration_s"'
} | tee run-record.txt
# 2024's row, from its live build's markers: it was not rebuilt (step 3.5 aside).
docker exec -i "$(fl pipeline)" python - 2024 20261112T211727Z — — "$(free_gb)" — < record.py 2>&1 | grep -v '^{' | tee 2024-row.md
```

```bash
# laptop
mkdir -p ~/fundlens-backfill && cd ~/fundlens-backfill
for f in backfill-rows.md run-record.txt indiv-sizes.txt resolve-inputs.txt disk-before.txt disk-after.txt meta-before.txt cycles.tsv; do scp "hetzner-01:fundlens-backfill/$f" .; done
```

**Expected:** `run-record.txt` holds the model, resolve's summary lines and its `real`, the resolve peak,
validate's figures, the final load and publish lines with their `real`, and the `resolved` marker's
`duration_s`. `2024-row.md` holds 2024's row. The `scp` loop copies eight files into `~/fundlens-backfill`.
One file per `scp`: since OpenSSH 9, `scp` copies over SFTP, which does not expand braces in a remote path.

Then, in one PR, `docs(capacity): record the backfill of every cycle since 1980 (NEU-2060)`:

1. **`capacity.md` → Backfill:** `backfill-rows.md`, one row per cycle, oldest first. Write the step `where` named
   for each peak into the Notes, with any rerun and its reason. Without step 3.5, 2024 has no row of its own:
   put `2024-row.md` in its place, noting that it is the live build of 2026-11-12, not rebuilt here, and that its
   peak is under Per cycle (24.34 GiB, the NEU-2076 row).
2. **`capacity.md` → Resolution:** a row for step 5: date, model `<M>`, `1980–2026 (each cycle's build)`, SHA,
   keys, clusters, the phase times in the column's order, wall time (the `resolved` marker's `duration_s`), the
   peak, the working file's size, and in the Notes the `adjudications` phase time (the column predates it),
   resolve's `real` and the `crosswalk:` line.
3. **`capacity.md` → Per cycle:** a row for step 6's load and publish of every cycle, with load's two halves from
   `loaded build … (aggregates <a> s, copy <c> s)` and gold's size from `disk-after.txt`.
4. **`capacity.md` → Triggers:** replace its placeholder with the check, worked out from the rows:
   - **Weekly run.** Until incremental resolution (NEU-2062), the weekly `fundlens run` of 2026 is
     2026's extract, seats, transform, load and publish plus a `resolve --full` over every cycle. Estimate it as
     2026's extract, seats and transform from its Backfill row, plus step 5's wall time, plus step 6's load and
     publish. Set it against the handover's 6–8 h, and against NEU-2062: incremental resolution leaves only the
     2026 steps.
   - **Steady-state disk.** `/data/fundlens`'s total plus the database, from `disk-after.txt`, against ~300 GB.
     Give ClickHouse's size beside it: it shares the disk, but is not fundlens's.
   - **CPU and memory.** The largest transform peak and resolution's peak, against the 40 GiB container.
   - **Verdict:** which triggers fired, if any. **For each one that fired, file a ticket** in the fundlens v1
     project ("Ephemeral runner: <trigger>"), with the figures, related to NEU-2060, and name it here.
5. **`capacity.md` → Findings:** a bullet for anything the backfill showed that the rows do not say on their own:
   where the memory went, which cycle was largest, how resolution scaled with keys.
6. **This runbook → Log:** an entry headed `### <date> — every cycle, 1980 to 2026 (NEU-2060)`: the SHA, the
   first `LARGER` cycle and step 2's time, step 1.2's checks, every rerun and its reason, step 4's pauses, step
   5's output lines, step 5.3's figures beside `meta-before.txt`'s, `cycles.tsv`, step 8's restore, every
   deviation, and each ticket filed.

Merging it redeploys `pipeline`, which is safe now that nothing is running.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-13 — 1980 rerun after NEU-2281

1980's build `20261113T010657Z` (from `2aa1466`) failed `silver_committee_transfer_recipient.sql` on an 18K
filed by `C00109298`, absent from 1980's `cm`. NEU-2281 (PR #149) fixed it. Every cycle from here on is built
from `ad1447bb7230c7672ff3ef08ae1333434909d0d7`; 1980 reruns under a new build.

### 2026-11-13 — 1994 rerun after NEU-2282

1994's build `20261113T023353Z` (from `ad1447b`) stopped at `load`: `COPY committee, line 16224` refused a NUL
byte (`CharacterNotInRepertoire … 0x00`), the last character of `C00080291`'s `CONNECTED_ORG_NM` in 1994's `cm`.
NEU-2282 (PR #150) drops NUL bytes from FEC bulk text in `copy_as_utf8`. 1980–1992's silver holds no NUL, so they
are not rebuilt. 1994 onward is built from `da1b6f4235ddeb39c89ef12f16f57d41f021e6e7`; 1994 reruns under a new build.

### 2026-11-13 — 1980–1998 rebuilt after NEU-2283

1998's build `20261113T035643Z` (from `da1b6f4`) passed every check, but 11 of its 473 races totalled $0, against
none in 1994 and 1996. `TN-09`, `OR-03` and `NY-18` were missing their incumbents (`H6TN09043`, `H6OR03064`,
`H8NY20056`). FEC's 1998 `cn` lists them with `CAND_ELECTION_YR` 2000, their latest registration, and
`02_candidate.sql` only gave a race to filings for 1997–1998. 25 House incumbents and $14.30M were left out of
1998's races; Senate filings for a later year (about 60 incumbents a cycle) are senators whose seat isn't up, and
correctly have no race. NEU-2283 stands a House filing for the next election marked `I` in this cycle's race. The
fix is in silver, so 1980–1998 are rebuilt from its merge before 2000; each first build's directory is kept as
`<C>-superseded-<B>`.
