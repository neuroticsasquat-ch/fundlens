# Runbook: the weekly run

How fundlens rebuilds its current cycle every Sunday without anyone watching, and what to do when it doesn't
(NEU-2063; spec §5.1, §5.5, §5.6, §10.3, §10.5). Steps 1–8 are done once, top to bottom: a hand run of the current
cycle, a rollback and roll forward, the Coolify scheduled task, the two Kuma monitors resumed, a forced failure
through the task, and the first two unattended Sundays checked. The sections after them are procedures, used when
they are needed: [reading a run's output](#reading-a-runs-output), [a run missed](#a-run-missed),
[rolling back](#rolling-back) and [re-resolving with `--full`](#re-resolving-with---full). Append to the
[Log](#log) at the bottom; never rewrite it.

**Not in this runbook:** the dataset snapshot. Since 2026-11-18 the task runs `fundlens run --scheduled --dataset`,
which takes `fundlens dataset --snapshot` (NEU-2064) once every step has finished; its launch, and the check of the
first Sunday that publishes one, are [dataset-launch.md](dataset-launch.md) (NEU-2067). The cycles before the
current one are built once, by [backfill.md](backfill.md), and rebuilt only by
[re-resolving with `--full`](#re-resolving-with---full).

## Before you start

- NEU-2061 (`run`, `--scheduled`) and NEU-2062 (incremental resolution) are merged and deployed. Step 1.1
  checks.
- The backfill is done ([backfill.md](backfill.md), NEU-2060): every cycle from 1980 to 2026 is live with donors,
  and `/data/fundlens/resolution/resolve.duckdb` is the working file the next incremental resolution reads.
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo, `gh` and `jq`
  are installed, and you can sign in to Coolify, Kuma (`https://kuma.tail1afe5a.ts.net`), Bugsink
  (`https://bugsink.neuroticsasquat.ch`) and Discord `#alerts`.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Scheduled task | `fundlens weekly` on the `pipeline` service: `opentelemetry-instrument fundlens run --scheduled --dataset` (`--dataset` since 2026-11-18, NEU-2067), `0 3 * * 0` |
| Schedule's timezone | Coolify's, **UTC**: Sunday 03:00 UTC, 04:00 on the VM's own clock (CET) or 05:00 in CEST (ops `docs/runbooks/uptime-kuma-monitors.md`, *Schedules*) |
| The cycle it builds | `run` picks it: the next even year from today's, 2026 until 2027-01-01, then 2028 (spec §5.6). From the first Sunday of 2027 the task builds 2028 and 2026 is no longer rebuilt |
| `--scheduled` | The task's flag only. It is the only thing that makes `run` push `fundlens/weekly`, so hand runs, reruns and resumes neither reset the deadman nor alert as a failed Sunday. A hand resume of a failed Sunday passes it, so the monitor recovers ([A run missed](#a-run-missed)) |
| Resolution | Incremental: the cycle's new contributor keys against the live model and the working file (spec §6.10). A scheduled run never starts `resolve --full` by itself. With no live model or working file it stops with exit 1, unless also given `--yes` |
| Push monitors | `fundlens/weekly` (pushed by `run --scheduled` and `crash-test`) and `fundlens/publish` (pushed by every `publish`, scheduled or not, and by `publish --rollback`). Both at 648000 s (7 d + 12 h), retries 0, `Discord #alerts`. Paused by [coolify-setup.md](coolify-setup.md) §12 until step 5 |
| Why 7 d + 12 h for both | A Sunday's push lands when the run ends, and that varies. A 7 d interval would alert on any Sunday that ended later than the one before. The 12 h grace means a Sunday that never finished alerts at about 15:00 UTC the same day |
| A run's output | In Coolify's own database, `coolify-db`, table `scheduled_task_executions`, column `message`. Not in `docker logs`: a scheduled task is a `docker exec`, not the container's main process ([Reading a run's output](#reading-a-runs-output)) |
| How long a run takes | About 45 min plus the incremental resolution: 2026's extract, seats and transform (7 + 5 + 981 s) and the load and publish of every cycle (1,402 + 157 s), `capacity.md`. Step 2 measures the incremental resolution for the first time. Then about 16 minutes for the dataset snapshot, `--dataset` (16m26s by hand on 2026-11-18, `capacity.md` → *Dataset snapshot*) |
| What a merge does | Every merge to `main` makes Coolify recreate the whole fundlens stack, `fundlens-postgres` included. It kills a running `docker exec` in `pipeline`, the scheduled task's included, and a running dump of the database (NEU-2405, Log). Don't merge between 02:00 and 02:30 UTC on any day (the nightly dump), or on Sunday between 03:00 UTC and the run's end. `/doit` merges as soon as CI passes, so check the clock before starting one near 02:00 UTC. Dependabot's auto-merge runs daily at 11:00 UTC and on Saturdays from 13:00 to 23:30 UTC (`.github/workflows/dependencies.yml`), so it never overlaps |
| The nightly backup | `backup-postgres.sh` runs at 03:00 on the VM's clock, 02:00 UTC, and dumps the fundlens database without its `gold*` schemas (`--exclude-schema='gold*'`, spec §10.4: only `app` needs keeping; gold is rebuilt from silver), about 0.7 GB. A failed dump is retried once, 10 minutes later, before the night is marked failed (ops `backups/postgres.md`, NEU-2405). It takes no lock on a gold table, so it cannot hold up `publish`'s swap, which gives up after about 40 s of waiting for its locks (`SWAP_ATTEMPTS`, `LOCK_TIMEOUT`, `SWAP_RETRY_SECONDS`, `src/fundlens/publish/gold.py`). A script installed before NEU-2405 still dumps `gold*` and holds those locks until it ends. Step 1.3 checks which script is installed, and that it ran |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-weekly
```

In the tmux session, define the helpers. Paste the whole block:

```bash
# VM, in tmux
mkdir -p ~/fundlens-weekly && cd ~/fundlens-weekly
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# psql in the fundlens database.
pg() { docker exec "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
# psql in Coolify's own database.
cdb() { docker exec -i coolify-db psql -U coolify -d coolify -P pager=off "$@"; }
# A step's completion marker, or MISSING: `mk <step> <cycle> <build>`.
mk() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; m = markers.read(sys.argv[1], R2.from_settings(get_settings()), cycle=int(sys.argv[2]), build_id=sys.argv[3]); print(m.model_dump_json(indent=2) if m else "MISSING")' "$1" "$2" "$3"; }
# Each cycle's live build, from markers/live.json.
live() { docker exec "$(fl pipeline)" python -c 'from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; print(markers.read_live(R2.from_settings(get_settings())))'; }
# A cycle's newest builds and the markers each has: `builds <cycle>`.
builds() {
  docker exec -i "$(fl pipeline)" python - "$1" <<'PY' 2>&1 | grep -v '^{'
import sys
from collections import defaultdict
from fundlens.r2 import R2
from fundlens.settings import get_settings
steps = defaultdict(list)
for key in R2.from_settings(get_settings()).list_keys(f"markers/cycle={sys.argv[1]}/"):
    build, step = key.split("/")[2:4]
    steps[build.removeprefix("build=")].append(step.removesuffix(".json"))
for build in sorted(steps)[-3:]:
    print(build, " ".join(sorted(steps[build])))
PY
}
# The live gold build and the rollback target, from Postgres.
gmeta() { pg -Atc "select 'gold', build_id, published_at, model_version from gold.meta union all select 'gold_prev', build_id, published_at, model_version from gold_prev.meta"; }
# Free disk on / in decimal GB, as capacity.md counts sizes.
free_gb() { df -BGB --output=avail / | tail -1 | tr -dc '0-9'; }
```

**Expected:** no output.

## 1. Preflight

### 1.1 The deployed code

```bash
# VM
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES DUCKDB_MEMORY_LIMIT
docker exec "$(fl pipeline)" fundlens health; echo "exit=$?"
```

```bash
# laptop
cd ~/projects/fundlens
git fetch origin
SHA=$(ssh hetzner-01 'docker exec "$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)" printenv OTEL_RESOURCE_ATTRIBUTES' | sed 's/.*service.version=//; s/,.*//')
echo "$SHA"
git merge-base --is-ancestor 99029ab "$SHA" && echo "incremental resolution deployed"
```

**Expected:** `service.version=<sha>` and `32GB`; `postgres: ok`, `r2: ok`, `exit=0`; then the SHA and
`incremental resolution deployed` (`99029ab` is NEU-2062). If the line is missing: Coolify → the `fundlens`
resource → *Deploy*, wait for it to finish, and run this step again. Write the SHA in the Log.

### 1.2 What the next run resolves against

```bash
# VM
gmeta
live
builds 2026
docker exec "$(fl pipeline)" python -c 'from fundlens.r2 import R2; from fundlens.resolve import runner; from fundlens.resolve.model import live_version; from fundlens.settings import get_settings; s = get_settings(); store = R2.from_settings(s); print("live model", live_version(store)); print("incremental ready" if runner.incremental_ready(store, s.data_dir) else "NOT READY")' 2>&1 | grep -v '^{'
docker exec "$(fl pipeline)" du -sh /data/fundlens/resolution/resolve.duckdb
free_gb
```

**Expected:** `gold` with build `20261116T005426Z` and model `20261116T224205Z`, and a `gold_prev` line (the
backfill's earlier publish); `markers/live.json` naming 2026's build `20261116T013416Z`; `builds 2026` listing
that build last, with `extracted loaded published resolved transformed`; then `live model 20261116T224205Z`,
`incremental ready`, a working file of about 14G, and at least 130 GB free.

`NOT READY` means the scheduled run would stop at `resolve` with exit 1 every Sunday. Find out why before going
on: no live model, or no working file, is [re-resolving with `--full`](#re-resolving-with---full)'s case. A
newer 2026 build than the live one in `builds 2026` means someone transformed after the backfill: find out who
before step 2, because `run` refuses a build older than its cycle's newest transformed one.

### 1.3 The backup runs every night

```bash
# VM
grep -c "exclude-schema='gold\*'" /usr/local/bin/backup-postgres.sh
ls -l --time-style=+%FT%T%z /var/backups/postgres/ | grep 'fundlens-postgres-' | tail -3
sudo tail -20 /var/log/postgres-backup.log
```

**Expected:** `1` or more from the `grep`; a dump a night, each file named for the script's start, about 03:00 on
the VM's clock (`+0100`); and `Backup complete` in the log. `0` from the `grep` means the installed script
predates NEU-2405: it still dumps `gold*`, and a dump still running when the Sunday run reaches `publish` can fail
it with `LockNotAvailable` (Facts). Stop, and install the script from the ops repo's `main` (ops
`backups/postgres.md`, *Install on the VM*). With the script installed, the dump's finish time no longer matters
to `publish`. A night with no fundlens dump means `app` has no backup for that day. If one is missing, stop: read the
log's error for that night, and compare its time with the merges' (`gh pr list --state merged`). A merge during
the dump is the known cause (Facts, *What a merge does*). Write the latest finish time in the Log.

## 2. A hand run of the current cycle

The first incremental resolution on prod, and a new 2026 build for step 3 to roll back from. A hand run, so it
pushes `fundlens/publish` but not `fundlens/weekly`: both are still paused, so `publish` ends with `kuma push (up)
failed: HTTPError: HTTP Error 404: Not Found`, the paused monitor refusing the push, not a fault.

```bash
# VM, in tmux
echo "$(date -u +%FT%TZ) start hand run" | tee -a hand-window.txt
{ time docker exec "$(fl pipeline)" opentelemetry-instrument fundlens run; } 2>&1 | tee hand-run.log
echo "$(date -u +%FT%TZ) end hand run" | tee -a hand-window.txt
grep -E '^build |^[0-9]{4}: build|new contributor keys|^attach:|^crosswalk:|^warning:|^model |^(extract|seats|transform|resolve|load|publish).*: |loaded build|published build|previous build|^finished build|^real' hand-run.log
```

**Expected:** `build <B> of 2026` first: write `<B>` in the Log. Then resolve's incremental lines, in order:

```
2026: build <B>
<n> new contributor keys of <k>, <e> pairs scored at or above the match threshold
attach: …
overrides: …
adjudications: …
crosswalk: <d> new donors, 0 keys re-pointed, <r> redirects
model 20261116T224205Z: the live model, untrained
load <s> s, … 
DuckDB memory limit: 29.8 GiB
```

Then load's and publish's lines, `published build <B> of 2026` with `previous build: 20261116T013416Z` (2026's live build: `gmeta`'s `20261116T005426Z` is 2024's, the backfill's last publish), the Kuma
404, and `finished build <B> of 2026: ran extract, transform, resolve, load, publish`. About 45 minutes plus the
resolution; `real` gives the whole.

- `<n>` is the 2026 keys the crosswalk had never given a donor_id: FEC's amendments since 2026-11-16 and the week's
  new filings. A few thousand to a few hundred thousand is plausible. All 2026 keys, about 2.6 million, means the
  working file did not hold 2026's: stop and find out why.
- **`keys re-pointed` must be 0.** Anything else prints `warning: <n> keys that stood were re-pointed by
  overrides or verdicts …`: an override or verdict new since the last full run, which only `--full` applies to
  every cycle. Go on, then do [re-resolving with `--full`](#re-resolving-with---full) before the first Sunday.
- If the run stops at `resolve` with exit 1 instead, read its message:
  [A run missed](#a-run-missed) says what each one means. The run built `<B>` up to `transform`, so resume it
  rather than starting a new one.

Then the step times, for `capacity.md`:

```bash
# VM, in tmux
B=<the build from the first line>
for s in extracted transformed resolved loaded published; do printf '%s ' "$s"; mk "$s" 2026 "$B" | jq -r '.duration_s' 2>/dev/null || echo MISSING; done | tee hand-steps.txt
docker exec "$(fl pipeline)" du -sh /data/fundlens/resolution/resolve.duckdb
free_gb
```

**Expected:** five lines, each with seconds; the working file a little larger than in step 1.2 (DuckDB never
shrinks a file); free disk about where it was.

Then check the site:

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq '{build_id, published_at, model_version, precision, recall}'
curl -sS "https://api.fundlens.org/v1/cycles?nocache=$(date +%s)" | jq -r '.[0] | [.cycle, .race_count, .contribution_count, .total_amount] | @tsv'
```

**Expected:** `build_id` `<B>`, today's `published_at`, model `20261116T224205Z` with the backfill's figures; then
2026 first, with races, contributions and a total above 0.

## 3. Roll back, and forward

Proves [rolling back](#rolling-back) on prod (the Definition of done). `gold` is now step 2's build and
`gold_prev` the backfill's:

```bash
# VM
gmeta | tee rollback-before.txt
{ time docker exec "$(fl pipeline)" fundlens publish --rollback; } 2>&1 | tee rollback.log
gmeta
```

**Expected:** `gold` `<B>` and `gold_prev` `20261116T005426Z`; then, after about 75 s (the wait before the purge),
`rolled back: build 20261116T005426Z is live` and `build <B> is now gold_prev`, the Kuma 404; then the two lines
of `gmeta` swapped.

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq -r .build_id
curl -sS "https://api.fundlens.org/v1/meta?nocache=$(date +%s)" | jq -r .build_id
```

**Expected:** `20261116T005426Z` twice: the edge was purged, and the origin agrees. The first still printing `<B>`
means the purge did not reach the edge: run it again in a minute, then read `rollback.log` for `cloudflare purge`.

Roll forward, which is the same command again:

```bash
# VM
{ time docker exec "$(fl pipeline)" fundlens publish --rollback; } 2>&1 | tee rollforward.log
gmeta
live
```

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq -r .build_id
```

**Expected:** `rolled back: build <B> is live`, `build 20261116T005426Z is now gold_prev`; `gmeta` as in
`rollback-before.txt`; `live` naming `<B>` for 2026; then `<B>`. Write both `/v1/meta` readings in the Log.

## 4. The scheduled task

1. Coolify → `fundlens` → `production` → the resource → *Scheduled Tasks* → *+ Add*:

   | Field | Value |
   | --- | --- |
   | Name | `fundlens weekly` |
   | Command | `opentelemetry-instrument fundlens run --scheduled` |
   | Frequency | `0 3 * * 0` |
   | Timeout (seconds) | `21600` (6 h: room for a slow incremental resolution on top of the run's 45 minutes, and still inside the monitors' 12 h grace) |
   | Container name | `pipeline` |

   *Save*. If the form has no *Timeout* field, or names a field differently, record it in the Log.
2. Read it back from Coolify's database:

   ```bash
   # VM
   cdb -c "SELECT to_jsonb(t) - 'id' - 'uuid' FROM scheduled_tasks t WHERE t.name = 'fundlens weekly'"
   ```

**Expected:** one row with the command, `"frequency": "0 3 * * 0"`, `"enabled": true`, the container `pipeline`,
and the timeout if the column exists. Write the row in the Log.

`opentelemetry-instrument` is on the image's `PATH`, as for every app's task (ops
`docs/runbooks/scheduled-task-telemetry.md`); without it the run reports crashes to Bugsink but sends SigNoz no
spans or logs.

## 5. Resume the monitors

In Kuma, open `fundlens/weekly` → *Resume*, then `fundlens/publish` → *Resume*. Open each one's *Edit* page and
check it still reads Heartbeat Interval `648000`, Retries `0`, Notifications `Discord #alerts`. Leave the interval
alone: 7 d + 12 h is the point (Facts).

**Check:** both are listed without *Paused*. A resumed push monitor waits one interval for its first push; step 6
sends them both.

## 6. A forced failure, through the task

The path a real Sunday crash takes: Coolify runs the command in `pipeline`, it crashes, `fundlens/weekly` goes down,
Bugsink gets the event tagged with the step, and both post to `#alerts`.

1. Bugsink → `fundlens`: if the `` RuntimeError: deliberate crash from `fundlens crash-test` `` issue from
   [coolify-setup.md](coolify-setup.md) §11 is open or muted, *Resolve* it. Only a new, regressed or unmuted issue
   posts to Discord.
2. Coolify → the resource → *Scheduled Tasks* → *+ Add*: Name `crash-test (NEU-2063)`, Command
   `opentelemetry-instrument fundlens crash-test`, Frequency `* * * * *`, Container name `pipeline`. *Save*.
3. Wait for one execution, then **delete the task at once**:

   ```bash
   # VM
   cdb -c "SELECT e.status, e.created_at, e.message FROM scheduled_task_executions e JOIN scheduled_tasks t ON t.id = e.scheduled_task_id WHERE t.name = 'crash-test (NEU-2063)' ORDER BY e.created_at DESC LIMIT 3"
   ```

   **Expected:** one row, `failed`, its message ending in the traceback and `RuntimeError: deliberate crash from
   `fundlens crash-test``. Then delete the task in Coolify. Every further minute adds a Bugsink event to the same
   issue and nothing to Discord, so it is noise without proof.

**Expected, within a minute of the execution:**

- Bugsink → `fundlens`: the issue regressed (or new), its newest event with tag `pipeline_mode=crash-test`, release
  `<sha>` (step 1.1), environment `production`.
- Discord `#alerts`: Bugsink's post for the issue, and Kuma's for `fundlens/weekly` going **down** with
  `crash-test: RuntimeError: deliberate crash from `fundlens crash-test``.

Write the execution's time, the Bugsink event's link and both Discord posts' times in the Log.

Put both monitors up, so neither waits out an interval with nothing pushed:

```bash
# VM
docker exec "$(fl pipeline)" fundlens crash-test --recover; echo "exit=$?"
docker exec "$(fl pipeline)" python -c "import os, urllib.request as u; print(u.urlopen(os.environ['KUMA_PUSH_PUBLISH'].split('?')[0] + '?status=up&msg=NEU-2063').read())"
```

**Expected:** `exit=0` and `fundlens/weekly` back **up** in Kuma, Kuma posting the recovery to `#alerts`; then
`b'{"ok":true}'` and `fundlens/publish` **up**. Then resolve the crash-test issue in Bugsink again, so a later
crash reads as new.

## 7. The ops monitor list

`uptime-kuma-monitors.md` in the ops repo is the written copy of every monitor, and its fundlens rows still say
*none yet (NEU-2063)*. In the ops repo, on a branch, replace its `### fundlens` table with:

```markdown
| Monitor | Pinged by | Schedule | Interval | Env var |
| --- | --- | --- | --- | --- |
| `fundlens/weekly` | Coolify task `fundlens weekly` (`fundlens run --scheduled`), on `pipeline` | `0 3 * * 0` | 7.5 d (648000 s) | `KUMA_PUSH_WEEKLY` |
| `fundlens/publish` | the `publish` step of `fundlens weekly`, and every `fundlens publish` by hand | `0 3 * * 0` | 7.5 d (648000 s) | `KUMA_PUSH_PUBLISH` |

`fundlens/weekly` is pushed only by `run --scheduled` (and `fundlens crash-test`), so a hand run never resets it.
Procedures: fundlens `docs/runbooks/weekly.md`.
```

Commit it as `docs(kuma): fundlens monitors are pushed by the weekly task (NEU-2063)`, open the PR, link it from
NEU-2063, and merge it.

## 8. The first two Sundays

On each of the two Sundays after step 4, once the run has had time to finish (from about 05:00 UTC), or on the
Monday:

```bash
# VM
cdb -c "SELECT e.id, e.status, e.created_at, e.updated_at - e.created_at AS took FROM scheduled_task_executions e JOIN scheduled_tasks t ON t.id = e.scheduled_task_id WHERE t.name = 'fundlens weekly' ORDER BY e.created_at DESC LIMIT 3"
```

**Expected:** a row for the Sunday, `success`, created at 03:00 UTC. Then its output
([Reading a run's output](#reading-a-runs-output)), the Sunday's build, and its step times:

```bash
# VM
cdb -At -c "SELECT e.message FROM scheduled_task_executions e WHERE e.id = <id>" | tee sunday-$(date -u +%F).log | grep -E '^build |new contributor keys|^crosswalk:|^warning:|published build|^finished build'
B=<the build from the first line>
for s in extracted transformed resolved loaded published; do printf '%s ' "$s"; mk "$s" 2026 "$B" | jq -r '.duration_s' 2>/dev/null || echo MISSING; done
gmeta
free_gb
```

**Expected:** `build <B> of 2026`; the incremental lines with `0 keys re-pointed` and no `warning:`;
`published build <B> of 2026`; `finished build <B> of 2026: ran extract, transform, resolve, load, publish`; five
step times; `gold` at `<B>`; free disk where it was. Then in Kuma, both monitors **up**, each with an ok push at
the run's end (*weekly* `run: ok`, *publish* `publish: ok`). Then `/v1/meta`:

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq '{build_id, published_at}'
```

**Expected:** `<B>` and the Sunday's `published_at`.

Anything else is [A run missed](#a-run-missed). A failed Sunday doesn't count toward the two: the two must be
consecutive and unattended.

After the second, record them, in one PR, `docs(weekly): record the first two scheduled runs (NEU-2063)`:

1. **`capacity.md` → Per cycle:** a row for each Sunday and one for step 2's hand run: cycle 2026, the date, the
   build, the deployed SHA, the step times from the markers (seats is `—`: it writes no marker), and in the Notes
   resolve's `duration_s` (the table has no resolve column), `<n>` new keys, and the `crosswalk:` line.
2. **`capacity.md` → Triggers:** the weekly run's measured length beside the estimate in its *Weekly run* row.
3. **This runbook → Log:** an entry per Sunday.

Merge it on a weekday: the merge redeploys `pipeline`.

---

## Reading a run's output

A scheduled task's output is in `coolify-db`, `scheduled_task_executions.message`, written when the run ends.
`docker logs` on `pipeline` shows the container's own process (`sleep infinity`), not the task. fundlens's output
carries no secrets: the Kuma push URL is never logged (`src/fundlens/heartbeat.py`).

```bash
# VM. The newest runs, without their output:
cdb -c "SELECT e.id, e.status, e.created_at, e.updated_at - e.created_at AS took FROM scheduled_task_executions e JOIN scheduled_tasks t ON t.id = e.scheduled_task_id WHERE t.name = 'fundlens weekly' ORDER BY e.created_at DESC LIMIT 5"
# One run's output, whole:
cdb -At -c "SELECT e.message FROM scheduled_task_executions e WHERE e.id = <id>" | less
```

How to read it:

- The first line is `build <B> of <cycle>`: the build a resume names.
- A step skipped because its marker exists prints `<step>: skipped, done already`.
- A crash is a `step <name> failed` log line, then a traceback ending in the exception. The Bugsink event
  carries `pipeline_mode=<name>`, the step that crashed.
- The last line of a run that finished is `finished build <B> of <cycle>: ran …`.
- Logs are JSON lines with the stdout lines between them. `grep -v '^{'` keeps only the latter.

While a run is going, `status` is `running` and `message` is empty. Read its progress from the markers
(`builds 2026`) or from SigNoz → *Logs*, service `fundlens-pipeline`.

## A run missed

`#alerts` has a `fundlens/weekly` **down** (a step failed and said so), or `fundlens/weekly` timed out (no run
finished in 7 d + 12 h), or step 8's check found no `success`. Work down the list:

1. **What ran.** The newest executions ([Reading a run's output](#reading-a-runs-output)). No row for the Sunday
   means the task didn't start: check it is still *Enabled* in Coolify, and that its command and container match
   step 4 (Coolify settings have reverted after upgrades before). A `running` row long after 03:00 UTC means it is
   still going or hung: `docker top "$(fl pipeline)"` shows a `fundlens run` if it is going. A row with no output
   and a `failed` status after a deploy means the deploy killed it.
2. **Which build, and how far it got.** The output's first line, or, if there is none, `builds 2026`: the newest
   build and the markers it has.
3. **Why it stopped,** from the output's end and Bugsink. Then the row below.
4. **Resume it** once the cause is fixed: the same build, with `--scheduled`, so `fundlens/weekly` recovers. A resume
   skips each step whose marker exists:

   ```bash
   # VM, in tmux
   { time docker exec "$(fl pipeline)" opentelemetry-instrument fundlens run --build-id <B> --scheduled; } 2>&1 | tee resume-<B>.log
   ```

   **Expected:** `build <B> of 2026`, the remaining steps' output, `<step>: skipped, done already` for the rest,
   `finished build <B> of 2026: ran …`, and in Kuma `fundlens/weekly` **up**.
5. **Log it:** the date, the build, the cause, the fix and the resume, in this runbook's Log.

| The run stopped with | Means | Do |
| --- | --- | --- |
| A traceback, exit 1, a Bugsink event `pipeline_mode=<step>` | `<step>` crashed | Fix the cause (a ticket if it is code, then merge and deploy), then step 4. FEC serving a truncated file (NEU-2321) is fixed by waiting for FEC and resuming |
| `no live model and working file to resolve against, and a scheduled run does not start resolve --full by itself` | The working file or the live model is gone | Find out why first: `ls -l /data/fundlens/resolution/` in `pipeline`, and step 1.2's check. Then either resume with `--yes` (`run --build-id <B> --scheduled --yes`), which resolves in full, about 2 h, then loads and publishes; or [re-resolve with `--full`](#re-resolving-with---full) steps 1–4, then step 4 here without `--yes` |
| `the working file was resolved with model <V>, but the live model is <L>: finish that run with fundlens resolve --full --model <V>` | A `resolve --full` stopped part way after saving its model | Finish it as the message says ([re-resolving with `--full`](#re-resolving-with---full) step 3's `--model` rerun), then its steps 4 and the resume here |
| `the working file holds <n> keys of other cycles … that app.crosswalk does not`, or `the working file's clusters are not the crosswalk's donors (…)`, each ending `run fundlens resolve --full` | The working file and the crosswalk disagree | Only a person resolves in full over it: [re-resolving with `--full`](#re-resolving-with---full) steps 1–4, then step 4 here. `--yes` does not override this |
| `no live model to resolve with`, `no working file to resolve against` or `the working file holds no clusters to resolve against` | Run by hand without `--scheduled`, which resolves in full by itself when it can: these come from `resolve` alone | As the row for the scheduled run's message above |
| `build <B> of 2026 is older than its newest transformed build, <N>: resume <N> with --build-id <N>, or start a new build` | Someone transformed a newer build of the cycle since this one started | Don't resume `<B>`. Find out who made `<N>` and whether it is meant to go live; then resume `<N>`, or run a new build (`run --scheduled`, with no `--build-id`) |
| `too many open files` (Bugsink, often opening a Parquet), then `IOException: Cannot open file "…/scratch/load-<C>-<B>/<table>.csv": No such file or directory` in `load` | Most likely the container's open-file soft limit: a load opens every cycle's live silver build plus DuckDB's spill files. 2024's load died this way under Docker's default 1,024 and passed with 65536 (NEU-2147's run, `reported-totals-run.md` Log), so `docker-compose.prod.yml` sets `nofile` to 65536 on `pipeline` and `api` (NEU-2399) | `docker exec "$(fl pipeline)" sh -c 'ulimit -Sn'; docker exec "$(fl api)" sh -c 'ulimit -Sn'`. `1024`: the deploy lacks the limit. Coolify → the `fundlens` resource → *Deploy* (not during a Sunday run, Facts), check it again, and if it still prints `1024`, a ticket: Coolify dropped `ulimits`. Once it prints `65536`, step 4 (it resumes at `load`). `65536` already: something else ran out of files, so a ticket, and step 4 once it is fixed |
| `LockNotAvailable` in `publish` | A session held a `gold_prev` table (the swap drops them) or `gold_build.meta` (it updates it) for the swap's 40 s. Not the nightly backup, which leaves out `gold*` since NEU-2405 (Facts), unless the VM's `/usr/local/bin/backup-postgres.sh` predates that change | `ps -o pid,lstart,args -C pg_dump` on the VM, and `grep -c exclude-schema /usr/local/bin/backup-postgres.sh` (0: reinstall it from the ops repo). Then step 4 (it resumes at `publish`) |
| Nothing: killed by a deploy, or by the task's 6 h timeout | The process died without pushing | A deploy: step 4. The timeout: read SigNoz's logs for the step it was in before resuming, and log how long it had run |
| `build <B> of <C> is having its donor ids rewritten: snapshot it once fundlens resolve has finished`, or `no crosswalk snapshot for the live build <B>`, exit 1 after `finished build` | `--dataset`'s snapshot: a resolve was still rewriting the live build, or its publish never took the crosswalk snapshot | The build is live; only the snapshot is missing. Once the resolve has finished (or after `fundlens publish --cycle <C> --build-id <B>` for the crosswalk), run `fundlens dataset --snapshot` |

A `warning: <n> keys that stood were re-pointed` line in a run that finished is not a miss: the run published.
Schedule [re-resolving with `--full`](#re-resolving-with---full) before the next Sunday.

## Rolling back

When a publish put something wrong live (a gold check missed it, a page shows wrong figures) and the build before
it was right. `publish --rollback` swaps `gold_prev` back in as `gold`, rewrites `markers/live.json` from it, waits
75 s for the API's build-id cache, and purges Cloudflare. It writes no marker and prunes nothing. A second
rollback swaps forward again.

```bash
# VM
gmeta
{ time docker exec "$(fl pipeline)" fundlens publish --rollback; } 2>&1 | tee rollback-$(date -u +%F).log
gmeta
live
```

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq '{build_id, published_at, model_version}'
curl -sS "https://api.fundlens.org/v1/meta?nocache=$(date +%s)" | jq -r .build_id
```

**Expected:** `gmeta`'s two lines swapped, `rolled back: build <prev> is live`, `build <bad> is now gold_prev`;
`live` naming `<prev>` for its cycle; then `<prev>` from the edge and from the origin. A `nothing to roll back to:
gold_prev holds no build` means there is no earlier gold to go to.

What it leaves behind:

- **The next run rebuilds the bad build's cycle from scratch and the others from their live builds.** A load reads
  `markers/live.json`, which now names `<prev>`. Fix the cause before Sunday, or turn the task off (Coolify →
  the task → *Enabled* off), and back on once it is fixed.
- **The next publish drops the bad build:** it replaces `gold_prev`. Until then, `publish --rollback` returns to
  it.
- **Rolling back past a `--full`** puts the earlier donor_ids live only until the next load. `resolve --full`
  rewrote every cycle's silver in place under its build (spec §6.6), so any later load builds gold with the new
  donor_ids again. Undoing a `--full` is another `--full`, with the change that caused it reverted.

## Re-resolving with `--full`

**When:** the resolution model or normalization changes (a comparison level, a threshold, a name or address rule in
`src/fundlens/resolve/normalize.py`, `nicknames.csv` or `aliases.yaml`); an incremental run printed `warning: … keys
that stood were re-pointed`, from an override or a verdict new since the last full run; or the working file is lost
or no longer matches the crosswalk ([A run missed](#a-run-missed)). Incremental resolution never changes a
donor_id it gave, so none of these reaches the cycles already built without it.

**What it does:** retrains the model on every cycle's contributor keys, re-clusters them, gives each cluster its
persistent donor_id, writes the donor_ids onto every cycle's newest transformed build and makes the model live.
Then one load and publish of the current cycle rebuilds all of gold from every cycle's live build, now with the new
donor_ids. Historical cycles are not extracted or transformed again.

**How long:** about 2h30m, from `capacity.md`: `resolve --full` over every cycle took 7,147 s (Resolution,
2026-11-16), `validate` about 4 min, and the load and publish of every cycle 1,402 + 157 s (Per cycle,
2026-11-17). Its peak memory was 32.60 GiB of the 40 GiB container, and free disk fell by about 130 GB while it
ran.

1. **Pick the time, and freeze merges.** Not within 4 h of Sunday 03:00 UTC: two pipeline runs at once don't fit
   the box. Otherwise turn the task off (Coolify → the task → *Enabled* off) and turn it on at step 6. Then:

   ```bash
   # laptop
   gh workflow disable dependencies --repo neuroticsasquat-ch/fundlens
   gh pr list --repo neuroticsasquat-ch/fundlens --state open
   ```

   **Expected:** no output from the first; the open PRs, none of which merges until step 6. A merge redeploys
   `pipeline` and kills the run.
2. **What it will read.** Every cycle's newest transformed build must be its live build:

   ```bash
   # VM, in tmux
   docker exec -i "$(fl pipeline)" python - <<'PY' 2>&1 | grep -v '^{' | tee resolve-inputs.txt
   from fundlens import markers
   from fundlens.r2 import R2
   from fundlens.resolve.runner import transformed_builds
   from fundlens.settings import get_settings

   store = R2.from_settings(get_settings())
   live = markers.read_live(store)
   for cycle, build in transformed_builds(store).items():
       print(cycle, build, "live" if live.get(cycle) == build else f"NOT LIVE (live: {live.get(cycle)})")
   PY
   free_gb
   ```

   **Expected:** a line per cycle, 1980 to the current cycle, each `live`, and at least 130 GB free (the run
   deletes the old working file first, which frees about 102 GB more). A `NOT LIVE` line means resolution would
   write donor_ids onto a build that step 5 would not load: stop, and find where that build came from. The one
   exception is the current cycle's build of a run that stopped at `resolve`, from [A run missed](#a-run-missed):
   that is the build step 5 resumes.
3. **Resolve.** First start a disk guard in its own tmux window (`Ctrl-b c`; the helpers are not defined
   there). It restarts `pipeline`, which stops the run, if free disk falls under 60 GB, then exits:

   ```bash
   # VM, a new tmux window
   cd ~/fundlens-weekly
   while true; do
     f=$(df -BGB --output=avail / | tail -1 | tr -dc '0-9')
     if [ "$f" -lt 60 ]; then
       p=$(docker ps --format '{{.Names}}' | grep '^pipeline-lvch8zyndujjzkz16ksys8im' | head -1)
       echo "$(date -u +%FT%TZ) free=${f}GB < 60: docker restart $p" | tee -a guard.txt
       docker restart "$p" 2>&1 | tee -a guard.txt
       break
     fi
     sleep 10
   done
   ```

   Then, back in window 0 (`Ctrl-b 0`):

   ```bash
   # VM, in tmux
   export M=$(date -u +%Y%m%dT%H%M%SZ)
   echo "$M" | tee model-version.txt
   { time docker exec "$(fl pipeline)" opentelemetry-instrument fundlens resolve --full --build-id "$M"; } 2>&1 | tee resolve-full.log
   grep -v '^{' resolve-full.log | tail -14
   ```

   **Expected:** a `<cycle>: build <build>` line per cycle, matching `resolve-inputs.txt`; then `<k> contributor
   keys in <c> clusters`, `recluster:`, `overrides:`, `adjudications:`, `crosswalk:`, `model <M>: trained, wrote
   resolution/model/<M>.json`, the phase times, `DuckDB memory limit: 29.8 GiB`, and `real` about 2 h. Most
   donor_ids are kept by the crosswalk's rules; `crosswalk:` gives the new donors, the re-pointed keys and the
   redirects. If it fails after its `resolve model:` log line, the model is saved: rerun with `--model "$M"` in
   place of `--build-id "$M"`, which skips the 14 min of training. If it fails before, rerun the same command.
   [backfill.md](backfill.md) step 5.2 has the failures seen at this scale.
4. **Validate 2024,** so `/v1/meta` and the methodology page keep resolution's quality figures under the new
   model ([refreshing-dime.md](refreshing-dime.md) §5):

   ```bash
   # VM, in tmux
   time docker exec "$(fl pipeline)" fundlens validate --cycle 2024 | tee validate.txt
   ```

   **Expected:** the precision and recall table and `model <M>, DIME v4.0, build <2024's live build>`. If overall
   precision falls by more than 0.02 from `/v1/meta`'s, stop before step 5 and file a ticket with both sets of
   figures: the live gold still holds the old donor_ids, so nothing is lost by waiting.

   Coming from [A run missed](#a-run-missed)? Stop here and resume the Sunday's build there (its step 4): its load
   and publish are step 5's.
5. **Load and publish every cycle,** resuming the current cycle's live build from `load`:

   ```bash
   # VM, in tmux
   C=2026
   B=$(docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; print(markers.read_live(R2.from_settings(get_settings()))[int(sys.argv[1])])' "$C" | tail -1)
   echo "$B" | grep -Ex '[0-9]{8}T[0-9]{6}Z' || echo "NO BUILD: stop"
   { time docker exec "$(fl pipeline)" opentelemetry-instrument fundlens run --cycle "$C" --build-id "$B" --from load; } 2>&1 | tee reload.log
   grep -E 'quality:|resolution:|loaded build|published build|previous build|^finished build|^real' reload.log
   ```

   **Expected:** the build ID (`NO BUILD: stop` means the cycle has no live build: stop, and read `live`); load's lines with `quality: precision …` at step 4's figures and `loaded build <B> into
   gold_build …`; `published build <B> of 2026`, `previous build: <B>` (only gold changes, not the build);
   `extract: skipped, done already`, `transform: skipped, done already`, `resolve: skipped, done already`;
   `finished build <B> of 2026: ran load, publish`. About 26 min. A hand run, so `fundlens/weekly` is not pushed,
   and `fundlens/publish` is.
6. **Verify and restore.**

   ```bash
   # laptop
   curl -sS https://api.fundlens.org/v1/meta | jq '{build_id, model_version, precision, recall, published_at}'
   gh workflow enable dependencies --repo neuroticsasquat-ch/fundlens
   ```

   **Expected:** model `<M>` with step 4's figures and today's `published_at`. Turn the task back on if step 1
   turned it off, and stop the guard. Record the run in `capacity.md` (a Resolution row, and a Per cycle row for
   step 5), and in this runbook's Log.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-17 — Runbook written (NEU-2063)

Written from `main` at `be3084f` (NEU-2062 merged). Found while writing, against the ticket's Solution:

- **`resolve --full --yes` is not a command.** `resolve` has no `--yes`. The flag is `run`'s, with `--scheduled`
  only, and lets a scheduled run fall back to `resolve --full` when there is nothing to resolve against. The hand
  procedure is `resolve --full`, then `validate`, then `run --from load` ([Re-resolving with
  `--full`](#re-resolving-with---full)); `run --scheduled --yes` is the resume of a Sunday that stopped for a lost
  working file ([A run missed](#a-run-missed)).
- **"`load`/`publish` for every cycle" is one load and one publish.** A load rebuilds all of gold from every cycle's
  live build, so one `run --from load` of the current cycle puts every cycle's new donor_ids live, as the backfill's
  step 6 did.
- **"Sunday 03:00 box time" is 03:00 UTC.** Coolify's scheduled tasks run on UTC; the VM's own clock is CET. Spec
  §5.6 now says UTC.
- **The nightly backup can block `publish`.** It dumps `gold*` too, at 02:00 UTC, and `publish` gives up on its swap
  after about 40 s of waiting for its locks. Step 1.3 checks that the dump ends in time.
- **A hand run comes before the task** (step 2). The first incremental resolution on prod then runs with someone
  watching, not on the first Sunday, and it gives step 3 a build to roll back from.

**Pending:** steps 1–8.

### 2026-11-20 — Merges and the nightly backup (NEU-2405)

- **A merge recreates `fundlens-postgres`, not just `pipeline`.** Merges at 02:01, 02:15 and 02:35 UTC killed the
  fundlens dumps of 2026-11-19 and 2026-11-20, so the last good one was 2026-11-18's. An `app`-only dump taken by
  hand on 2026-11-20 at 23:00 UTC covers the gap: `/var/backups/postgres/fundlens-app-manual-20261120T2300Z.dump`,
  715 MB. Facts now name the 02:00–02:30 UTC window. The 02:35 merge killed a 3.6 GB dump, `gold*` included, that
  was still running; the window assumes the 0.7 GB one below. If step 1.3's dumps finish after 03:30 on the VM's
  clock, widen it.
- **The dump leaves out `gold*` and retries once** (ops `backups/backup-postgres.sh`), so it shrinks from 3.6 GB to
  about 0.7 GB and no longer locks the gold tables. Step 1.3 now checks that this script is installed and ran, not
  that the dump ended before `publish`.
- **`resolve.duckdb` was compacted** from 101.6 GiB (360,262 of 416,215 blocks free) to 13.5 GiB. Step 1.2 expects
  about 14G.
