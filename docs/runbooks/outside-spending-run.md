# Runbook: the 2024 production run with all outside spending

How to put all of 2024's outside spending live on real data (NEU-2171; every-FEC-dollar spec §6). Transform a new
2024 build with the 24/48-hour file's rows in `independent_expenditure` and the new `electioneering_communication`,
then resolve, load and publish it. Before publishing, check it against FEC three ways:

- the five Senate races of NEU-2162's measurement, every kind per candidate, against its Q13;
- the 14 spenders the by-spender rule adds (its Q6f) and the largest added row, each read against its filing;
- no receipt or spending total moved.

Then check one race page. Run it once, top to bottom, on `music-box-dancer`, one step at a time. Append to the
[Log](#log) at the bottom; never rewrite it.

**Why now.** NEU-2164 to NEU-2170 are merged. Since NEU-2168's reload (2026-11-24 22:05 UTC), live gold shows
2024's communication costs and party coordinated expenditures: they are `pas2` rows v1 already held. It shows no
24/48-hour row and no electioneering communication for 2024. 2024's live build, `20261124T002500Z`, was
transformed before NEU-2165 and NEU-2166, and load reads `electioneering_communication` as having no rows in a build
that lacks it (spec §2, older builds). So a 2024 race page's electioneering figure is a dash, and a Form 5 filer such
as Earthjustice Action spends $0 on its page. Two transform-only 2024 builds were made on 2026-11-24 (NEU-2166,
NEU-2167), but neither was loaded or checked against FEC. This run does both.

**Why nothing is extracted.** 2024's bronze already holds every file the transform reads. The live build read the v1
files as FEC published them on 2026-11-23, and NEU-2166 downloaded the three outside-spending CSVs on 2026-11-24.
§6's measured figures are of those files. A new download would bring FEC's amendments since, and step 7 could not
tell an amendment from a defect, nor step 7.5 a moved receipt from a bug. Step 2 extracts a CSV only if bronze lacks
it.

**Why no `run`.** `fundlens run --from transform` would still run `extract` in full, because this build has no
`extracted` marker. The steps are run one by one, as `run` orders them.

**Not in this runbook:** cycles before 2024 (NEU-2180's backfill), and the dataset snapshot: Sunday's `run
--dataset` takes it.

## Before you start

- NEU-2170 (`f864bb9`, PR #248) is merged, and so is this runbook. Step 1.1 checks that the deployed code includes
  it.
- **Nothing merges to `main` from step 2 until step 9 has printed its last line.** Every merge redeploys
  `pipeline` and kills a running `docker exec`. On 2026-11-02 a docs merge killed a `publish` part way through.
  Step 1.1 turns Dependabot's auto-merge off and lists the open PRs.
- Not within 4 h of Sunday 03:00 UTC: the scheduled `fundlens weekly` task runs then, and two pipeline runs at once
  do not fit the box. Not between 02:00 and 02:30 UTC either: the nightly backup runs then ([weekly.md](weekly.md)
  Facts).
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo, `gh`
  and `jq` are installed, and you can sign in to Bugsink (`https://bugsink.neuroticsasquat.ch`) and Linear.
- Allow about two hours: about 31 min of transform (NEU-2167's run), 7 of resolve and 25 of load (NEU-2160's and
  NEU-2168's), 3 of publish, and the reading in step 7.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycle | `2024` |
| 2024's live build before this run | `20261124T002500Z`: the live build NEU-2162's measurement read, every source file of 2026-11-23 but `oppexp` (2026-11-22). Its `independent_expenditure` holds `pas2` rows alone, and it has no `electioneering_communication` |
| Live gold before this run | `20261123T224142Z`, 2026's live build, loaded and published 2026-11-24 22:05:32 UTC by NEU-2168's close-out, with every outside-spending column and `race_top_spender` |
| The reference transform | `20261124T201924Z`, transform-only on `23d2806` (NEU-2167), never loaded. It read the same bronze this run reads, the three CSVs of 2026-11-24 among it |
| Silver and transform changes since the reference | None: NEU-2168 to NEU-2170 change gold, the API and the pages alone |
| The 24/48-hour rows, as measured (spec §6.3) | NEU-2165 on FEC's files of 2026-11-24: by spender 65 rows, $997,843.85, 13 spenders; timeliness 35 rows, $3,453.50, all FORFACT, LLC (`C90018771`); 100 rows and $1,001,297.35 together, 14 spenders, Q6's figure exactly. Largest added row $90,000 |
| The pas2 kinds, as measured (spec §6.2) | NEU-2167 on the reference: `communication costs 799 rows, $7,157,987.00, 779 with a type; party coordinated 812 rows, $89,161,724.00` |
| Electioneering, as measured (spec §6.4) | NEU-2166 on `20261124T190842Z`: 67 rows, $9,442,373.94, $7,230,615.02 of it reaching a race, 2 copies dropped, 25 spenders |
| The five races | NEU-2162's Q13: `2024-S-OH-00`, `2024-S-PA-00`, `2024-S-MT-00`, `2024-S-MI-00`, `2024-S-WI-00` (`docs/measurements/outside-spending-2024.md`). Ohio and Wisconsin have electioneering communications, and Ohio two spenders the 24/48-hour file adds (Q13d) |
| What Q13 can differ by (spec §6.5) | Only timeliness, at most $28,732 across 2024: none of it is in the five races, since FORFACT's rows are Q6's and the one spender the track record leaves out, Conservative Fighter PAC ($25,278.89), is no Q13 row. The two copies dropped ($38,500) name House candidates. Any other gap is explained in the Log |
| The 14 spenders (Q6f) | `C90022781` Earthjustice Action $293,577, `C90020447` FLIC VOTES INC $207,175, `C90020058` RED WINE AND BLUE $134,695, `C90022567` Somos the Future $90,020, `C90020454` Freedom Action Now Inc. $84,468, `C90022997` PAC for Georgia's Youth $76,999, `C00892117` BEYONDROE.COM POLITICAL FUND $50,000, `C90018391` The Family Foundation Action $33,892, `C90021841` Private Equity Stakeholder Action $11,479, `C90022146` Seattle DSA $7,833, `C90018771` FORFACT LLC $3,454, `C90023094` International Brotherhood of 42 Joint Council $3,021, `C90023003` Herr $2,614, `C90022948` U.S. Veterans for Ukraine Inc. $2,070. All but BEYONDROE.COM are Form 5 filers (`cm` type `I`) |
| Monitors | `fundlens/publish` gets a push from `publish`. If the monitor is still paused, `publish` ends with `kuma push (up) failed: HTTPError: HTTP Error 404: Not Found`: the paused monitor refusing the push, not a fault |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-outside-spending
```

In the tmux session, define the helpers. Paste the whole block:

```bash
# VM, in tmux
mkdir -p ~/fundlens-outside-spending-run && cd ~/fundlens-outside-spending-run
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# A step's completion marker for one 2024 build, or MISSING: `mk <step> <build>`.
mk() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; m = markers.read(sys.argv[1], R2.from_settings(get_settings()), cycle=2024, build_id=sys.argv[2]); print(m.model_dump_json(indent=2) if m else "MISSING")' "$1" "$2"; }
# Each cycle's live build, from markers/live.json.
live() { docker exec "$(fl pipeline)" python -c 'from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; print(markers.read_live(R2.from_settings(get_settings())))'; }
# psql in the fundlens database. `-i`, so a query can come from stdin (`pg < file.sql`).
pg() { docker exec -i "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
# The live gold build and the rollback target, from Postgres.
gmeta() { pg -Atc "select 'gold', build_id, published_at, model_version from gold.meta union all select 'gold_prev', build_id, published_at, model_version from gold_prev.meta"; }
# Free disk on / in decimal GB, as capacity.md counts sizes.
free_gb() { df -BGB --output=avail / | tail -1 | tr -dc '0-9'; }
```

**Expected:** no output. If the tmux session is lost, run `tmux attach -t fundlens-outside-spending`. If the session
itself is gone, paste the helpers again, `cd ~/fundlens-outside-spending-run`, and export what earlier steps saved:
`export OLD=$(cat old-build.txt)` from step 1.2 on and `export B=$(cat build-id.txt)` from step 3 on.

**Scripts.** Each script below is saved to a file with `cat > <name> <<'EOF'` and then run from it, never pasted as
a heredoc into `docker exec`: a long paste into tmux can arrive mangled (NEU-2160's run), and a file arrives whole
or not at all. Check a script arrived whole with `tail -3 <name>` before running it.

## 1. Preflight

### 1.1 The deployed code, and the merge freeze

```bash
# VM
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES DUCKDB_MEMORY_LIMIT
docker exec "$(fl pipeline)" sh -c 'ulimit -Sn'
docker exec "$(fl pipeline)" fundlens health; echo "exit=$?"
docker top "$(fl pipeline)" | grep -E 'fundlens (run|weekly|transform|resolve|load|publish)' || echo "nothing running"
```

```bash
# laptop
cd ~/projects/fundlens
git fetch origin
SHA=$(ssh hetzner-01 'docker exec "$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)" printenv OTEL_RESOURCE_ATTRIBUTES' | sed 's/.*service.version=//; s/,.*//')
echo "$SHA"
git merge-base --is-ancestor f864bb9 "$SHA" && echo "race pages deployed"
git log --oneline 23d2806.."$SHA" -- sql/silver 'sql/checks/silver_*' src/fundlens/transform src/fundlens/fec src/fundlens/resolve
gh workflow disable dependencies --repo neuroticsasquat-ch/fundlens
gh pr list --repo neuroticsasquat-ch/fundlens --state open
```

**Expected:** `service.version=<sha>` and `32GB`; `65536` (NEU-2399); `postgres: ok`, `r2: ok`, `exit=0`; `nothing
running`. Then the SHA, `race pages deployed`, and no commit from `git log`. If the `deployed` line is missing:
Coolify → the `fundlens` resource → *Deploy*, wait for it to finish, and run this step again. A commit from `git log`
means silver changed since the reference transform, so step 4 would blame its differences on the wrong thing: stop
and find out what it changes. Then no output from `gh workflow disable`, and the open PRs: none of them merges until
step 9 is done. Write the SHA in the Log.

### 1.2 The live state

```bash
# VM
gmeta
live
live | grep -o "2024: '[0-9TZ]*'" | grep -o '[0-9]\{8\}T[0-9]\{6\}Z' | tee old-build.txt
export OLD=$(cat old-build.txt)
mk transformed 20261124T201924Z | tee ref-transformed.json | jq '.row_counts | {independent_expenditure, electioneering_communication, contribution}'
mk transformed "$OLD" | tee old-transformed.json | jq '.row_counts | {independent_expenditure, electioneering_communication, contribution}'
pg -Atc "select count(*), count(electioneering), sum(ie_support + ie_oppose) from gold.race where cycle = 2024"
pg -Atc "select committee_id, ie_total, electioneering_total from gold.committee_cycle where cycle = 2024 and committee_id in ('C90022781', 'C30001978') order by committee_id"
docker exec "$(fl pipeline)" python -c 'from fundlens.r2 import R2; from fundlens.resolve import runner; from fundlens.settings import get_settings; s = get_settings(); print("incremental ready" if runner.incremental_ready(R2.from_settings(s), s.data_dir) else "NOT READY")' 2>&1 | grep -v '^{'
free_gb
```

**Expected:**

- `gold` naming `20261123T224142Z`, `published_at` 2026-11-24 22:05 UTC or later, and `gold_prev`. Write both lines
  in the Log: after step 8, `gold` becomes `gold_prev`, the rollback target.
- `markers/live.json` with 2024 at `20261124T002500Z`, and `old-build.txt` holding it. Another build means someone
  published 2024 since the Facts were written: stop, and read [weekly.md](weekly.md)'s and the other runbooks' Logs
  to find out what it is.
- The reference's three counts: its `independent_expenditure`, `electioneering_communication` 67 and its
  `contribution`. `MISSING` (and a `jq` parse error) means a publish pruned the reference: compare against the live
  build alone in step 4, and say so in the Log.
- The live build's: `independent_expenditure` the reference's less 100, `electioneering_communication` `null` and
  the same `contribution`. A `contribution` that differs means the reference read other v1 files than the live
  build: stop, and go to step 1.3.
- 2024's races: `<n>|0|<s>`. `0`: no 2024 race has an electioneering figure yet.
- Earthjustice Action (`C90022781`) with `ie_total` 0.00 and Patriotic Veterans (`C30001978`, an electioneering
  spender in Ohio) with an empty `electioneering_total`. Earthjustice's figure today is `pas2`'s, which holds no
  independent expenditure for it; step 7.5 expects it to become $293,577.
- `incremental ready`, and at least 100 GB free: `transform` can spill up to 60 GB of DuckDB scratch
  (`DUCKDB_MAX_TEMP_DIRECTORY_SIZE`). With less, free some first.

Then what the site serves for Ohio before the run:

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/races/2024/senate/OH?nocache=$(date +%s)" | jq '{outside_spending, outside_spending_total, spenders: (.top_spenders | length), not_committees: [.top_spenders[] | select(.is_committee | not) | .name]}' | tee ~/fundlens-outside-spending-oh-before.json
```

**Expected:** `electioneering_communication: null`, independent expenditures of $99,581,722 for and $207,925,152
against (Q13c's gold), communication costs and party coordinated expenditures already filled, and the top
spenders' non-committee names: Form 5 filers from `pas2`, no electioneering spender and no RED WINE AND BLUE.

### 1.3 Transform will read the live build's v1 files and NEU-2166's CSVs

transform reads the newest bronze download of each file. Set each beside the date the live build read:

```bash
# VM
cat > bronze.py <<'EOF'
import psycopg

from fundlens import paths
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.settings import get_settings

settings = get_settings()
store = R2.from_settings(settings)
with psycopg.connect(settings.database_url) as conn:
    [(dates,)] = conn.execute("SELECT cycles -> '2024' -> 'source_dates' FROM gold.meta").fetchall()
for name in CATALOGUE:
    keys = sorted(store.list_keys(paths.bronze_dir(2024, name)))
    newest = keys[-1].rsplit("/", 1)[1].split(".")[0] if keys else "NONE"
    read = dates.get(name, "none")
    print(f"{name}: newest {newest}, live build read {read}: {'same' if newest == read else 'DIFFERENT'}")
EOF
tail -3 bronze.py
docker exec -i "$(fl pipeline)" python - < bronze.py 2>&1 | grep -v '^{' | tee bronze-before.txt
```

**Expected:** a line per catalogued file. Every v1 file, `committee_summary` and `oppexp` are `same`: 2026-11-23,
and `oppexp` 2026-11-22. `ie_24_48`, `ElectioneeringComm` and `CommunicationCosts` are `newest 2026-11-24, live
build read none: DIFFERENT`: NEU-2166's downloads, which the live build predates. A file with no 2024 source (`newest
NONE, live build read none`) is fine.

- One of the three CSVs `NONE`: step 2 extracts it.
- Any other `DIFFERENT`: someone extracted 2024 since the live build, so transform would read FEC's amendments since
  then, and step 7.5's "no receipt or spending total moved" could not hold. Stop and find out who. `committee_summary`
  is the one most likely: FEC rewrites it daily. It feeds `reported_total`, and so the timeliness rule (spec §6.3:
  "a build reads `committee_summary` and `pas2` of the same extract").

## 2. Extract, only a CSV bronze lacks

Only if step 1.3 listed one of the three CSVs as `NONE`. `F` is its name:

```bash
# VM, in tmux
F=<ie_24_48 | ElectioneeringComm | CommunicationCosts>
docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --file "$F" 2>&1 | grep -v '^{' | tee -a extract.log
```

**Expected:** `<F>: downloaded bronze/cycle=2024/<F>/<today>.csv`, about 19.5 MB, 18 KB and 237 KB for the three
on 2026-11-24. A CSV downloaded today is FEC's file of today, not the one §6 measured: write it in the Log, and read
step 4's lines against §6's figures as within 1%, not exactly. `--file` writes no `extracted` marker, as intended.
With nothing to extract, write "nothing extracted" in the Log.

## 3. Seats

`transform` reads the unmatched filings that `seats --report` records, and `load` reads the `race` partition of the
same build. Fix the build ID here:

```bash
# VM, in tmux
export B=$(date -u +%Y%m%dT%H%M%SZ)
echo "$B" | tee build-id.txt
time docker exec "$(fl pipeline)" fundlens seats --cycle 2024 --report --build-id "$B" 2>&1 | grep -v '^{' | tee seats.log
```

**Expected:** `house: 441 races (0 special)`, `senate: 35 races (2 special)`, `president: 1 races (0 special)`,
`wrote silver/race/cycle=2024/build=<B>/…`, and 49 unmatched filings recorded, as in every 2024 run since
NEU-2324. Under a minute.

## 4. Transform

The raw log is kept: its JSON lines hold the three outside-spending lines and the `memory after <step>` lines, which
the plain output leaves out.

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens transform --cycle 2024 --build-id "$B" 2>&1 | tee transform-raw.log | grep -v '^{' | tee transform.log
mk transformed "$B" | tee transformed.json
for ref in ref old; do echo "against $ref:"; jq -rn --slurpfile o "$ref-transformed.json" --slurpfile n transformed.json '$n[0].row_counts | to_entries[] | select($o[0].row_counts[.key] != .value) | "  \(.key): \($o[0].row_counts[.key] // "none") -> \(.value)"'; done
grep -oE '"message": "(independent_expenditure 2024|electioneering_communication 2024)[^"]*"' transform-raw.log | tee outside-lines.txt
```

**Expected:** a `<table>: <n> rows` line per silver table, then `wrote …` lines and a `transformed` marker. Then the
tables whose row count differs:

```
against ref:
against old:
  independent_expenditure: <n> -> <n + 100>
  electioneering_communication: none -> 67
```

Against the reference, nothing: the same code read the same bronze. Against the live build, the 100 added rows and the
new table. Any other line means transform read other files than both: stop, and go back to step 1.3's list.

Then the three lines, each the Facts' figure:

```
independent_expenditure 2024: 24/48-hour rows added: by spender 65 rows, $997,843.85; timeliness 35 rows, $3,453.50; largest $90,000.00 by <spender> (<file_num>:<tran_id>)
independent_expenditure 2024: communication costs 799 rows, $7,157,987.00, 779 with a type; party coordinated 812 rows, $89,161,724.00
electioneering_communication 2024: 67 rows, $9,442,373.94; $7,230,615.02 reaching a race; disbursements' copies dropped: 2
```

Equal, when step 2 extracted nothing. With a CSV downloaded in step 2, within 1% of each. A largest row above
$1,000,000 is a hoax filing that passed the screen (spec §6.3): it is step 7.2's first row to read. Write the three
lines in the Log.

**Estimated:** about 31 min. A failed check stops the run before anything is uploaded. The traceback names the
`sql/checks/silver_*.sql` file whose query returned rows, and Bugsink gets an issue tagged `pipeline_mode=transform`.
§6 adds `silver_independent_expenditure_no_double.sql`, `silver_independent_expenditure_communication.sql` and the
four `silver_electioneering_communication_*.sql` checks. File a Bug ticket with the check's name and a few of its
rows, link it from NEU-2171, and stop. The live build is untouched.

### 4.1 Memory

```bash
# VM, in tmux
cat > memory.py <<'EOF'
import json
import sys

for line in sys.stdin:
    if line.startswith("{"):
        entry = json.loads(line)
        if entry["message"].startswith("memory after "):
            print(entry["ts"][11:19], entry["message"][13:])
EOF
tail -3 memory.py
# The script goes as an argument, so stdin is free for the log.
docker exec -i "$(fl pipeline)" python -c "$(cat memory.py)" < transform-raw.log | tee memory.txt
tail -1 memory.txt
peak=$(tail -1 memory.txt | grep -o 'peak resident [0-9.]* GiB'); grep -m1 "$peak" memory.txt
grep -E '^[0-9:]+ silver (reported_total|independent_expenditure|electioneering_communication) 2024' memory.txt
```

**Expected:** the last line, the process's peak resident memory over the whole transform: 28.53 GiB on NEU-2160's
run, set in `write contribution 2024`. Within about 2 GiB of it is the run-to-run spread
[capacity.md](../capacity.md) records. Above 29.80 GiB means the transform went past DuckDB's limit and lived on
spill: write it in the Log, and file a ticket against the memory budget. Then the step that set it. Then three
lines: `reported_total`, the model before `independent_expenditure` (it reads `reported_total`), then the two
outside-spending models. DuckDB's figure moves by about 0.01 GiB across `independent_expenditure` and not at all
across `electioneering_communication` (spec §6.2, §6.4). Write the peak, its step and the two models' costs in the
Log.

## 5. Resolve

The new build's contributor keys against the live model, with no training (spec §6.10):

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens resolve --cycle 2024 2>&1 | grep -v '^{' | tee resolve.log
mk resolved "$B" | jq '{step, row_counts, duration_s}'
```

**Expected:**

```
2024: build <B>
0 new contributor keys of <k>, 0 returning to the working file, 0 pairs scored at or above the match threshold
…
crosswalk: 0 new donors, 0 keys re-pointed, 0 redirects
…
```

`0 new contributor keys`: transform read the live build's `indiv`, so every key is in the crosswalk already. New keys
mean transform read other files: stop, and go back to step 1.3. A `warning: … keys that stood were re-pointed` line
means an override or verdict new since the last `--full`: the run can go on, but write it in the Log and do
[weekly.md](weekly.md)'s re-resolving with `--full` afterwards. Then a `resolved` marker for `<B>`. About 7 min.

If it stops with exit 1 and a message, [weekly.md](weekly.md)'s *A run missed* says what each one means.

## 6. Load

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens load --cycle 2024 --build-id "$B" 2>&1 | grep -v '^{' | tee load.log
mk loaded "$B" | jq '{step, duration_s}'
```

**Expected:** a `<table>: <n> rows` line per gold table, `race_top_spender` above NEU-2168's 98,511 (the 24/48-hour
rows and electioneering communications add lines to 2024's races). Then `quality: precision …`, a `resolution:
release <sha>, <o> overrides, <a> adjudications applied` line, and `loaded build <B> into gold_build (aggregates <a>
s, copy <c> s)`. That last line means every `sql/checks/gold_*.sql` passed, §6.5's among them
(`gold_outside_spending_total.sql`, `gold_race_totals.sql`, `gold_race_top_spender_amount.sql`,
`gold_rank_contiguous.sql`). A failed check leaves no `gold_build` and names the check: file a Bug ticket with its
rows, link it from NEU-2171, and stop. Then a `loaded` marker. About 25 min: a load rebuilds gold from every cycle's
live build, this cycle's from `<B>`.

## 7. Check the figures before publishing

Both builds are in Postgres now: `gold` is the live gold and `gold_build` is `<B>`. Nothing is live yet.

### 7.1 The rows the 24/48-hour file added

`added.py` reads the build's silver: every row with `source_file = 'ie_24_48'`, with its spender and the spender's
reported figure. It takes the build and a mode: `spenders` lists them, `filings` reads each against its filing
(step 7.2).

```bash
# VM, in tmux
cat > added.py <<'EOF'
import csv
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal

from fundlens import paths
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform import runner

build, mode = sys.argv[1], sys.argv[2]
settings = get_settings()
store = R2.from_settings(settings)


def parquet(table):
    """The build's 2024 partition of a silver table, downloaded first where the volume lacks it."""
    prefix = paths.silver_partition(table, 2024, build)
    for key in store.list_keys(prefix + "/"):
        local = paths.local_path(settings.data_dir, key)
        if not local.exists():
            store.download_to(key, local)
    files = paths.local_path(settings.data_dir, prefix) / "**" / "*.parquet"
    return f"read_parquet({runner.literal(files)}, hive_partitioning = false)"


con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
# A row dated after its spender's period end is timeliness's; every other one the by-spender rule's
# (10_independent_expenditure.sql). Its key is <file_num>:<tran_id>.
con.execute(
    "CREATE TEMP TABLE added AS SELECT ie.*, c.name, c.type, r.independent_expenditures AS reported_ie,"
    " r.period_end, CASE WHEN ie.date > r.period_end THEN 'timeliness' ELSE 'by_spender' END AS rule,"
    " split_part(ie.source_record_id, ':', 1) AS file_num,"
    " substr(ie.source_record_id, strpos(ie.source_record_id, ':') + 1) AS tran_id"
    f" FROM {parquet('independent_expenditure')} AS ie JOIN {parquet('committee')} AS c USING (committee_id)"
    f" LEFT JOIN {parquet('reported_total')} AS r USING (committee_id) WHERE ie.source_file = 'ie_24_48'"
)
if mode == "spenders":
    con.sql("SELECT rule, count(*) AS rows, count(DISTINCT committee_id) AS spenders, sum(amount) AS dollars,"
            " sum(amount) FILTER (WHERE race_id IS NOT NULL) AS reaching_a_race FROM added GROUP BY ALL"
            " ORDER BY rule").show(max_width=250)
    con.sql("SELECT committee_id, name, type, count(*) AS rows, sum(amount) AS dollars, any_value(reported_ie)"
            " AS reported_ie, any_value(period_end) AS period_end, string_agg(DISTINCT rule, ', ') AS rule,"
            " sum(amount) FILTER (WHERE race_id IS NOT NULL) AS reaching_a_race,"
            " string_agg(DISTINCT race_id, ', ') AS races FROM added GROUP BY committee_id, name, type"
            " ORDER BY dollars DESC, committee_id").show(max_width=250, max_rows=100)
    con.sql("SELECT committee_id, name, amount, date, candidate_id, race_id, support_oppose, payee_name, purpose,"
            " source_record_id FROM added ORDER BY amount DESC, source_record_id LIMIT 1").show(max_width=250)
    sys.exit()


def number(field):
    """A field of the filing as a number, or None: an amount is matched by value, not spelling."""
    try:
        return Decimal(field.strip().strip('"'))
    except ArithmeticError:
        return None


rows = con.execute("SELECT committee_id, name, file_num, tran_id, amount, date, candidate_id, support_oppose,"
                   " payee_name, purpose FROM added ORDER BY amount DESC, file_num, tran_id").fetchall()
filings, failures = {}, {}
for committee, name, file_num, tran_id, amount, date, candidate, side, payee, purpose in rows:
    if file_num not in filings:
        request = urllib.request.Request(f"https://docquery.fec.gov/dcdev/posted/{file_num}.fec",
                                         headers={"User-Agent": "fundlens-runbook"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                text = response.read().decode("latin-1")
            # Split on newlines alone: str.splitlines() also breaks on \x1c, the fields' separator.
            filings[file_num] = [line.split("\x1c") if "\x1c" in line else next(csv.reader([line]))
                                 for line in text.replace("\r", "").split("\n") if line.strip()]
        except (urllib.error.URLError, TimeoutError) as error:
            filings[file_num] = []
            failures[file_num] = str(error)
        time.sleep(1)
    records = filings[file_num]
    # The record after the header is the form: F24N/F24A or F5N/F5A, the filer's id, then the report's fields.
    if file_num in failures:
        filer, form = "not read", f"FETCH FAILED {failures[file_num]}"
    elif len(records) > 1:
        filer = "the spender's" if records[1][1].strip() == committee else "NOT THE SPENDER'S"
        form = " | ".join(f.strip() for f in records[1][:12] if f.strip())
    else:
        filer, form = "not read", "no form line"
    line = next((r for r in records if tran_id in (f.strip().strip('"') for f in r)), None)
    on_line = line is not None and any(number(f) == amount for f in line)
    print(f"{committee} {name} | silver ${amount:,} {date} {candidate} {side} | {payee} | {purpose}")
    print(f"  filing {file_num}, {filer}: {form}")
    print(f"  page https://docquery.fec.gov/cgi-bin/forms/{committee}/{file_num}/")
    shown = "NOT FOUND" if line is None else " | ".join(f.strip().strip('"') for f in line if f.strip().strip('"'))
    print(f"  line {tran_id}: {shown}")
    print(f"  amount on the line: {'yes' if on_line else 'NO'}")
EOF
tail -3 added.py
docker exec -i "$(fl pipeline)" python - "$B" spenders < added.py 2>&1 | grep -v '^{' | tee added-spenders.txt
```

**Expected,** in a minute or two (the first read downloads the three partitions):

1. Two rules. `by_spender`: 65 rows, 13 spenders, $997,843.85. `timeliness`: 35 rows, 1 spender, $3,453.50.
   Together $1,001,297.35 (Facts), of which Q6e's $251,224 reaches a race.
2. The 14 spenders of the Facts, each with Q6f's dollars, rounded to the dollar, and a reported figure above $0.
   FORFACT LLC is `timeliness`, its period ending 2024-09-30. RED WINE AND BLUE and Private Equity Stakeholder Action
   reach `2024-S-OH-00` (Q13d). A spender not in the Facts' list, or one missing, is a difference from Q6f: write it in
   the Log, and read its rows in step 7.2 before anything else.
3. The largest row: step 4's `largest`, $90,000.

Copy all three into the Log.

### 7.2 Each added row against its filing

The 100 rows, largest first, each beside its line in FEC's raw filing (`docquery.fec.gov/dcdev/posted/<file_num>.fec`).
About two minutes: one request a second, one per filing.

```bash
# VM, in tmux
docker exec -i "$(fl pipeline)" python - "$B" filings < added.py 2>&1 | grep -v '^{' | tee added-filings.txt
grep -c "NOT THE SPENDER'S" added-filings.txt; grep -c 'NOT FOUND' added-filings.txt; grep -c 'amount on the line: NO' added-filings.txt
grep '^  filing ' added-filings.txt | sort -u
```

**Expected:** five lines per row: silver's row; the filing, `the spender's`, and its form line; its FEC page; the
filing's line with that transaction id; and `amount on the line: yes`. Then `0`, `0` and `0`. Then each filing once
with its form line: `F24N` or `F24A` (a committee's 24- or 48-hour report, its third field `24` or `48`) or `F5N` or
`F5A` (a Form 5 filer's), then the filer's id, then the report's fields. For the shape alone: Senate Leadership
Fund's `1821585`, a 48-hour report no added row is on (`pas2` holds SLF's spending, so none of its rows is added),
reads `F24N | C00571703 | 48 | Senate Leadership Fund | …`, and its line `SE | C00571703 | SE.1 | … | MAIN STREET
MEDIA GROUP | … | 6668132.16 | … | TV/MEDIA PLACEMENT | O | S6OH00163 | BROWN | …`.

Read each spender's rows against its filing, the largest row first, and write a line per spender in the Log:

- **Real:** the filing is the spender's own, a 24/48-hour report or a Form 5, and each line names a payee and a
  purpose a real ad buy reads as (media, digital, mail, canvassing), with the amount silver holds. Open the FEC page
  link for the largest row and for any line the raw text leaves unclear. A web-form id (`tran_id` beginning `WFT`)
  decides nothing either way: real spenders file on the web form too (spec §6.3).
- **A hoax that passed the screen:** an implausible payee or purpose, or a spender's rows far beyond its reported
  figure (step 7.1 sets the two side by side; the screen allows ten times). File a Bug ticket with the rows, link it
  from NEU-2171, and stop before `publish`: the screen let one through (spec §6.3).
- **`NOT THE SPENDER'S`:** the 24/48-hour file names a filing another filer made. FEC's file is wrong, or the
  model read `file_num` from the wrong column: open the FEC page, and if the filing is the other filer's, a Bug ticket,
  linked from NEU-2171, and stop.
- **`NOT FOUND` or `amount on the line: NO`:** open the FEC page. A line FEC's raw file writes differently (a
  rounded amount, a transaction id quoted another way) is explained; write how. A line the filing lacks is a defect in
  the model or the file: a Bug ticket, linked from NEU-2171, and stop.

A filing listed as `not read: FETCH FAILED <error>` was not served: its rows are `NOT FOUND` because nothing was
read, not because the filing lacks them, and `grep -c 'not read' added-filings.txt` counts them. One `404` is a
filing docquery has not posted: open its FEC page. Every filing `HTTP Error 403` or a timeout means docquery
refused the container's address. Fetch them from the laptop instead, one at a time, the filing number and
transaction id from each row's `filing` and `line` lines in `added-filings.txt`: `curl -sS
https://docquery.fec.gov/dcdev/posted/<file_num>.fec | tr '\034' '|' | grep '<tran_id>'`, and read them the same way.

### 7.3 The five races against Q13

Gold's figures per candidate and kind, against Q13b's, the 24/48-hour rows it adds included (Q13's "added"
column, here in the independent expenditures). A column is equal within $1: Q13 writes whole dollars, and a 24/48-hour
row and an electioneering share carry cents.

```bash
# VM
cat > five-races.sql <<'EOF'
\pset footer off
-- Q13b, per candidate: gold IE + added for and against, communication costs for and against,
-- coordinated, electioneering shares (docs/measurements/outside-spending-2024.md).
create temp table q13 (race_id text, candidate_id text, ie_for numeric, ie_against numeric,
    cc_for numeric, cc_against numeric, coordinated numeric, electioneering numeric);
insert into q13 values
    ('2024-S-OH-00', 'S4OH00192', 68907148, 85641445, 36268, 1145, 1928697, 29500),
    ('2024-S-OH-00', 'S6OH00163', 24404163, 115071732, 151189, 16, 2276000, 0),
    ('2024-S-OH-00', 'S4OH00200', 3248966, 4033491, 0, 0, 0, 63000),
    ('2024-S-OH-00', 'S2OH00477', 3129765, 3178484, 0, 0, 0, 0),
    ('2024-S-PA-00', 'S6PA00217', 19668493, 104734969, 342203, 54, 2550018, 0),
    ('2024-S-PA-00', 'S2PA00661', 29236814, 78108081, 0, 5320, 2458625, 0),
    ('2024-S-MT-00', 'S4MT00183', 18563194, 63515395, 36268, 0, 219972, 0),
    ('2024-S-MT-00', 'S6MT00162', 16589898, 63314407, 50144, 38, 246304, 0),
    ('2024-S-MT-00', 'S8MT00234', 0, 114297, 0, 0, 0, 0),
    ('2024-S-MT-00', 'S4MT00225', 0, 44346, 0, 0, 0, 0),
    ('2024-S-MI-00', 'S4MI00470', 23942099, 53991590, 5210, 0, 1959000, 0),
    ('2024-S-MI-00', 'S4MI00595', 24273884, 39084085, 0, 7918, 1589974, 0),
    ('2024-S-MI-00', 'S4MI00694', 473608, 0, 0, 0, 0, 0),
    ('2024-S-MI-00', 'S4MI00553', 27848, 0, 0, 0, 0, 0),
    ('2024-S-WI-00', 'S2WI00268', 10105634, 50324227, 0, 1139, 1098871, 0),
    ('2024-S-WI-00', 'S2WI00219', 8392337, 51061401, 53715, 0, 1139501, 42000);
-- Q13c, per race, with Q13b's added in the independent expenditures; electioneering NULL where
-- none of the race's candidates has a row.
create temp table q13_race (race_id text, ie_for numeric, ie_against numeric, cc numeric,
    coordinated numeric, electioneering numeric);
insert into q13_race values
    ('2024-S-OH-00', 99690042, 207925152, 188618, 4204697, 92500),
    ('2024-S-PA-00', 48905307, 182843050, 347577, 5008643, null),
    ('2024-S-MT-00', 35153092, 126988445, 86450, 466276, null),
    ('2024-S-MI-00', 48717439, 93075675, 13128, 3548974, null),
    ('2024-S-WI-00', 18497971, 101385628, 54854, 2238372, 42000);

\echo 'Per candidate: gold_build, every kind'
select rc.race_id, rc.candidate_id, rc.name, rc.ie_support, rc.ie_oppose, rc.communication_cost_support,
    rc.communication_cost_oppose, rc.party_coordinated, rc.electioneering
from gold_build.race_candidate rc
where rc.race_id in (select race_id from q13_race)
    and (rc.candidate_id in (select candidate_id from q13) or rc.ie_support <> 0 or rc.ie_oppose <> 0
        or rc.communication_cost_support <> 0 or rc.communication_cost_oppose <> 0
        or rc.party_coordinated <> 0 or coalesce(rc.electioneering, 0) <> 0)
order by rc.race_id, rc.ie_support + rc.ie_oppose desc;

\echo 'Per candidate: gold_build less Q13, where a kind differs by $1 or more'
with d as (
    select q.race_id, q.candidate_id, rc.name,
        rc.ie_support - q.ie_for as ie_for, rc.ie_oppose - q.ie_against as ie_against,
        rc.communication_cost_support - q.cc_for as cc_for,
        rc.communication_cost_oppose - q.cc_against as cc_against,
        rc.party_coordinated - q.coordinated as coordinated,
        coalesce(rc.electioneering, 0) - q.electioneering as electioneering
    from q13 q left join gold_build.race_candidate rc using (race_id, candidate_id))
select * from d
where name is null or greatest(abs(ie_for), abs(ie_against), abs(cc_for), abs(cc_against), abs(coordinated),
    abs(electioneering)) >= 1
order by race_id, candidate_id;

\echo 'Per race: gold_build, and gold_build less Q13'
select r.race_id, r.ie_support, r.ie_oppose, r.communication_cost_support + r.communication_cost_oppose as cc,
    r.party_coordinated, r.electioneering, r.outside_spending_total,
    r.ie_support - q.ie_for as d_ie_for, r.ie_oppose - q.ie_against as d_ie_against,
    r.communication_cost_support + r.communication_cost_oppose - q.cc as d_cc,
    r.party_coordinated - q.coordinated as d_coordinated,
    case when (r.electioneering is null) = (q.electioneering is null)
        then coalesce(r.electioneering - q.electioneering, 0) end as d_electioneering,
    r.outside_spending_total - (q.ie_for + q.ie_against + q.cc + q.coordinated + coalesce(q.electioneering, 0))
        as d_total
from q13_race q left join gold_build.race r using (race_id)
order by r.ie_support + r.ie_oppose desc;
EOF
tail -3 five-races.sql
pg < five-races.sql | tee five-races.txt
```

**Expected:**

1. **Per candidate:** the 16 candidates of Q13b, each with every kind, and no other candidate. Ohio's Brown has
   independent expenditures for of $24,404,163: Q13b's $24,295,843 and the $108,320 RED WINE AND BLUE and Private
   Equity Stakeholder Action added. Moreno, LaRose and Baldwin have electioneering figures, $29,500, $63,000 and
   $42,000. Every other candidate's electioneering figure is empty: no row names them.
2. **The differences:** no row. A row with an empty `name` is a Q13 candidate gold no longer has in the race: a
   defect in the race's candidates, a Bug ticket.
3. **Per race:** the five races, the differences all 0 (within $1), and `d_electioneering` 0 for all five: a figure
   where Q13 has one and empty where it has none. An empty `d_electioneering` means one of the two has a figure and
   the other none.

Any difference is explained in the Log before publishing. Spec §6.5 allows timeliness alone, and none of it is in
these races (Facts). Read a difference this way:

- **Independent expenditures, by the cents of an added row.** Under $1: equal.
- **Independent expenditures, by more:** list the race's rows on both sides with `source_file`, from the build's
  silver, and find the rows that are not in Q13. `pas2` rows are v1's, so a difference there means transform read
  another `pas2` (step 1.3). An added row means the 24/48-hour rule added a row Q6 did not, or the other way round:
  set it against step 7.1's spenders.
- **Electioneering:** Q13 counts every row of the file, and the contract drops a disbursement's copies (spec §6.4).
  The two copies of 2024 name House candidates, so a Senate difference is no copy: a Bug ticket.
- **Communication costs or party coordinated:** these are `pas2` rows v1 already held, unchanged since the
  measurement. A difference means transform read another `pas2` (step 1.3) or the gold columns are wrong: a Bug ticket.

Copy the three tables into the Log.

### 7.4 The non-committee spenders on the five races

```bash
# VM
cat > not-committees.sql <<'EOF'
\pset footer off
\echo 'Kinds among each race''s top spenders'
select race_id, kind, count(*) as lines, sum(amount) as amount
from gold_build.race_top_spender
where race_id in ('2024-S-OH-00', '2024-S-PA-00', '2024-S-MT-00', '2024-S-MI-00', '2024-S-WI-00')
group by race_id, kind order by race_id, kind;
\echo 'Non-committee spenders among them (committee.type I, C or E)'
select t.race_id, t.rank, t.committee_id, t.name, c.type, t.candidate_id, t.kind, t.support_oppose, t.amount
from gold_build.race_top_spender t join gold_build.committee c using (committee_id)
where t.race_id in ('2024-S-OH-00', '2024-S-PA-00', '2024-S-MT-00', '2024-S-MI-00', '2024-S-WI-00')
    and c.type in ('I', 'C', 'E')
order by t.race_id, t.rank;
EOF
tail -3 not-committees.sql
pg < not-committees.sql | tee not-committees.txt
```

**Expected:** each race's top-spender lines by kind. Ohio and Wisconsin each have all four kinds, if the
electioneering lines are large enough for the top 100: Ohio's are $63,000 and $29,500, and Wisconsin's $42,000.
Then the non-committee spenders that made the top 100: Form 5 filers (`I`) such as WORKING AMERICA (Q13d), the
electioneering spenders (`E`) PATRIOTIC VETERANS, INC, AMERICAN RESOLVE PAC INC. and AMERICANS FOR PHARMA REFORM
INC., and in Ohio RED WINE AND BLUE, the 24/48-hour file's, if its $96,841 on Brown makes the top 100 of a $312M
race.

**The page for step 9.2:** Ohio, `https://fundlens.org/race/2024/senate/OH`, when its top spenders hold all four
kinds and a non-committee spender. Otherwise Wisconsin, `https://fundlens.org/race/2024/senate/WI`, if it does. Either
page shows all four kinds in its candidates' table whatever the top 100 holds: that table is the race's figures. If
neither race's top spenders holds a non-committee spender, the ticket's second check cannot pass on these races: write
it in the Log and ask on NEU-2171 which page to check instead. Write the race chosen in the Log.

### 7.5 No receipt or spending total moved

The build changes outside spending alone. Every receipt and spending figure, in every cycle, should be the live
gold's:

```bash
# VM
cat > moved.sql <<'EOF'
\pset footer off
\echo 'Receipt and spending figures that differ between gold and gold_build, every cycle'
select 'committee_cycle' as tbl,
    count(*) filter (where o.committee_id is null or n.committee_id is null) as missing,
    count(*) filter (where row(o.total_individual, o.self_funding, o.total_from_committees,
        o.total_from_organizations, o.total_non_contribution_account, o.total_other_lines, o.total_refunds,
        o.total_to_candidates, o.total_returned_by_candidates, o.total_operating_expenditures, o.itemized_total,
        o.reported_receipts, o.reported_disbursements, o.reported_independent_expenditures)
        is distinct from row(n.total_individual, n.self_funding, n.total_from_committees,
        n.total_from_organizations, n.total_non_contribution_account, n.total_other_lines, n.total_refunds,
        n.total_to_candidates, n.total_returned_by_candidates, n.total_operating_expenditures, n.itemized_total,
        n.reported_receipts, n.reported_disbursements, n.reported_independent_expenditures)) as moved
from gold.committee_cycle o full join gold_build.committee_cycle n using (committee_id, cycle)
union all
select 'candidate_cycle',
    count(*) filter (where o.candidate_id is null or n.candidate_id is null),
    count(*) filter (where row(o.total_individual, o.total_committee, o.total_jfc_transfers, o.self_funding,
        o.total_operating_expenditures, o.itemized_total, o.reported_receipts)
        is distinct from row(n.total_individual, n.total_committee, n.total_jfc_transfers, n.self_funding,
        n.total_operating_expenditures, n.itemized_total, n.reported_receipts))
from gold.candidate_cycle o full join gold_build.candidate_cycle n using (candidate_id, cycle)
union all
select 'race',
    count(*) filter (where o.race_id is null or n.race_id is null),
    count(*) filter (where row(o.total_individual, o.total_committee, o.total_jfc_transfers,
        o.total_operating_expenditures) is distinct from row(n.total_individual, n.total_committee,
        n.total_jfc_transfers, n.total_operating_expenditures))
from gold.race o full join gold_build.race n using (race_id)
union all
select 'cycle',
    count(*) filter (where o.cycle is null or n.cycle is null),
    count(*) filter (where row(o.race_count, o.contribution_count, o.total_amount)
        is distinct from row(n.race_count, n.contribution_count, n.total_amount))
from gold.cycle o full join gold_build.cycle n using (cycle);

\echo 'What did move: committees'' outside spending, by cycle'
select cycle,
    count(*) filter (where o.ie_total is distinct from n.ie_total) as ie_moved,
    sum(n.ie_total - o.ie_total) as ie_change,
    count(*) filter (where row(o.communication_cost_total, o.party_coordinated_total)
        is distinct from row(n.communication_cost_total, n.party_coordinated_total)) as pas2_kinds_moved,
    count(n.electioneering_total) as electioneering_committees, sum(n.electioneering_total) as electioneering
from gold.committee_cycle o join gold_build.committee_cycle n using (committee_id, cycle)
group by cycle
having count(*) filter (where o.outside_spending_total is distinct from n.outside_spending_total) > 0
order by cycle;

\echo 'What did move: candidates'' outside spending, 2024'
select count(*) filter (where row(o.ie_support, o.ie_oppose) is distinct from row(n.ie_support, n.ie_oppose))
        as ie_moved,
    sum(n.ie_support + n.ie_oppose - o.ie_support - o.ie_oppose) as ie_change,
    count(n.electioneering) as electioneering_candidates, sum(n.electioneering) as electioneering
from gold.candidate_cycle o join gold_build.candidate_cycle n using (candidate_id, cycle)
where cycle = 2024;
EOF
tail -3 moved.sql
pg < moved.sql | tee moved.txt
```

**Expected:**

1. Four rows, `committee_cycle`, `candidate_cycle`, `race` and `cycle`, each `missing` 0 and `moved` 0. This is
   the ticket's "no receipt or spending total moved", in every cycle: load rebuilt every other cycle from the same
   live builds, and 2024's v1 tables are the live build's (step 4). A `missing` above 0 means the two builds'
   committees, candidates or races differ. A `moved` above 0 means a v1 table differs. Neither is explained by
   anything since the live build: stop, and file a Bug ticket with the rows (`select … where … is distinct from …`).
2. One row, 2024: `ie_moved` 14 and `ie_change` $1,001,297.35, the 14 spenders and their added rows. `pas2_kinds_moved`
   0: communication costs and party coordinated were live already. `electioneering_committees` 25 and `electioneering`
   $9,442,373.94, the 25 electioneering spenders (Q9a). Another cycle listed means load read another build of it: stop.
3. Candidates: how many moved and by how much, about $251,224: Q6e's added dollars that name a candidate, every one
   of them in a race, less the $85 row with no side. Then the candidates with an electioneering figure and their
   sum, $7,230,615.02: NEU-2166's dollars reaching a candidate and a race, the table's $9,442,373.94 less the rows
   that name no candidate (about $2,179,759) and the one naming an id `cn` lacks ($32,000) (spec §6.4).

Write all three outputs in the Log.

## 8. Publish

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens publish --cycle 2024 --build-id "$B" 2>&1 | grep -v '^{' | tee publish.log
mk published "$B" | jq '{step, duration_s}'
gmeta
live
pg -Atc "select count(*), count(electioneering) from gold.race where cycle = 2024"
```

**Expected:** `published build <B> of 2024`, `previous build: 20261124T002500Z`, `cloudflare purge: done`,
`wrote resolution/build=<B>/crosswalk.parquet` and `pruned <n> silver builds (<m> objects)`. Prune removes only
builds older than `20261124T002500Z`: never the live build, nor the one before it, nor NEU-2166's and NEU-2167's
hand transforms, which are newer. Then a Kuma line (Facts). Then:

- a `published` marker;
- `gold` naming `<B>`, `published_at` now; `gold_prev` the `gold` line of step 1.2;
- `markers/live.json` with 2024 at `<B>`, every other cycle as in step 1.2;
- 2024's races, and how many have an electioneering figure: a handful, those whose candidates an electioneering row
  names. Ohio and Wisconsin are among them.

About 3 min: the purge waits 75 s after the swap on purpose. The merge freeze holds until step 9 is done.

**If a check in step 9 fails.** Roll back:

```bash
# VM
docker exec "$(fl pipeline)" fundlens publish --rollback
```

**Expected:** `rolled back: build <step 1.2's gold> is live`, then `build <B> is now gold_prev`. 2024 shows no
24/48-hour row and no electioneering communication again, as before the run. File a Bug ticket with the failed
check's output and link it from NEU-2171. Nothing runs on `pipeline` after a rollback, so end the merge freeze as
step 9.3 does: `gh workflow enable dependencies --repo neuroticsasquat-ch/fundlens` on the laptop.

## 9. Verify

### 9.1 The API serves the build

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/meta?nocache=$(date +%s)" | jq '{build_id, published_at, model_version}'
curl -sS "https://api.fundlens.org/v1/races/2024/senate/OH?nocache=$(date +%s)" | jq '{outside_spending, outside_spending_total, kinds: ([.top_spenders[].kind] | unique), not_committees: [.top_spenders[] | select(.is_committee | not) | {rank, name, kind, support_oppose, amount}]}' | tee ~/fundlens-outside-spending-oh-after.json
curl -sS "https://api.fundlens.org/v1/committees/C90020058/independent-expenditures?cycle=2024&nocache=$(date +%s)" | jq '{rows: (.expenditures | length), from_24_48: [.expenditures[] | select(.source_file == "ie_24_48") | {source_record_id, date, amount, candidate_id, support_oppose, payee_name, purpose}]}'
```

**Expected:** `build_id` `<B>`, `published_at` now. Then Ohio: `independent_expenditure` $99,690,042 for and
$207,925,152 against, communication costs $188,618 across both sides, `party_coordinated` $4,204,697,
`electioneering_communication` $92,500, and `outside_spending_total` $312,101,009 (step 7.3's Ohio row, within $1).
Then the kinds among its top spenders and its non-committee spenders, as step 7.4 listed them. Then RED WINE AND
BLUE's list: its five 24/48-hour rows, each with a payee and a purpose, three of them on Brown (`S6OH00163`), for.
Copy the Ohio block into the Log, beside step 1.2's.

### 9.2 The page

Open step 7.4's page in a browser, `https://fundlens.org/race/2024/senate/OH` unless it chose Wisconsin.

**Expected:** an **Outside spending** section whose candidates' table has a column for each of the four kinds:
*Independent expenditures* for and against, *Communication costs* for and against, *Party coordinated expenditures*
and *Electioneering communications*, the last with step 7.3's figures for the candidates an electioneering communication names and a dash
for the rest. Below it, **Top outside spenders**, with a non-committee spender marked **Not a committee** and the
note under the table saying what that is. This is the ticket's definition of done. A page with no electioneering
column is served from an old cache: reload with the cache bypassed (Shift-reload) once. If it still has none, go back
to step 9.1.

Then click RED WINE AND BLUE (or open `https://fundlens.org/committee/C90020058`) and choose 2024.

**Expected:** its independent expenditures listed, each 24/48-hour row marked **24/48-hour estimate**. Write what
both pages show in the Log.

### 9.3 Signals

- **Bugsink** → `fundlens`: no new `pipeline` issue since step 3, and no new `api` issue since step 8. A `pipeline`
  issue is from a step that crashed and was run again: note it in the Log, then resolve it. An `api` issue after the
  publish means a route reads something gold does not have: read it before anything else.

Nothing runs on `pipeline` after this, so merging to `main` is safe again:

```bash
# laptop
gh workflow enable dependencies --repo neuroticsasquat-ch/fundlens
```

**Expected:** no output; Dependabot's auto-merge runs on its schedule again.

## 10. Record the run

Gather the run's identifiers and step times in one file:

```bash
# VM
{
  date -u +%Y-%m-%d
  docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES | sed 's/.*service.version=/sha /; s/,.*//'
  echo "live before $OLD"
  echo "build $B"
  cat extract.log 2>/dev/null || echo "nothing extracted"
  for s in transformed resolved loaded published; do mk "$s" "$B" | grep -E '"step"|"duration_s"'; done | paste - - | tr -d ' ,"'
  cat outside-lines.txt
  tail -1 memory.txt
  grep -E 'new contributor keys|^crosswalk:' resolve.log
  grep -E '^race_top_spender: |^loaded build' load.log
  free_gb
} | tee run-record.txt
```

One `scp` per file: since OpenSSH 9, `scp` copies over SFTP, which does not expand braces in a remote path.

```bash
# laptop
mkdir -p ~/fundlens-outside-spending-run
cd ~/fundlens-outside-spending-run
for f in run-record.txt bronze-before.txt transformed.json memory.txt added-spenders.txt added-filings.txt five-races.txt not-committees.txt moved.txt; do scp "hetzner-01:fundlens-outside-spending-run/$f" .; done
```

**Expected:** `run-record.txt` holds the date, the SHA, the two builds, what step 2 extracted, four `step:<name>`
lines with their `duration_s`, step 4's three lines, the last memory line, resolve's two lines, load's
`race_top_spender` and last lines, and the free disk. The other files are the output of steps 1.3, 4 and 7.

Append a Log entry from them, headed `### <date> — 2024 with all outside spending (NEU-2171)`:

- the date, the SHA, build `<B>` (live before: `20261124T002500Z`), `seats`' `real`, the four marker step times,
  what step 2 extracted, and step 1.2's `gold` and `gold_prev` lines;
- step 4's three lines and the tables whose row count moved;
- step 4.1's peak, the step that set it, and the three models' memory lines;
- step 5's `new contributor keys` and `crosswalk:` lines;
- step 7.1's rules, its 14 spenders set beside Q6f, and the largest added row;
- step 7.2: a line per spender, real or not, with its filings, and the largest row's reading;
- step 7.3's three tables, with every difference explained;
- step 7.4's kinds and non-committee spenders, and the page chosen;
- step 7.5's three outputs;
- steps 9.1 and 9.2: Ohio before and after, RED WINE AND BLUE's 24/48-hour rows, and what both pages showed;
- every deviation, each filed as a ticket and linked from NEU-2171.

In the same PR:

- **`docs/capacity.md`:** a Per cycle row for `<B>`: its date and SHA; `—` for Extract s (or step 2's `real`, if it
  extracted) and `seats`' `real` as Seats s; transform, load and publish from their markers, load as `<total>
  (<aggregates> + <copy>)` from load's last line; and as peak the process's peak resident memory from step 4.1. Its
  note: "First published 2024 build with the 24/48-hour file's rows and `electioneering_communication` (NEU-2171).
  The peak <y> GiB, set in <step>; the outside-spending models moved DuckDB's figure by <x> GiB."
- **`docs/specs/fundlens-every-fec-dollar-project-spec.md` §6.5:** the paragraph **The five races** gains what step
  7.3 found, citing this Log: "Measured by NEU-2171 on 2024's first published build with all outside spending
  (`<B>`): <every kind equal for all 16 candidates | the differences and why>."

Open one PR, `docs(runbooks): log the 2024 outside spending run (NEU-2171)`, with the entry. Merging it redeploys
`pipeline`, which is safe now that nothing is running.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-25 — 2024 with all outside spending (NEU-2171)

Run 2026-11-25 01:23 to 16:00 UTC, on `2edb19ea0b824854ae80c29c6e4a7ca2e3903cb3`. Build `20261125T021311Z`; live
before: `20261124T002500Z`. Before the run, `gold` was
`20261123T224142Z|2026-11-24 22:05:32.456171+00|20261116T224205Z` and `gold_prev`
`20261124T002500Z|2026-11-24 01:25:08.541796+00|20261116T224205Z`. After publish, `gold_prev` is
`20261123T224142Z`. Seats (§3) waited for the nightly backup, which had ended by 02:13 UTC.

**Bronze (step 1.3).** Nothing was extracted. The v1 files were the live build's: `cm`, `cn`, `ccl`, `indiv`,
`pas2`, `oth`, `weball`, `webk` and `committee_summary` of 2026-11-23, and `oppexp` of 2026-11-22, each `same`. The
three CSVs, `ie_24_48`, `ElectioneeringComm` and `CommunicationCosts`, were already in bronze from 2026-11-24 and
had been read by no live build.

| Step | Time | Notes |
| --- | ---: | --- |
| extract | — | nothing extracted |
| seats | 5.2 s | 441 House, 35 Senate (2 special), 1 presidential race; 49 unmatched filings |
| transform | 1800.4 s (30m0s) | against the reference `20261124T201924Z`, no table moved; against the live build, `independent_expenditure` 75,452 → 75,552 and `electioneering_communication` none → 67 |
| resolve | 418.2 s (7m3s) | `0 new contributor keys of 5504649`; crosswalk 0 new donors, 0 re-pointed, 0 redirects |
| load | 1370.3 s (22m56s) | aggregates 679.67 s, copy 664.48 s; every gold check passed; `race_top_spender` 98,518 rows (NEU-2168: 98,511) |
| publish | 143.9 s (2m38s) | pruned 1 silver build (268 objects); 177 GB free after it |

**Step 4's three lines:**

- `independent_expenditure 2024: 24/48-hour rows added: by spender 65 rows, $997,843.85; timeliness 35 rows,
  $3,453.50; largest $90,000.00 by C90020447 (1845232:F57.000001)`
- `independent_expenditure 2024: communication costs 799 rows, $7,157,987.00, 779 with a type; party coordinated
  812 rows, $89,161,724.00`
- `electioneering_communication 2024: 67 rows, $9,442,373.94; $7,230,615.02 reaching a race; disbursements'
  copies dropped: 2`

**Memory (step 4.1).** Peak resident 28.73 GiB, set in `write contribution 2024`, where DuckDB first spilled
(0.90 GiB): 1.07 GiB under DuckDB's 29.80 GiB limit, and 0.20 GiB over NEU-2160's 28.53 GiB, inside the run-to-run
spread. The three models' lines:

- `silver reported_total 2024`: DuckDB 19.43 GiB;
- `silver independent_expenditure 2024`: DuckDB 19.44 GiB (+0.01);
- `silver electioneering_communication 2024`: DuckDB 20.13 GiB. The +0.69 GiB is `operating_expenditure`'s, which
  runs between them (`silver operating_expenditure 2024`: 20.13 GiB; NEU-2160: 0.69 GiB). The electioneering model
  itself moved DuckDB by 0.00 GiB.

**Step 7.1, the 24/48-hour rows by rule and spender.** `by_spender` 65 rows, 13 spenders, $997,843.85 ($247,770.66
reaching a race); `timeliness` 35 rows, 1 spender, $3,453.50 (all reaching a race). The 14 spenders are Q6f's,
each at Q6f's dollars:

| Id | Spender | Type | Rows | Dollars | Q6f | Reported IE | Period end | Rule | Race |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| C90022781 | EARTHJUSTICE ACTION | I | 18 | 293,576.92 | 293,577 | 293,576.96 | 2024-12-31 | by_spender | — |
| C90020447 | FLIC VOTES INC. | I | 8 | 207,175.03 | 207,175 | 209,322.19 | 2024-12-31 | by_spender | — |
| C90020058 | RED WINE AND BLUE | I | 5 | 134,694.99 | 134,695 | 134,694.99 | 2024-12-31 | by_spender | 2024-S-OH-00 ($96,841.23) |
| C90022567 | SOMOS THE FUTURE | I | 5 | 90,020.33 | 90,020 | 90,020.31 | 2024-12-31 | by_spender | 2024-P-US-00 |
| C90020454 | FREEDOM ACTION NOW INC. | I | 5 | 84,468.19 | 84,468 | 84,695.65 | 2024-12-31 | by_spender | — |
| C90022997 | PAC FOR GEORGIA'S YOUTH | I | 2 | 76,999.29 | 76,999 | 76,999.29 | 2024-12-31 | by_spender | — |
| C00892117 | BEYONDROE.COM POLITICAL FUND | O | 3 | 50,000.00 | 50,000 | 59,792.00 | 2024-12-31 | by_spender | — |
| C90018391 | THE FAMILY FOUNDATION ACTION | I | 7 | 33,892.12 | 33,892 | 6,900.32 | 2024-12-31 | by_spender | 2024-H-VA-07 |
| C90021841 | PRIVATE EQUITY STAKEHOLDER ACTION | I | 6 | 11,479.00 | 11,479 | 11,479.00 | 2024-11-05 | by_spender | 2024-S-OH-00 |
| C90022146 | SEATTLE DSA | I | 3 | 7,832.99 | 7,833 | 15,362.62 | 2024-03-31 | by_spender | 2024-P-US-00 |
| C90018771 | FORFACT, LLC | I | 35 | 3,453.50 | 3,454 | 759.00 | 2024-09-30 | timeliness | 2024-P-US-00 |
| C90023094 | INTERNATIONAL BROTHERHOOD OF 42 JOINT COUNCIL | I | 1 | 3,020.85 | 3,021 | 3,020.85 | 2024-12-31 | by_spender | 2024-P-US-00 |
| C90023003 | HERR, STEVEN | I | 1 | 2,614.14 | 2,614 | 2,614.14 | 2024-11-11 | by_spender | 2024-P-US-00 |
| C90022948 | U.S. VETERANS FOR UKRAINE INC. | I | 1 | 2,070.00 | 2,070 | 7,120.00 | 2024-12-31 | by_spender | 2024-P-US-00 |

PRIVATE EQUITY STAKEHOLDER ACTION files as FINANCIAL SERVICES STAKEHOLDER ACTION NFP. The largest added row is
FLIC VOTES INC.'s $90,000.00 of 2024-10-30, against Trump with no candidate id, to Imaginart Media Productions for
`Haitian Radio`, `1845232:F57.000001`: step 4's line named the same row.

**Step 7.2, each row against its filing.** 100 rows read from 33 filings on docquery: `NOT THE SPENDER'S` 0, `NOT
FOUND` 0, `amount on the line: NO` 0, `not read` 0. Every filing was the spender's own: 30 Form 5s (`F5N`) and
BEYONDROE.COM's three 24-hour reports (`F24N`, third field `24`). The largest row's line reads `F57 | C90020447 |
F57.000001 | ORG | Imaginart Media Productions | 17814 SW 47th St | Miramar | FL | 33029 | G2024 | 20241030 |
90000.00 | .00 | Haitian Radio | 004 | O | TRUMP | DONALD | P`. Every spender is real:

- **FLIC VOTES** (6 filings): Haitian radio, canvassing for Mucarsel-Powell (Hard Knocks Strategies), billboards
  (Outfront), radio (iHeartMedia), Meta and Vibe Stream ads, robocalls (Stones' Phones). The lines carry no
  candidate id, so no row reaches a race.
- **EARTHJUSTICE ACTION:** mailers (Pendulum Creative Group), phone banking (Stones' Phones), message targeting
  (Sedgwick Group) and its own staff time, for Harris, Casey, Brown and Slotkin, against Trump and McCormick. No
  candidate ids.
- **RED WINE AND BLUE:** Google, Meta and ViralGains digital ads for Brown with `S6OH00163` ($96,841.23, the three
  rows reaching Ohio); two Katz Audio digital lines for Brown without an id ($37,853.76, no race).
- **SOMOS THE FUTURE:** mail (NEON Strategies), phone banking, yard signs and handouts (COPAL), for Harris. COPAL's
  lines carry Biden's id `P80000722` beside Harris's name. Silver holds Harris's `P00009423`, as the 24/48-hour file
  reads them.
- **FREEDOM ACTION NOW:** mailers and postcards against Trump in Wisconsin (Staples Direct Mail), digital ads
  (Bedrock Media).
- **PAC FOR GEORGIA'S YOUTH:** Moxie Media mailers, for Harris and against Trump.
- **BEYONDROE.COM POLITICAL FUND:** $50,000 of advertising (Winton Campaign Associates, Innonde, Inspiration
  Strategies) opposing South Dakota's Amendment G, a state ballot measure, not a federal candidate: the candidate
  fields read `amend g`. Real and as filed, and it reaches no race. Nothing is filed: FEC's own reported figure
  ($59,792) includes it.
- **THE FAMILY FOUNDATION ACTION:** digital ads and texts against Vindman (`H4VA07234`, Winning Republican
  Strategies) and door-knockers paid for Derrick Anderson (`H2VA07170`), VA-07. Its rows are 4.9 times its
  reported $6,900.32, inside the screen's 10 times, and every line is ordinary field or digital spending.
- **PRIVATE EQUITY STAKEHOLDER ACTION:** web ads for Brown (Speakeasy Political, Ross Turner Design), and four
  lines of $42–$104 to individuals at the spender's own address, purpose `web advertisement`. Small, and its rows
  equal its reported $11,479.
- **SEATTLE DSA:** text and phone banking paid to Democratic Socialists of America, against Biden, March 2024
  (`P2024`).
- **FORFACT, LLC** (3 filings, `timeliness`): 35 Facebook ad lines of $1.58–$222.30, for Harris and against Trump.
  One, $85.29 on 2024-10-28, has no support or oppose mark.
- **INTERNATIONAL BROTHERHOOD OF 42 JOINT COUNCIL:** Harris campaign buttons (A to Z Printing). **HERR, STEVEN:**
  billboards for Harris (Lamar). **U.S. VETERANS FOR UKRAINE:** a newspaper ad against Trump (Gannett).

**Step 7.3, the five races against Q13: equal.** Per candidate: Q13b's 16 candidates and no other. Brown's
independent expenditures for him are $24,404,163.23, Q13b's $24,295,843 plus the $108,320 the 24/48-hour file adds.
Electioneering: Moreno $29,500, LaRose $63,000 and Baldwin $42,000, and no other candidate. The per-candidate
differences table has no row. Per race:

| Race | IE for | IE against | Communication costs | Party coordinated | Electioneering | Total | Difference from Q13 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2024-S-OH-00 | 99,690,042.23 | 207,925,152.00 | 188,618.00 | 4,204,697.00 | 92,500.00 | 312,101,009.23 | `d_ie_for` 0.23, every other 0 |
| 2024-S-PA-00 | 48,905,307.00 | 182,843,050.00 | 347,577.00 | 5,008,643.00 | — | 237,104,577.00 | 0 |
| 2024-S-MT-00 | 35,153,092.00 | 126,988,445.00 | 86,450.00 | 466,276.00 | — | 162,694,263.00 | 0 |
| 2024-S-MI-00 | 48,717,439.00 | 93,075,675.00 | 13,128.00 | 3,548,974.00 | — | 145,355,216.00 | 0 |
| 2024-S-WI-00 | 18,497,971.00 | 101,385,628.00 | 54,854.00 | 2,238,372.00 | 42,000.00 | 122,218,825.00 | 0 |

Ohio's $0.23 is the cents of RED WINE AND BLUE's $49,341.23 Google row: Q13's figures are whole dollars.

**Step 7.4, kinds and non-committee spenders.** The top 100 lines by kind:

| Race | Independent expenditure | Communication cost | Party coordinated | Electioneering | Non-committee lines |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024-S-OH-00 | 93 | 3 | 2 | 2 | 15 |
| 2024-S-WI-00 | 91 | 5 | 3 | 1 | 21 |
| 2024-S-PA-00 | 92 | 6 | 2 | 0 | 13 |
| 2024-S-MT-00 | 95 | 3 | 2 | 0 | 11 |
| 2024-S-MI-00 | 96 | 2 | 2 | 0 | 12 |

Ohio held 12 non-committee lines before the run and 15 after. The three new ones are RED WINE AND BLUE (`I`, #67,
$96,841.23 for Brown), PATRIOTIC VETERANS, INC (`E`, #76, $63,000 of electioneering naming LaRose) and AMERICAN
RESOLVE PAC INC. (`E`, #90, $29,500 naming Moreno). In Wisconsin, AMERICANS FOR PHARMA REFORM INC. (`E`, #57,
$42,000 naming Baldwin). WORKING AMERICA (`I`) is in all five. **The page: Ohio.**

**Step 7.5, nothing else moved.**

- `committee_cycle`, `candidate_cycle`, `race`, `cycle`: each `missing` 0, `moved` 0.
- Committees, one row: `2024 | ie_moved 14 | ie_change 1001297.35 | pas2_kinds_moved 0 |
  electioneering_committees 25 | electioneering 9442373.94`.
- Candidates: `ie_moved 6 | ie_change 251138.87 | electioneering_candidates 12 | electioneering 7230615.02`. The
  candidates' `ie_change` is $85.29 under the $251,224.16 the added rows reaching a race sum to: FORFACT's row with
  no support or oppose mark reaches the race but counts for no candidate and against none.

**Steps 9.1 and 9.2.**

- `/v1/meta` served `20261125T021311Z`, published 2026-11-25 15:35:30 UTC, model `20261116T224205Z`. `gold.race`
  2024: 477 races, 8 with an electioneering figure.
- Ohio, before and after:

  | | Before (`20261124T002500Z`) | After (`20261125T021311Z`) |
  | --- | ---: | ---: |
  | IE for | 99,581,722 | 99,690,042.23 |
  | IE against | 207,925,152 | 207,925,152 |
  | Communication costs, for / against | 187,457 / 1,161 | 187,457 / 1,161 |
  | Party coordinated | 4,204,697 | 4,204,697 |
  | Electioneering | none | 92,500 |
  | Total | 311,900,189 | 312,101,009.23 |
  | Non-committee lines in the top 100 | 12 | 15 |

- RED WINE AND BLUE's 24/48-hour rows from the API: `1837129:F57.000001` Meta $30,000, `…000002` Google
  $49,341.23 and `…000003` ViralGains $17,500, each for Brown (`S6OH00163`), `Estimated Cost for Digital
  Advertising`; `1848329:F57.000001` Katz Audio $19,667.31 and `…000002` $18,186.45, for, no candidate, `Digital
  Advertising`.
- `https://fundlens.org/race/2024/senate/OH` showed the Outside spending table with all four kinds and Top outside
  spenders with Not a committee rows.
- `https://fundlens.org/committee/C90020058?cycle=2024` listed the five rows, each marked `24/48-HOUR ESTIMATE`.
- Bugsink: nothing new. Publish logged no Kuma line: `heartbeat.py` logs only a failed push.

**Deviations, none filed.**

- Dependabot's workflow was re-enabled at 02:14 UTC and disabled again before the transform started. Nothing
  merged.
- At step 9.3 `gh workflow enable dependencies` failed twice, HTTP 500 then 502, during a GitHub incident with
  Actions degraded. It was enabled from the Actions page at about 16:00 UTC.
- The runbook's step 7.5 expected the candidates' `ie_change` at about $251,224. The measured $251,138.87 is
  explained above.
