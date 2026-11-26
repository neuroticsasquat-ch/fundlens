# Runbook: the 2024 production run with leadership PACs and lobbyist bundling

How to put 2024's leadership PACs, lobbyist/registrant PACs and lobbyist bundling live on real data (NEU-2179;
every-FEC-dollar spec §7). Transform a new 2024 build with the three new silver tables, `leadership_pac`,
`lobbyist_pac` and `bundling_report`, then resolve, load and publish it. Before publishing, check it against
NEU-2173's measurement (`docs/measurements/leadership-lobbyist-2024.md` Q13) three ways:

- the ten leadership PACs of Q13a, each with its sponsor, and Eye of the Tiger, a PAC whose sponsor the file leaves
  blank and the list fills (Scalise);
- five recipients' 2024 bundled totals (Q13b), and the cycle's total within 1% of Q10a's $57,262,231;
- no receipt total moved.

Then check a House leader's candidate page. Run it once, top to bottom, on `music-box-dancer`, one step at a time.
Append to the [Log](#log) at the bottom; never rewrite it.

**Why now.** NEU-2174 to NEU-2178 are merged. Since NEU-2177's reload (2026-11-26 18:17 UTC), live gold has §7.7's
columns on `committee_cycle`, and the API and pages read them. They are empty: no live build holds the three
tables, so every sponsor is NULL, every lobbyist flag false and every `bundled_total` NULL ("no reports on this
build"). A candidate page links no leadership PAC. 2024's live build, `20261125T021311Z`, was transformed before
NEU-2175. NEU-2175's hand transform of 2024 (`20261126T011839Z`) holds the tables and matched the measurement, but
was never loaded or checked against FEC. This run does both. Cycles other than 2024 keep reading as having no rows
until NEU-2180's backfill.

**Why nothing is extracted.** 2024's bronze already holds every file the transform reads. The live build read the v1
files as FEC published them on 2026-11-23 and the three outside-spending CSVs of 2026-11-24, and NEU-2174 downloaded
`leadership`, `lobbyist` and `lobbyist_bundle` on 2026-11-25. §7's figures and Q13 are of those files. A new download
would bring FEC's amendments since: Form 3L reports are amended years late (spec §7.5), so step 7.2 could not tell an
amendment from a defect, nor step 7.3 a moved receipt from a bug. Step 2 extracts a file only if bronze lacks it.

**Why no `run`.** `fundlens run --from transform` would still run `extract` in full, because this build has no
`extracted` marker. The steps are run one by one, as `run` orders them.

**Not in this runbook:** cycles before 2024 (NEU-2180's backfill), and the dataset snapshot: Sunday's `run
--dataset` takes it.

## Before you start

- NEU-2178 (`b0788a3`, PR #259) is merged, and so is this runbook. Step 1.1 checks that the deployed code includes
  it.
- **Nothing merges to `main` from step 3 until step 9 has printed its last line.** Every merge redeploys
  `pipeline` and kills a running `docker exec`. On 2026-11-02 a docs merge killed a `publish` part way through.
  Step 1.1 turns Dependabot's auto-merge off and lists the open PRs.
- Not within 4 h of Sunday 03:00 UTC: the scheduled `fundlens weekly` task runs then, and two pipeline runs at once
  do not fit the box. Steps 3 to 8 take about an hour and a half: start step 3 by 00:15 UTC or after 02:30 UTC, so
  none of them runs during the nightly backup, 02:00 to 02:30 UTC ([weekly.md](weekly.md) Facts). NEU-2175's
  transform ran into it and took 52 min against NEU-2171's 30.
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo, `gh`
  and `jq` are installed, and you can sign in to Bugsink (`https://bugsink.neuroticsasquat.ch`) and Linear.
- Allow about two hours: about 30 min of transform (NEU-2171's run), 7 of resolve and 23 of load (NEU-2171's), 3
  of publish, and the reading in step 7.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycle | `2024` |
| 2024's live build before this run | `20261125T021311Z` (NEU-2171): every v1 file of 2026-11-23 but `oppexp` (2026-11-22), and the three outside-spending CSVs of 2026-11-24. It has none of the three tables |
| Live gold before this run | `20261123T224142Z`, 2026's live build, loaded and published 2026-11-26 18:17:41 UTC by NEU-2177's close-out, with §7.7's columns |
| The reference transform | `20261126T011839Z`, transform-only (NEU-2175), never loaded. It read the same bronze this run reads, `leadership`, `lobbyist` and `lobbyist_bundle` of 2026-11-25 among it |
| Silver and transform changes since the reference | None: NEU-2176 to NEU-2178 change gold, the API and the pages alone |
| The three tables, as measured (spec §7.3, §7.5) | NEU-2175 on the reference: `leadership_pac` 833 rows, 460 with a sponsor by the rule, 324 by the list, 49 with none, 6 designated `D` the file lacks; `lobbyist_pac` 1,461 rows; `bundling_report` 317 rows, 6 superseded, bundled total $57,262,231.23 at 84 recipients |
| Leadership PACs in 2024 | 839, every one designated `D` in `cm`: the file's 833 are all `D`, and 6 `D` committees are not in the file (Q2a). So `is_leadership_pac` moves for no committee: live gold already reads `D` |
| The ten (Q13a) | 2024's ten leadership PACs with the largest receipts and a sponsor the rule matches: `C00271338` AmeriPAC (Hoyer, `H2MD05155`), `C00344234` PAC to the Future (Pelosi, `H8CA05035`), `C00807412` Hellfire PAC (Hunt, `H0TX07170`), `C00685552` Medicare for All (Jayapal, `H6WA07458`), `C00841148` Great American Comeback (DeSantis, `P40013039`), `C00617803` JEFF PAC (Jeffries, `H2NY10092`), `C00574970` Fair Shot PAC (Clark, `H4MA05084`), `C00416131` Midwest Values PAC (Franken, `S8MN00438`), `C00387464` Alamo PAC (Cornyn, `S2TX00106`), `C00872804` Defend Freedom (Gabbard, `H2HI02508`). Each agrees with OpenFEC by id; Alamo PAC only by rung 2, last name and first given name |
| The list-linked one | `C00467431` The Eye of the Tiger PAC: the file leaves its sponsor blank, and `leadership_sponsors.csv`'s 2024 row names `SCALISE, STEVE MR`, `H0LA01087` (spec §7.4) |
| The five recipients (Q13b) | 2024's five largest bundled totals: `C00867937` Trump 47 Committee $10,293,939, `C00042366` DSCC $9,841,143, `C00744946` Harris Victory Fund $9,699,650 (the bundling file names it Biden Victory Fund), `C00000935` DCCC $8,104,058, `C00842336` Bell for Missouri $3,167,971 |
| The page for step 9.2 | Jeffries, `https://fundlens.org/candidate/H2NY10092`: a House leader whose PAC the rule links |
| Monitors | `fundlens/publish` gets a push from `publish`. `heartbeat.py` logs only a failed push, as a JSON warning that step 8's `grep -v '^{'` drops, so the plain output shows no Kuma line either way (NEU-2171's Log). `grep 'kuma push' publish-raw.log` finds a failure; `kuma push (up) failed: HTTPError: HTTP Error 404: Not Found` is a paused monitor refusing the push, not a fault |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-leadership
```

In the tmux session, define the helpers. Paste the whole block:

```bash
# VM, in tmux
mkdir -p ~/fundlens-leadership-run && cd ~/fundlens-leadership-run
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

**Expected:** no output. If the tmux session is lost, run `tmux attach -t fundlens-leadership`. If the session
itself is gone, paste the helpers again, `cd ~/fundlens-leadership-run`, and export what earlier steps saved:
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
git merge-base --is-ancestor b0788a3 "$SHA" && echo "pages deployed"
git log --oneline 86f4afa.."$SHA" -- sql/silver 'sql/checks/silver_*' src/fundlens/transform src/fundlens/fec src/fundlens/resolve
gh workflow disable dependencies --repo neuroticsasquat-ch/fundlens
gh pr list --repo neuroticsasquat-ch/fundlens --state open
```

**Expected:** `service.version=<sha>` and `32GB`; `65536` (NEU-2399); `postgres: ok`, `r2: ok`, `exit=0`; `nothing
running`. Then the SHA, `pages deployed`, and no commit from `git log`: `86f4afa` is NEU-2175's merge, the code the
reference was transformed on. If the `deployed` line is missing: Coolify → the `fundlens` resource → *Deploy*, wait
for it to finish, and run this step again. A commit from `git log` means silver changed since the reference
transform, so step 4 would blame its differences on the wrong thing: stop and find out what it changes. Then no
output from `gh workflow disable`, and the open PRs: none of them merges until step 9 is done. Write the SHA in the
Log.

### 1.2 The live state

```bash
# VM
gmeta
live
live | grep -o "2024: '[0-9TZ]*'" | grep -o '[0-9]\{8\}T[0-9]\{6\}Z' | tee old-build.txt
export OLD=$(cat old-build.txt)
mk transformed 20261126T011839Z | tee ref-transformed.json | jq '.row_counts | {leadership_pac, lobbyist_pac, bundling_report, contribution}'
mk transformed "$OLD" | tee old-transformed.json | jq '.row_counts | {leadership_pac, lobbyist_pac, bundling_report, contribution}'
pg -Atc "select count(*) filter (where is_leadership_pac), count(sponsor_candidate_id), count(*) filter (where is_lobbyist_pac), count(bundled_total) from gold.committee_cycle where cycle = 2024"
docker exec "$(fl pipeline)" python -c 'from fundlens.r2 import R2; from fundlens.resolve import runner; from fundlens.settings import get_settings; s = get_settings(); print("incremental ready" if runner.incremental_ready(R2.from_settings(s), s.data_dir) else "NOT READY")' 2>&1 | grep -v '^{'
free_gb
```

**Expected:**

- `gold` naming `20261123T224142Z`, `published_at` 2026-11-26 18:17 UTC or later, and `gold_prev`. Write both lines
  in the Log: after step 8, `gold` becomes `gold_prev`, the rollback target.
- `markers/live.json` with 2024 at `20261125T021311Z`, and `old-build.txt` holding it. Another build means someone
  published 2024 since the Facts were written: stop, and read [weekly.md](weekly.md)'s and the other runbooks' Logs
  to find out what it is.
- The reference's four counts: `leadership_pac` 833, `lobbyist_pac` 1461, `bundling_report` 317, and its
  `contribution`. `MISSING` (and a `jq` parse error) means a publish pruned the reference: compare against the live
  build alone in step 4, and say so in the Log.
- The live build's: the three `null` and the same `contribution`. A `contribution` that differs means the reference
  read other v1 files than the live build: stop, and go to step 1.3.
- 2024's committees in live gold: `839|0|0|0`. 839 leadership PACs, all by designation `D` (Facts); no sponsor, no
  lobbyist/registrant PAC and no bundled total, since the live build has none of the tables.
- `incremental ready`, and at least 100 GB free: `transform` can spill up to 60 GB of DuckDB scratch
  (`DUCKDB_MAX_TEMP_DIRECTORY_SIZE`). With less, free some first.

Then what the site serves before the run:

```bash
# laptop
curl -sSL "https://api.fundlens.org/v1/candidates/H2NY10092?nocache=$(date +%s)" | jq -c '{name, leadership_pacs}' | tee ~/fundlens-leadership-jeffries-before.json
curl -sS "https://api.fundlens.org/v1/committees/C00867937?nocache=$(date +%s)" | jq -c '.cycles[] | select(.cycle == 2024) | {is_leadership_pac, sponsor, is_lobbyist_pac, bundled_total}'
```

**Expected:** Jeffries with `leadership_pacs: []`, and Trump 47 Committee's 2024 with `is_leadership_pac: false`,
`sponsor: null`, `is_lobbyist_pac: false` and `bundled_total: null`.

### 1.3 Transform will read the live build's files and NEU-2174's CSVs

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

**Expected:** a line per catalogued file. Every v1 file, `committee_summary`, `oppexp`, `ie_24_48`,
`ElectioneeringComm` and `CommunicationCosts` are `same`: 2026-11-23, `oppexp` 2026-11-22 and the three
outside-spending CSVs 2026-11-24. `leadership`, `lobbyist` and `lobbyist_bundle` are `newest 2026-11-25, live build
read none: DIFFERENT`: NEU-2174's downloads, which the live build predates. A file with no 2024 source (`newest
NONE, live build read none`) is fine.

- One of the three new files `NONE`: step 2 extracts it.
- Any other `DIFFERENT`: someone extracted 2024 since the live build, so transform would read FEC's amendments since
  then, and step 7.3's "no receipt total moved" could not hold. Stop and find out who. `committee_summary` is the one
  most likely: FEC rewrites it daily.

## 2. Extract, only a file bronze lacks

Only if step 1.3 listed `leadership`, `lobbyist` or `lobbyist_bundle` as `NONE`. `F` is its name:

```bash
# VM, in tmux
F=<leadership | lobbyist | lobbyist_bundle>
docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --file "$F" 2>&1 | grep -v '^{' | tee -a extract.log
```

**Expected:** `<F>: downloaded bronze/cycle=2024/<F>/<today>.csv`. A file downloaded today is FEC's file of today,
not the one §7 measured: write it in the Log, and read step 4's lines and step 7.2's figures against §7's as within
1%, not exactly. `--file` writes no `extracted` marker, as intended. With nothing to extract, write "nothing
extracted" in the Log.

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

The raw log is kept: its JSON lines hold the three tables' lines and the `memory after <step>` lines, which the
plain output leaves out.

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens transform --cycle 2024 --build-id "$B" 2>&1 | tee transform-raw.log | grep -v '^{' | tee transform.log
mk transformed "$B" | tee transformed.json
for ref in ref old; do echo "against $ref:"; jq -rn --slurpfile o "$ref-transformed.json" --slurpfile n transformed.json '$n[0].row_counts | to_entries[] | select($o[0].row_counts[.key] != .value) | "  \(.key): \($o[0].row_counts[.key] // "none") -> \(.value)"'; done
grep -oE '"message": "(leadership_pac|lobbyist_pac|bundling_report) 2024:[^"]*"' transform-raw.log | tee leadership-lines.txt
```

**Expected:** a `<table>: <n> rows` line per silver table, then `wrote …` lines and a `transformed` marker. Then the
tables whose row count differs:

```
against ref:
against old:
  leadership_pac: none -> 833
  lobbyist_pac: none -> 1461
  bundling_report: none -> 317
```

Against the reference, nothing: the same code read the same bronze. Against the live build, the three new tables.
Any other line means transform read other files than both: stop, and go back to step 1.3's list. If step 1.2 found
the reference `MISSING`, `against ref:` prints a `jq` parse error instead: read `against old:` alone.

Then the three lines, each the Facts' figure:

```
leadership_pac 2024: 833 leadership PACs, sponsor by the rule 460, by the list 324, neither 49; 6 designated D the file lacks
lobbyist_pac 2024: 1,461 lobbyist/registrant PACs
bundling_report 2024: 317 reports, 6 superseded; bundled total $57,262,231.23 at 84 recipients
```

Equal, when step 2 extracted nothing. With a file downloaded in step 2, within 1% of each. Write the three lines in
the Log.

**Estimated:** about 30 min. A failed check stops the run before anything is uploaded. The traceback names the
`sql/checks/silver_*.sql` file whose query returned rows, and Bugsink gets an issue tagged `pipeline_mode=transform`.
§7 adds `silver_leadership_pac_*.sql` (committee, key, sponsor), `silver_lobbyist_pac_*.sql` (committee, key) and
`silver_bundling_report_*.sql` (committee, key, not counted, total). File a Bug ticket with the check's name and a
few of its rows, link it from NEU-2179, and stop. The live build is untouched.

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
grep -E '^[0-9:]+ silver (electioneering_communication|leadership_pac|lobbyist_pac|bundling_report) 2024' memory.txt
```

**Expected:** the last line, the process's peak resident memory over the whole transform: 28.73 GiB on NEU-2171's
run, set in `write contribution 2024`. Within about 2 GiB of it is the run-to-run spread
[capacity.md](../capacity.md) records. Above 29.80 GiB means the transform went past DuckDB's limit and lived on
spill: write it in the Log, and file a ticket against the memory budget. Then the step that set it. Then four lines:
`electioneering_communication`, the model before the three, then the three. DuckDB's figure moves by about 0.01 GiB
across them: NEU-2175 measured 20.12 GiB after `electioneering_communication` and 20.13 GiB after `bundling_report`
(spec §7.6). Write the peak, its step and the three models' cost in the Log.

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

`0 new contributor keys` (of 5504649 on NEU-2171's run): transform read the live build's `indiv`, so every key is in
the crosswalk already. New keys mean transform read other files: stop, and go back to step 1.3. A `warning: … keys
that stood were re-pointed` line means an override or verdict new since the last `--full`: the run can go on, but
write it in the Log and do [weekly.md](weekly.md)'s re-resolving with `--full` afterwards. Then a `resolved` marker
for `<B>`. About 7 min.

If it stops with exit 1 and a message, [weekly.md](weekly.md)'s *A run missed* says what each one means.

## 6. Load

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens load --cycle 2024 --build-id "$B" 2>&1 | grep -v '^{' | tee load.log
mk loaded "$B" | jq '{step, duration_s}'
```

**Expected:** a `<table>: <n> rows` line per gold table, `committee_cycle` with the live gold's row count (step 7.3
compares them). Then `quality: precision …`, a `resolution: release <sha>, <o> overrides, <a> adjudications
applied` line, and `loaded build <B> into gold_build (aggregates <a> s, copy <c> s)`. That last line means every
`sql/checks/gold_*.sql` passed, §7.7's among them (`gold_committee_cycle_bundled_total.sql`: each `bundled_total`
equals its silver sum, 0 or NULL as each cycle's build holds the table; `gold_committee_cycle_sponsor.sql`: every
sponsored committee is a leadership PAC, and every sponsor id a candidate fundlens holds). A failed check leaves no
`gold_build` and names the check: file a Bug ticket with its rows, link it from NEU-2179, and stop. Then a `loaded`
marker. About 23 min: a load rebuilds gold from every cycle's live build, this cycle's from `<B>`. Every other
cycle's build lacks the three tables and reads as having none of their rows (spec §7.9).

## 7. Check the figures before publishing

Both builds are in Postgres now: `gold` is the live gold and `gold_build` is `<B>`. Nothing is live yet.

### 7.1 The ten leadership PACs and the list-linked one

First the build's silver `leadership_pac`, where `sponsor_source` says what linked each sponsor; gold does not carry
it. `sponsors.py` reads the build's partition:

```bash
# VM, in tmux
cat > sponsors.py <<'EOF'
import sys

from fundlens import paths
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform import runner

build = sys.argv[1]
settings = get_settings()
store = R2.from_settings(settings)
# Q13a's ten (docs/measurements/leadership-lobbyist-2024.md) and Eye of the Tiger, the list's.
ELEVEN = ("C00271338", "C00344234", "C00807412", "C00685552", "C00841148", "C00617803", "C00574970",
          "C00416131", "C00387464", "C00872804", "C00467431")


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
con.execute(f"CREATE TEMP TABLE lp AS SELECT * FROM {parquet('leadership_pac')}")
con.sql("SELECT sponsor_source, count(*) AS pacs, count(sponsor_name) AS named,"
        " count(sponsor_candidate_id) AS linked FROM lp GROUP BY ALL ORDER BY ALL").show()
con.sql("SELECT committee_id, sponsor_name, sponsor_candidate_id, sponsor_source FROM lp"
        f" WHERE committee_id IN {ELEVEN} ORDER BY committee_id").show(max_width=250)
EOF
tail -3 sponsors.py
docker exec -i "$(fl pipeline)" python - "$B" < sponsors.py 2>&1 | grep -v '^{' | tee sponsors-silver.txt
```

**Expected,** in under a minute:

1. Three rows: `list` 324 PACs, all named and linked; `rule` 460, all named and linked; `NULL` 49, none linked, and
   named only where the file names a sponsor that neither the rule nor the list links (the rest of the 49 are blank
   in the file and in the list). Step 4's line, read by source.
2. The eleven PACs: the ten with `sponsor_source` `rule`, each with Q13a's sponsor name as the file gives it and
   Q13a's id (Facts); Eye of the Tiger (`C00467431`) with `SCALISE, STEVE MR`, `H0LA01087` and `list`. A PAC missing
   or with another id is a difference from Q13a: a Bug ticket, linked from NEU-2179, and stop before `publish`.

Then the same eleven in `gold_build`, each with the candidate page its sponsor id opens (an alias goes through
`candidate_redirect`, as the API's candidate route does) and the leadership PACs that page lists:

```bash
# VM
cat > sponsors.sql <<'EOF'
\pset footer off
-- Q13a's ten and Eye of the Tiger, with the sponsor id each should carry (Facts).
create temp table q13a (ord integer, committee_id text, sponsor_candidate_id text, who text);
insert into q13a values
    (1, 'C00271338', 'H2MD05155', 'Hoyer'), (2, 'C00344234', 'H8CA05035', 'Pelosi'),
    (3, 'C00807412', 'H0TX07170', 'Hunt'), (4, 'C00685552', 'H6WA07458', 'Jayapal'),
    (5, 'C00841148', 'P40013039', 'DeSantis'), (6, 'C00617803', 'H2NY10092', 'Jeffries'),
    (7, 'C00574970', 'H4MA05084', 'Clark'), (8, 'C00416131', 'S8MN00438', 'Franken'),
    (9, 'C00387464', 'S2TX00106', 'Cornyn'), (10, 'C00872804', 'H2HI02508', 'Gabbard'),
    (11, 'C00467431', 'H0LA01087', 'Scalise, by the list');

\echo 'The eleven in gold_build, 2024'
select q.who, q.committee_id, c.name, cc.is_leadership_pac, cc.sponsor_name, cc.sponsor_candidate_id,
    coalesce(r.candidate_id, cc.sponsor_candidate_id) as page_id, k.name as page_name,
    case when cc.sponsor_candidate_id = q.sponsor_candidate_id then 'agree' else 'DIFFERS' end as q13a
from q13a q
left join gold_build.committee_cycle cc on cc.committee_id = q.committee_id and cc.cycle = 2024
left join gold_build.committee c on c.committee_id = q.committee_id
left join gold_build.candidate_redirect r on r.old_candidate_id = cc.sponsor_candidate_id
left join gold_build.candidate k on k.candidate_id = coalesce(r.candidate_id, cc.sponsor_candidate_id)
order by q.ord;

\echo 'Each sponsor''s page: the leadership PACs it lists (the API''s candidate query, on gold_build)'
with page as (
    select distinct q.ord, q.who, coalesce(r.candidate_id, q.sponsor_candidate_id) as page_id
    from q13a q left join gold_build.candidate_redirect r on r.old_candidate_id = q.sponsor_candidate_id)
select p.who, p.page_id, cc.committee_id, c.name, array_agg(cc.cycle order by cc.cycle desc) as cycles
from page p
join gold_build.committee_cycle cc on cc.sponsor_candidate_id = p.page_id
    or cc.sponsor_candidate_id in (select old_candidate_id from gold_build.candidate_redirect
        where candidate_id = p.page_id)
join gold_build.committee c on c.committee_id = cc.committee_id
group by p.ord, p.who, p.page_id, cc.committee_id, c.name
order by p.ord, cc.committee_id;
EOF
tail -3 sponsors.sql
pg < sponsors.sql | tee sponsors-gold.txt
```

**Expected:**

1. **The eleven:** each `is_leadership_pac` `t`, with step 7.1's sponsor name and id, `q13a` `agree`, and a
   `page_name` naming the sponsor: fundlens holds a candidate under each id. A `page_id` other than the sponsor id
   is an alias resolved, as the page would; write it in the Log. `DIFFERS` or an empty `page_name` is a defect: the
   gold sponsor check should have caught an id fundlens lacks, so a Bug ticket, linked from NEU-2179, and stop.
2. **Each page:** a row per sponsor naming its PAC with `{2024}` alone: no other cycle's build holds
   `leadership_pac` yet. Another PAC on a sponsor's page is a second PAC the sponsor runs in 2024; check it on FEC
   (`https://www.fec.gov/data/committee/<id>/`) and write it in the Log. A sponsor with no row has a page that links
   no PAC: a Bug ticket.

Copy both tables, and step 7.1's silver counts, into the Log.

### 7.2 The five recipients' bundled totals

```bash
# VM
cat > bundling.sql <<'EOF'
\pset footer off
-- Q13b's five recipients and their 2024 bundled totals (docs/measurements/leadership-lobbyist-2024.md).
create temp table q13b (committee_id text, who text, bundled numeric);
insert into q13b values
    ('C00867937', 'Trump 47 Committee', 10293939), ('C00042366', 'DSCC', 9841143),
    ('C00744946', 'Harris Victory Fund', 9699650), ('C00000935', 'DCCC', 8104058),
    ('C00842336', 'Bell for Missouri', 3167971);

\echo 'The five in gold_build, 2024, against Q13b'
select q.who, q.committee_id, c.name, cc.bundled_total, cc.bundled_total - q.bundled as d_q13b,
    cc.total_individual, cc.bundled_total <= cc.total_individual as within_individual
from q13b q
left join gold_build.committee_cycle cc on cc.committee_id = q.committee_id and cc.cycle = 2024
left join gold_build.committee c on c.committee_id = q.committee_id
order by q.bundled desc;

\echo '2024''s six largest, as gold_build ranks them'
select cc.committee_id, c.name, cc.bundled_total
from gold_build.committee_cycle cc join gold_build.committee c using (committee_id)
where cc.cycle = 2024 order by cc.bundled_total desc nulls last, cc.committee_id limit 6;

\echo '2024''s bundled total against Q10a''s $57,262,231'
select count(*) as committees, count(bundled_total) as with_figure,
    count(*) filter (where bundled_total > 0) as above_0, sum(bundled_total) as total,
    round(100 * (sum(bundled_total) / 57262231 - 1), 4) as pct_off_q10a
from gold_build.committee_cycle where cycle = 2024;

\echo 'bundled_total by cycle'
select cycle, count(*) as committees, count(bundled_total) as with_figure, sum(bundled_total) as total
from gold_build.committee_cycle group by cycle order by cycle;
EOF
tail -3 bundling.sql
pg < bundling.sql | tee bundling.txt
```

**Expected:**

1. **The five:** each `d_q13b` 0, or under $1: Q13b writes whole dollars. `within_individual` `t` for each, as the
   shared contract assumes (Q11: 2024's recipients' $57.3M against $2.55B of individual contributions). Harris
   Victory Fund's `name` is `cm`'s; the bundling file names it Biden Victory Fund. A difference of $1 or more is
   explained before publishing: list the committee's rows in the build's silver `bundling_report` (step 7.1's
   `sponsors.py` shape, `bundling_report` for `leadership_pac`) beside Q13c's kept reports, and find the report that
   is kept, superseded or counted differently. Unexplained, it is a Bug ticket, linked from NEU-2179, and stop.
2. **The six largest:** the five, in Q13b's order, then a sixth below Bell for Missouri's $3,167,971: Q13b's are
   2024's five largest.
3. **2024's total:** `with_figure` equal to `committees` (every 2024 committee has a figure, 0 without a report),
   `above_0` at most step 4's 84 recipients (a recipient whose reports are all $0 stays at 0), `total`
   57262231.23, and `pct_off_q10a` 0.0000, the ticket's "within 1%" with room to spare. Off by more than 1% fails
   the ticket: a Bug ticket, and stop. Under 1% but not 0 means bronze differs from §7's (step 2): explain it.
4. **By cycle:** `with_figure` 0 in every cycle but 2024, whose builds lack `bundling_report` until NEU-2180's
   backfill, so their figure is NULL, "no reports on this build", never $0 (spec §7.7).

Copy all four into the Log.

### 7.3 No receipt total moved

The build adds §7.7's five fields alone. Every other column of every figure table, in every cycle, should be the
live gold's. Each row is compared whole, as JSON, so a column added since this runbook was written is compared too:

```bash
# VM
cat > moved.sql <<'EOF'
\pset footer off
-- committee_cycle's five §7.7 fields, the only columns this build should change.
create temp table new_fields as
select array['is_leadership_pac', 'is_lobbyist_pac', 'sponsor_candidate_id', 'sponsor_name',
    'bundled_total'] as f;

\echo 'Rows that differ between gold and gold_build, every cycle, every column but the five'
select 'committee_cycle' as tbl,
    count(*) filter (where o.committee_id is null or n.committee_id is null) as missing,
    count(*) filter (where o.committee_id is not null and n.committee_id is not null
        and to_jsonb(o) - (select f from new_fields) is distinct from to_jsonb(n) - (select f from new_fields))
        as moved
from gold.committee_cycle o full join gold_build.committee_cycle n using (committee_id, cycle)
union all
select 'candidate_cycle',
    count(*) filter (where o.candidate_id is null or n.candidate_id is null),
    count(*) filter (where o.candidate_id is not null and n.candidate_id is not null
        and to_jsonb(o) is distinct from to_jsonb(n))
from gold.candidate_cycle o full join gold_build.candidate_cycle n using (candidate_id, cycle)
union all
select 'race',
    count(*) filter (where o.race_id is null or n.race_id is null),
    count(*) filter (where o.race_id is not null and n.race_id is not null
        and to_jsonb(o) is distinct from to_jsonb(n))
from gold.race o full join gold_build.race n using (race_id)
union all
select 'race_candidate',
    count(*) filter (where o.race_id is null or n.race_id is null),
    count(*) filter (where o.race_id is not null and n.race_id is not null
        and to_jsonb(o) is distinct from to_jsonb(n))
from gold.race_candidate o full join gold_build.race_candidate n using (race_id, candidate_id)
union all
select 'cycle',
    count(*) filter (where o.cycle is null or n.cycle is null),
    count(*) filter (where o.cycle is not null and n.cycle is not null
        and to_jsonb(o) is distinct from to_jsonb(n))
from gold.cycle o full join gold_build.cycle n using (cycle)
union all
select 'committee',
    count(*) filter (where o.committee_id is null or n.committee_id is null),
    count(*) filter (where o.committee_id is not null and n.committee_id is not null
        and to_jsonb(o) is distinct from to_jsonb(n))
from gold.committee o full join gold_build.committee n using (committee_id)
union all
select 'candidate',
    count(*) filter (where o.candidate_id is null or n.candidate_id is null),
    count(*) filter (where o.candidate_id is not null and n.candidate_id is not null
        and to_jsonb(o) is distinct from to_jsonb(n))
from gold.candidate o full join gold_build.candidate n using (candidate_id);

\echo 'What did move: the five fields, by cycle'
select cycle,
    count(*) filter (where o.is_leadership_pac is distinct from n.is_leadership_pac) as leadership_moved,
    count(*) filter (where n.is_leadership_pac) as leadership_pacs,
    count(n.sponsor_name) as named, count(n.sponsor_candidate_id) as linked,
    count(*) filter (where n.is_lobbyist_pac) as lobbyist_pacs,
    count(n.bundled_total) as with_bundled_total, sum(n.bundled_total) as bundled
from gold.committee_cycle o join gold_build.committee_cycle n using (committee_id, cycle)
group by cycle
having count(*) filter (where row(o.is_leadership_pac, o.is_lobbyist_pac, o.sponsor_candidate_id,
        o.sponsor_name, o.bundled_total) is distinct from row(n.is_leadership_pac, n.is_lobbyist_pac,
        n.sponsor_candidate_id, n.sponsor_name, n.bundled_total)) > 0
order by cycle;
EOF
tail -3 moved.sql
pg < moved.sql | tee moved.txt
```

**Expected,** in a few minutes:

1. Seven rows, `committee_cycle`, `candidate_cycle`, `race`, `race_candidate`, `cycle`, `committee` and `candidate`,
   each `missing` 0 and `moved` 0. This is the ticket's "no receipt total moved", in every cycle, and every
   spending and outside-spending figure with it: load rebuilt every other cycle from the same live builds, and
   2024's other tables are the live build's (step 4). A leadership PAC's money stays its own and a bundled total is
   in no total (spec §7, shared contracts), so nothing but the five fields may move in these tables. The top lists
   (`*_top_*`) and donor tables are not compared: they are built from the same silver as these totals, so a
   bundled total reaching one would move a total here too. A `missing` above 0 means the
   two builds' committees, candidates or races differ. A `moved` above 0 means another table differs, or a bundled
   total or a sponsor reached a figure. Neither is explained by anything since the live build: stop, and file a Bug
   ticket with the rows (`select … where to_jsonb(o) … is distinct from …`).
2. One row, 2024: `leadership_moved` 0 and `leadership_pacs` 839 (Facts: every one is `D` already); `named` the
   three `named` of step 7.1's silver counts added, and `linked` 784, the rule's 460 and the list's 324;
   `lobbyist_pacs` 1461; `with_bundled_total` every 2024 committee, and `bundled` 57262231.23. Another cycle listed
   means load read another build of it: stop.

Write both outputs in the Log.

## 8. Publish

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens publish --cycle 2024 --build-id "$B" 2>&1 | tee publish-raw.log | grep -v '^{' | tee publish.log
grep 'kuma push' publish-raw.log || echo "no failed Kuma push"
mk published "$B" | jq '{step, duration_s}'
gmeta
live
pg -Atc "select count(*) filter (where is_leadership_pac), count(sponsor_candidate_id), count(*) filter (where is_lobbyist_pac), count(bundled_total), sum(bundled_total) from gold.committee_cycle where cycle = 2024"
```

**Expected:** `published build <B> of 2024`, `previous build: 20261125T021311Z`, `cloudflare purge: done`,
`wrote resolution/build=<B>/crosswalk.parquet` and `pruned <n> silver builds (<m> objects)`. Prune removes only
builds older than `20261125T021311Z`: never the live build, nor the one before it, nor NEU-2175's reference, which is
newer. Then `no failed Kuma push`, or a failed push's line (Facts). Then:

- a `published` marker;
- `gold` naming `<B>`, `published_at` now; `gold_prev` the `gold` line of step 1.2;
- `markers/live.json` with 2024 at `<B>`, every other cycle as in step 1.2;
- 2024's committees: `839|784|1461|<n>|57262231.23`, `<n>` every 2024 committee, against step 1.2's `839|0|0|0`.

About 3 min: the purge waits 75 s after the swap on purpose. The merge freeze holds until step 9 is done.

**If a check in step 9 fails.** Roll back:

```bash
# VM
docker exec "$(fl pipeline)" fundlens publish --rollback
```

**Expected:** `rolled back: build <step 1.2's gold> is live`, then `build <B> is now gold_prev`. 2024 shows no
sponsor, lobbyist flag or bundled total again, as before the run. File a Bug ticket with the failed check's output
and link it from NEU-2179. Nothing runs on `pipeline` after a rollback, so end the merge freeze as step 9.3 does:
`gh workflow enable dependencies --repo neuroticsasquat-ch/fundlens` on the laptop.

## 9. Verify

### 9.1 The API serves the build

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/meta?nocache=$(date +%s)" | jq '{build_id, published_at, model_version}'
curl -sSL "https://api.fundlens.org/v1/candidates/H2NY10092?nocache=$(date +%s)" | jq -c '{name, leadership_pacs}' | tee ~/fundlens-leadership-jeffries-after.json
curl -sSL "https://api.fundlens.org/v1/candidates/H2MD05155?nocache=$(date +%s)" | jq -c '{name, leadership_pacs}'
curl -sS "https://api.fundlens.org/v1/committees/C00617803?nocache=$(date +%s)" | jq -c '.cycles[] | select(.cycle == 2024) | {is_leadership_pac, sponsor, is_lobbyist_pac, bundled_total}'
curl -sS "https://api.fundlens.org/v1/committees/C00467431?nocache=$(date +%s)" | jq -c '.cycles[] | select(.cycle == 2024) | {is_leadership_pac, sponsor}'
curl -sS "https://api.fundlens.org/v1/committees/C00867937?nocache=$(date +%s)" | jq -c '.cycles[] | select(.cycle == 2024) | {is_leadership_pac, sponsor, is_lobbyist_pac, bundled_total}'
```

**Expected:** `build_id` `<B>`, `published_at` now. Then Jeffries's `leadership_pacs`:
`[{"committee_id":"C00617803","name":"<JEFF PAC's name>","cycles":[2024]}]`, and Hoyer's with `C00271338`,
AmeriPAC, `[2024]`: step 7.1's page rows. Then JEFF PAC's 2024: `is_leadership_pac` `true` and `sponsor`
`{"candidate_id":"H2NY10092","name":<the file's name>}`; its flag and bundled total as gold_build had them, the
bundled total a number, 0 without a report, never `null`. Eye of the Tiger's: `true`, and
`{"candidate_id":"H0LA01087","name":"SCALISE, STEVE MR"}`. Trump 47 Committee's: `false`, `null`, its flag, and
`bundled_total` 10293939 (or `10293939.0`: the API types it as a float), step 7.2's figure. The candidate calls
follow a redirect (`-L`): if step 7.1 gave a sponsor a `page_id` other than its id, that is the id the API and the
page answer under, and the one to open in step 9.2. A `null` `bundled_total` on 2024 is a response cached before the purge:
read step 9.2's note on the cache, then this step again. Copy the six lines into the Log, beside step 1.2's.

### 9.2 The page

Open `https://fundlens.org/candidate/H2NY10092` in a browser.

**Expected:** under the header, `Leadership PAC: <JEFF PAC's name> (2024)`, with `A PAC this member sponsors; its
money is not counted as the campaign's.` under it. This is the ticket's definition of done. Then click the PAC's
name. It opens `/committee/C00617803?cycle=2024`, whose 2024 section shows a **Leadership PAC in 2024** badge and
`Sponsored by <the sponsor's name>. Its money is counted as no candidate's, not even the sponsor's.`, the name
linking back to `/candidate/H2NY10092?cycle=2024`.

A page with no leadership PAC line is served from an old cache: reload with the cache bypassed (Shift-reload) once.
If it still has none and step 9.1's API line is right, a response cached between publish's purge and now is the
likely cause (NEU-2177 found one): purge the zone again on the VM,
`docker exec "$(fl pipeline)" python -c 'from fundlens.publish import cloudflare; from fundlens.settings import get_settings; cloudflare.purge_for(get_settings())(); print("purged")'`,
which prints `purged`, and reload. If the API line is wrong too, go back to step 9.1.

Then open `https://fundlens.org/committee/C00867937?cycle=2024`.

**Expected:** `Bundled by lobbyists: $10,293,939`, with the note that it is already counted in individual
contributions and added to no total. Write what both pages show in the Log.

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
  cat leadership-lines.txt
  tail -1 memory.txt
  grep -E 'new contributor keys|^crosswalk:' resolve.log
  grep -E '^committee_cycle: |^loaded build' load.log
  free_gb
} | tee run-record.txt
```

One `scp` per file: since OpenSSH 9, `scp` copies over SFTP, which does not expand braces in a remote path.

```bash
# laptop
mkdir -p ~/fundlens-leadership-run
cd ~/fundlens-leadership-run
for f in run-record.txt bronze-before.txt transformed.json memory.txt sponsors-silver.txt sponsors-gold.txt bundling.txt moved.txt; do scp "hetzner-01:fundlens-leadership-run/$f" .; done
```

**Expected:** `run-record.txt` holds the date, the SHA, the two builds, what step 2 extracted, four `step:<name>`
lines with their `duration_s`, step 4's three lines, the last memory line, resolve's two lines, load's
`committee_cycle` and last lines, and the free disk. The other files are the output of steps 1.3, 4 and 7.

Append a Log entry from them, headed `### <date> — 2024 with leadership PACs and lobbyist bundling (NEU-2179)`:

- the date, the SHA, build `<B>` (live before: `20261125T021311Z`), `seats`' `real`, the four marker step times,
  what step 2 extracted, and step 1.2's `gold` and `gold_prev` lines;
- step 4's three lines and the tables whose row count moved;
- step 4.1's peak, the step that set it, and the three models' cost;
- step 5's `new contributor keys` and `crosswalk:` lines;
- step 7.1: the silver counts by source, the eleven PACs and their sponsors, and each sponsor's page;
- step 7.2: the five recipients against Q13b, the six largest, 2024's total against Q10a, and the cycles' figures;
- step 7.3's two outputs;
- steps 9.1 and 9.2: the six API lines before and after, and what both pages showed;
- every deviation, each filed as a ticket and linked from NEU-2179.

In the same PR:

- **`docs/capacity.md`:** a Per cycle row for `<B>`: its date and SHA; `—` for Extract s (or step 2's `real`, if it
  extracted) and `seats`' `real` as Seats s; transform, load and publish from their markers, load as `<total>
  (<aggregates> + <copy>)` from load's last line; and as peak the process's peak resident memory from step 4.1. Its
  note: "First published 2024 build with `leadership_pac`, `lobbyist_pac` and `bundling_report` (NEU-2179). The
  peak <y> GiB, set in <step>; the three models moved DuckDB's figure by <x> GiB."
- **`docs/specs/fundlens-every-fec-dollar-project-spec.md` §7.7:** a paragraph **Checked against FEC**, citing this
  Log: "Measured by NEU-2179 on 2024's first published build with §7's tables (`<B>`): <the ten sponsors and the
  list's Scalise as Q13a has them, and the five bundled totals and 2024's $57,262,231.23 equal to Q13b and Q10a |
  the differences and why>; no receipt total moved."

Open one PR, `docs(runbooks): log the 2024 leadership and bundling run (NEU-2179)`, with the entry. Merging it
redeploys `pipeline`, which is safe now that nothing is running.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-26 — 2024 with leadership PACs and lobbyist bundling (NEU-2179)

Run 2026-11-26 19:09 to 22:05 UTC, on `cf5980cb21b432b051f4cb7dad45ce9a60fab4d2`. Build `20261126T191724Z`; live
before: `20261125T021311Z`. Before the run, `gold` was
`20261123T224142Z|2026-11-26 18:17:41.34821+00|20261116T224205Z` and `gold_prev`
`20261125T021311Z|2026-11-25 15:35:30.960564+00|20261116T224205Z`. After publish, `gold` is
`20261126T191724Z|2026-11-26 21:54:59.416511+00|20261116T224205Z` and `gold_prev` `20261123T224142Z`. Dependabot's
workflow was disabled from step 1.1 to step 9.3, and nothing merged in between. The reference build
`20261126T011839Z` (NEU-2175) had 833/1461/317 rows, and its `contribution` and the live build's were both 50,085,819.

**Bronze (step 1.3).** Nothing was extracted. Every file the live build read was the newest download, each `same`:
`cm`, `cn`, `ccl`, `indiv`, `pas2`, `oth`, `weball`, `webk` and `committee_summary` of 2026-11-23, `oppexp` of
2026-11-22, and `ie_24_48`, `ElectioneeringComm` and `CommunicationCosts` of 2026-11-24. The three new files,
`leadership`, `lobbyist` and `lobbyist_bundle`, were in bronze from 2026-11-25 and read by no live build
(`DIFFERENT`).

| Step | Time | Notes |
| --- | ---: | --- |
| extract | — | nothing extracted |
| seats | 5.4 s | 441 House, 35 Senate (2 special), 1 presidential race; 49 unmatched filings |
| transform | 1823.1 s (30m28s) | against the reference `20261126T011839Z`, no table moved; against the live build, `leadership_pac`, `lobbyist_pac` and `bundling_report` none → 833, 1,461 and 317 |
| resolve | 454.9 s (7m41s) | `0 new contributor keys of 5504649`; crosswalk 0 new donors, 0 re-pointed, 0 redirects; the live model `20261116T224205Z`, untrained |
| load | 1520.4 s (25m27s) | aggregates 711.41 s, copy 774.24 s; every gold check passed, `gold_committee_cycle_bundled_total.sql` and `gold_committee_cycle_sponsor.sql` among them; `committee_cycle` 298,732 rows |
| publish | 195.3 s (3m35s) | pruned 3 silver builds (296 objects); no failed Kuma push; 202 GB free after it |

Load's quality line: precision 0.8122, recall 0.8993 (top 0.9834/0.7591), 30,148,695 matched rows, DIME v4.0.
Resolution: release `cf5980c`, 1 override, 4 adjudications applied.

**Step 4's three lines:**

- `leadership_pac 2024: 833 leadership PACs, sponsor by the rule 460, by the list 324, neither 49; 6 designated D
  the file lacks`
- `lobbyist_pac 2024: 1,461 lobbyist/registrant PACs`
- `bundling_report 2024: 317 reports, 6 superseded; bundled total $57,262,231.23 at 84 recipients`

**Memory (step 4.1).** Peak resident 28.76 GiB, set in `write contribution 2024`, where DuckDB first spilled
(0.78 GiB): 1.04 GiB under DuckDB's 29.80 GiB limit, and 0.03 GiB over NEU-2171's 28.73 GiB. The three models cost
nothing measurable: DuckDB held 20.11 GiB at `silver electioneering_communication 2024`, the model before them, and
20.11 GiB after each of `silver leadership_pac`, `silver lobbyist_pac` and `silver bundling_report`.

**Step 7.1, the ten leadership PACs and the list-linked one.** The build's silver `leadership_pac` by
`sponsor_source`:

| Source | PACs | Named | Linked |
| --- | ---: | ---: | ---: |
| `list` | 324 | 324 | 324 |
| `rule` | 460 | 460 | 460 |
| none | 49 | 3 | 0 |

Each of Q13a's ten is `rule`, with Q13a's id, and Eye of the Tiger is the list's. In `gold_build`, each is a
leadership PAC with the sponsor silver gave it, `agree` with Q13a, and a candidate page under its own id (no alias):

| Who | PAC | Name | Sponsor | Id | Source | Page name |
| --- | --- | --- | --- | --- | --- | --- |
| Hoyer | C00271338 | AMERIPAC: THE FUND FOR A GREATER AMERICA | HOYER, STENY | H2MD05155 | rule | HOYER, STENY |
| Pelosi | C00344234 | PAC TO THE FUTURE | PELOSI, NANCY | H8CA05035 | rule | PELOSI, NANCY |
| Hunt | C00807412 | HELLFIRE PAC | HUNT, WESLEY | H0TX07170 | rule | HUNT, WESLEY |
| Jayapal | C00685552 | MEDICARE FOR ALL | JAYAPAL, PRAMILA | H6WA07458 | rule | JAYAPAL, PRAMILA |
| DeSantis | C00841148 | GREAT AMERICAN COMEBACK | DESANTIS, RON | P40013039 | rule | DESANTIS, RON |
| Jeffries | C00617803 | JOBS, EDUCATION, & FAMILIES FIRST  JEFF PAC | JEFFRIES, HAKEEM | H2NY10092 | rule | JEFFRIES, HAKEEM |
| Clark | C00574970 | FAIR SHOT PAC | CLARK, KATHERINE | H4MA05084 | rule | CLARK, KATHERINE |
| Franken | C00416131 | MIDWEST VALUES PAC | FRANKEN, AL | S8MN00438 | rule | FRANKEN, AL |
| Cornyn | C00387464 | ALAMO PAC | CORNYN, JOHN | S2TX00106 | rule | CORNYN, JOHN SEN |
| Gabbard | C00872804 | DEFEND FREEDOM, INC. | GABBARD, TULSI | H2HI02508 | rule | GABBARD, TULSI |
| Scalise | C00467431 | THE EYE OF THE TIGER POLITICAL ACTION COMMITTEE | SCALISE, STEVE MR | H0LA01087 | list | SCALISE, STEVE MR |

Each sponsor's page lists its PAC with `{2024}` alone. Two pages list a second 2024 leadership PAC, each one
OpenFEC also designates a leadership PAC with that sponsor (`sponsor_candidate_ids`):

- Jayapal: `C00629576` BUILD OUR MOVEMENT PAC, beside MEDICARE FOR ALL;
- Cornyn: `C00570861` R SENATE PAC, beside ALAMO PAC.

**Step 7.2, the five recipients' bundled totals.** Each within $1 of Q13b, which writes whole dollars, and each
under the recipient's individual contributions:

| Recipient | Committee | `bundled_total` | Q13b | Difference | Individual |
| --- | --- | ---: | ---: | ---: | ---: |
| Trump 47 Committee | C00867937 | 10,293,939.08 | 10,293,939 | 0.08 | 341,694,710.00 |
| DSCC | C00042366 | 9,841,143.26 | 9,841,143 | 0.26 | 99,816,495.00 |
| Harris Victory Fund | C00744946 | 9,699,650.33 | 9,699,650 | 0.33 | 914,308,933.00 |
| DCCC | C00000935 | 8,104,057.50 | 8,104,058 | −0.50 | 102,018,297.00 |
| Bell for Missouri | C00842336 | 3,167,971.03 | 3,167,971 | 0.03 | 4,684,102.00 |

`gold_build` ranks the five first, in Q13b's order; the sixth is `C00606939` ROSEN FOR NEVADA, $1,829,265.15. 2024:
20,937 committees, every one with a figure, 67 above 0, total $57,262,231.23, `pct_off_q10a` 0.0000. The other 17
of step 4's 84 recipients are at 0: their reports add to $0, since 2024's total is silver's to the cent. Every other
cycle has `bundled_total` NULL on all its committees (`with_figure` 0, 1980 to 2022 and 2026).

**Step 7.3, nothing else moved.**

- `committee_cycle` (but the five fields), `candidate_cycle`, `race`, `race_candidate`, `cycle`, `committee` and
  `candidate`: each `missing` 0, `moved` 0.
- What did move, one row: `2024 | leadership_moved 0 | leadership_pacs 839 | named 787 | linked 784 |
  lobbyist_pacs 1461 | with_bundled_total 20937 | bundled 57262231.23`. `named` is the 324, 460 and 3 of step 7.1;
  the 839 leadership PACs are the live gold's, every one designated `D` already.

**Steps 9.1 and 9.2.**

- `/v1/meta` served `20261126T191724Z`, published 2026-11-26 21:54:59 UTC, model `20261116T224205Z`.
- Before (step 1.2): Jeffries `{"name":"JEFFRIES, HAKEEM","leadership_pacs":[]}`; Trump 47 Committee's 2024
  `{"is_leadership_pac":false,"sponsor":null,"is_lobbyist_pac":false,"bundled_total":null}`.
- After:
  - Jeffries: `{"name":"JEFFRIES, HAKEEM","leadership_pacs":[{"committee_id":"C00617803","name":"JOBS, EDUCATION, &
    FAMILIES FIRST  JEFF PAC","cycles":[2024]}]}`;
  - Hoyer: `{"name":"HOYER, STENY","leadership_pacs":[{"committee_id":"C00271338","name":"AMERIPAC: THE FUND FOR A
    GREATER AMERICA","cycles":[2024]}]}`;
  - JEFF PAC's 2024: `{"is_leadership_pac":true,"sponsor":{"candidate_id":"H2NY10092","name":"JEFFRIES,
    HAKEEM"},"is_lobbyist_pac":false,"bundled_total":0.0}`;
  - Eye of the Tiger's 2024: `{"is_leadership_pac":true,"sponsor":{"candidate_id":"H0LA01087","name":"SCALISE, STEVE
    MR"}}`;
  - Trump 47 Committee's 2024: `{"is_leadership_pac":false,"sponsor":null,"is_lobbyist_pac":false,
    "bundled_total":10293939.08}`.
- `https://fundlens.org/candidate/H2NY10092` showed `Leadership PAC: JOBS, EDUCATION, & FAMILIES FIRST  JEFF PAC
  (2024)` and its note. The PAC's link opened `/committee/C00617803?cycle=2024`, with the **Leadership PAC in 2024**
  badge and the sponsor line linking back to Jeffries. `https://fundlens.org/committee/C00867937?cycle=2024` showed
  `Bundled by lobbyists: $10,293,939` with its note.
- Bugsink: nothing new.

**Deviations, none filed.**

- Step 9.1 expected Trump 47 Committee's `bundled_total` as `10293939` or `10293939.0`. The API serves
  `10293939.08`, step 7.2's figure: silver keeps the reports' cents, and Q13b's figure is whole dollars.
