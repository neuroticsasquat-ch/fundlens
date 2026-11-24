# Runbook: the 2024 production run with spending and payees

How to put spending and payees live for 2024 on real data (NEU-2160; every-FEC-dollar spec §5). Extract FEC's
2024 `oppexp` and `committee_summary` files, then transform a new 2024 build with `operating_expenditure` and
record its memory against NEU-2149's estimate. Load gold with the build's spending totals, categories and top
payees, its payee pages and the spending `reconciliation` measure, and publish it. Check ten committees' spending
against FEC's `committee_summary_2024.csv`, then the pages. Then review the top 20 payees for wrong merges, split
firms, missed in-kind outlays and names that should have no page. Run it once, top to bottom, on
`music-box-dancer`, one step at a time. Append to the [Log](#log) at the bottom; never rewrite it.

**Why now.** NEU-2151 to NEU-2159 are merged. 2026's spending went live on 2026-11-22 at 04:49 UTC, when the
Sunday run published 2026's build `20261122T030019Z` on `fc14e04`. 2024 has none: its live build,
`20261119T212247Z` (NEU-2147), was transformed before NEU-2152. Load reads a backfill-pending table as having no
rows (spec §2, older builds), so every 2024 committee page says "not available" under Spending, and no 2024 payment
reaches a payee page. Three transform-only 2024 builds were made on 2026-11-21 (NEU-2152, NEU-2153, NEU-2408), but
none was loaded or checked against FEC. This run does both.

**Why only `oppexp` and `committee_summary` are extracted.** 2024's live build read `indiv`, `pas2`, `oth`, `cm`,
`cn` and `ccl` as FEC published them on 2026-11-15 and 2026-11-16. A full extract would download them again with
FEC's amendments since, and step 4 could not tell an amendment from a bug. `extract --file` downloads only the two
files this run compares, on the same day, so that FEC's spending rows and FEC's reported figure are of the same
date. Transform then reads every other file exactly as build `20261121T211606Z` (NEU-2408) did, the reference that
step 4 checks the row counts against.

**What else goes live.** Since the live build, NEU-2400, NEU-2401 and NEU-2402 changed how receipts are read, and
NEU-2454 changed which `committee_summary` row counts. None of these is in a live 2024 build yet, so this publish
moves some 2024 receipt figures as well. Step 7.3 records how many. They are not this ticket's to check.

**Why no `run`.** `fundlens run --from transform` would still run `extract` in full, because this build has no
`extracted` marker. The steps are run one by one, as `run` orders them.

**Not in this runbook:** cycles before 2024 (NEU-2180's backfill), and the dataset snapshot: Sunday's `run
--dataset` takes it.

## Before you start

- NEU-2159 (`97b462f`, PR #223) is merged, and so is this runbook. Step 1.1 checks that the deployed code includes
  it.
- **Nothing merges to `main` from step 2 until step 10 has printed its last line.** Every merge redeploys
  `pipeline` and kills a running `docker exec`. On 2026-11-02 a docs merge killed a `publish` part way through.
  Step 1.1 turns Dependabot's auto-merge off.
- Not within 4 h of Sunday 03:00 UTC: the scheduled `fundlens weekly` task runs then, and two pipeline runs at once
  do not fit the box. Not between 02:00 and 02:30 UTC either: the nightly backup runs then ([weekly.md](weekly.md)
  Facts).
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo, `gh`
  and `jq` are installed, and you can sign in to Bugsink (`https://bugsink.neuroticsasquat.ch`) and Linear.
- Allow about three hours: about 31 min of transform (NEU-2408's run), 8 of resolve and 28 of load (NEU-2147's),
  3 of publish, and the payee review, which is reading.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycle | `2024` |
| 2024's live build before this run | `20261119T212247Z`, transformed on `6e01035` (NEU-2147), resolved under model `20261116T224205Z` ([reported-totals-run.md](reported-totals-run.md) Log) |
| The reference transform | `20261121T211606Z`, transform-only on `e4125a6` (NEU-2408), never loaded. It read the live build's v1 files and logged `operating_expenditure 2024: 2,246,038 rows, 1,550,225 counted, $9,594,284,292.22 counted, $362,505,186.62 (3.78%) unclassified` |
| Silver and transform changes since the reference | `77edd82` (NEU-2454, `reported_total`'s cycle-to-date row) alone |
| Gold changes since the live gold | `b62c49e` (NEU-2155, six more spellings in `fec/payee_no_page.csv`). The live gold, published 2026-11-22 04:49 UTC on `fc14e04`, already has every spending and payee table, with 2026's rows in them |
| NEU-2149's memory estimate | `operating_expenditure` holds 0.87 GiB in DuckDB for 2024, putting the transform's peak at about 27.35 GiB against DuckDB's 29.80 GiB (`32GB`) limit. NEU-2152 writes and drops it first, so it is gone before `contribution`'s write, the peak (spec §5.1). Measured since: 0.68 GiB; peak 27.44 GiB on the reference, with 2 GiB of spread between runs of the same code ([capacity.md](../capacity.md)) |
| The measurement's Q11 figures | At the 9,909 committees with a reported figure above $0: counted $9,594,311,329 against reported $9,916,558,902, median committee 98.76%, 63 committees more than 1% over by $1,086,185. By group (Q11b, median and dollar-weighted): candidate 99.20% / 99.44%, super PAC 99.49% / 99.82%, other 98.14% / 99.45%, party 50.51% / 83.83%. 12 committees list a reported $0 beside counted money (spec §5.6). `docs/measurements/oppexp-2024.md` Q11 |
| The ten comparisons | `C00840017` ALSOBROOKS FOR SENATE and `C00264697` (Sherrod Brown): Senate campaigns. `C00703975` (Biden, then Harris): Form 3P, the handoff. `C00853473` JONATHAN NEZ FOR CONGRESS: Q11d's largest excess. `C00835959` FAIRSHAKE and `C00571703` SLF PAC: super PACs. `C00494021` CATHOLICVOTE.ORG CANDIDATE FUND: Q11d's second-largest excess. `C00003418` RNC and `C00010603` DNC: parties. `C00401224` ACTBLUE: an "other" filer, and the conduit the reconciliation does not exclude here (spec §5.6) |
| What a comparison checks | That gold's `reported_operating_expenditures` is the file's `OP_EXP` + `TTL_OP_EXP` (Form 3 and 3P fill the first, Form 3X the second; `09_reported_total.sql`), and how gold's `total_operating_expenditures` stands against it. Itemized spending sits below the reported figure by design: payments of $200 or less a year to one payee are unitemized (spec §5.2) |
| Monitors | `fundlens/publish` gets a push from `publish`. If the monitor is still paused, `publish` ends with `kuma push (up) failed: HTTPError: HTTP Error 404: Not Found`: the paused monitor refusing the push, not a fault |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-spending
```

In the tmux session, define the helpers. Paste the whole block:

```bash
# VM, in tmux
mkdir -p ~/fundlens-spending-run && cd ~/fundlens-spending-run
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# A step's completion marker for one 2024 build, or MISSING: `mk <step> <build>`.
mk() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; m = markers.read(sys.argv[1], R2.from_settings(get_settings()), cycle=2024, build_id=sys.argv[2]); print(m.model_dump_json(indent=2) if m else "MISSING")' "$1" "$2"; }
# Each cycle's live build, from markers/live.json.
live() { docker exec "$(fl pipeline)" python -c 'from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; print(markers.read_live(R2.from_settings(get_settings())))'; }
# psql in the fundlens database. `-i`, so a query can come from stdin (`pg <<'SQL'`).
pg() { docker exec -i "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
# The live gold build and the rollback target, from Postgres.
gmeta() { pg -Atc "select 'gold', build_id, published_at, model_version from gold.meta union all select 'gold_prev', build_id, published_at, model_version from gold_prev.meta"; }
# Free disk on / in decimal GB, as capacity.md counts sizes.
free_gb() { df -BGB --output=avail / | tail -1 | tr -dc '0-9'; }
```

**Expected:** no output. If the tmux session is lost, run `tmux attach -t fundlens-spending`. If the session itself
is gone, paste the helpers again, `cd ~/fundlens-spending-run`, and export what earlier steps saved:
`export OLD=$(cat old-build.txt)` from step 1.2 on and `export B=$(cat build-id.txt)` from step 3 on.

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
git merge-base --is-ancestor 97b462f "$SHA" && echo "payee page deployed"
git log --oneline e4125a6.."$SHA" -- sql/silver 'sql/checks/silver_*' src/fundlens/transform src/fundlens/fec/files.py src/fundlens/resolve/normalize.py src/fundlens/resolve/aliases.yaml
gh workflow disable dependencies --repo neuroticsasquat-ch/fundlens
gh pr list --repo neuroticsasquat-ch/fundlens --state open
```

**Expected:** `service.version=<sha>` and `32GB`; `65536` (NEU-2399); `postgres: ok`, `r2: ok`, `exit=0`; `nothing
running`. Then the SHA, `payee page deployed`, and exactly one commit, `77edd82` (NEU-2454), from the Facts. If the
`deployed` line is missing: Coolify → the `fundlens` resource → *Deploy*, wait for it to finish, and run this step
again. A second commit means silver changed since the reference transform, so step 4 would blame its differences on
the wrong thing: stop and find out what it changes. Then no output from `gh workflow disable`, and the open PRs:
none of them merges until step 10 is done. Write the SHA in the Log.

### 1.2 The live state

```bash
# VM
gmeta
live
live | grep -o "2024: '[0-9TZ]*'" | grep -o '[0-9]\{8\}T[0-9]\{6\}Z' | tee old-build.txt
export OLD=$(cat old-build.txt)
mk transformed 20261121T211606Z | tee ref-transformed.json | grep -A20 '"row_counts"'
pg -Atc "select cycle, count(*), count(total_operating_expenditures) from gold.committee_cycle where cycle in (2024, 2026) group by cycle order by cycle"
pg -Atc "select count(*), count(*) filter (where first_cycle = 2024) from gold.payee"
docker exec "$(fl pipeline)" python -c 'from fundlens.r2 import R2; from fundlens.resolve import runner; from fundlens.settings import get_settings; s = get_settings(); print("incremental ready" if runner.incremental_ready(R2.from_settings(s), s.data_dir) else "NOT READY")' 2>&1 | grep -v '^{'
free_gb
```

**Expected:**

- `gold` naming `20261122T030019Z` (2026's build), `published_at` 2026-11-22 04:49 UTC or later, and `gold_prev`.
  Write both lines in the Log: after step 8, `gold` becomes `gold_prev`, the rollback target.
- `markers/live.json` with 2024 at `20261119T212247Z`, and `old-build.txt` holding it. Another build means someone
  published 2024 since the Facts were written: stop, and read [backfill.md](backfill.md) and
  [weekly.md](weekly.md)'s Logs to find out what it is.
- The reference's `transformed` marker, its `row_counts` with `operating_expenditure: 2246038`. `MISSING` means the
  reference was pruned. Compare against the live build instead, `mk transformed "$OLD" | tee ref-transformed.json`,
  and write every table step 4 then finds moved in the Log, with the commit since `6e01035` that explains it.
- Two lines, `2024|<n>|0` and `2026|<m>|<k>` with `<k>` above 0. A 2024 spending figure already means a 2024 build
  with `operating_expenditure` is live: stop and find out which.
- The payee count, and `0`: no payee's first cycle is 2024 yet.
- `incremental ready`, and at least 100 GB free: `transform` can spill up to 60 GB of DuckDB scratch
  (`DUCKDB_MAX_TEMP_DIRECTORY_SIZE`). With less, free some first.

Then what the site serves for the Senate campaign before the run:

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/committees/C00840017?nocache=$(date +%s)" | jq '{name, c: [.cycles[] | select(.cycle == 2024) | {total_operating_expenditures, categories: (.spending_by_category | length), payees: (.top_payees | length)}]}'
```

**Expected:** `ALSOBROOKS FOR SENATE` with 2024's `total_operating_expenditures: null`, `categories: 0` and
`payees: 0`.

### 1.3 Transform will read the reference's v1 files

transform reads the newest bronze download of each file. List them:

```bash
# VM
docker exec -i "$(fl pipeline)" python - <<'PY' 2>&1 | grep -v '^{' | tee bronze-before.txt
from fundlens import paths
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.settings import get_settings

store = R2.from_settings(get_settings())
for name, file in CATALOGUE.items():
    keys = sorted(store.list_keys(paths.bronze_dir(2024, name)))
    print(name, keys[-1] if keys else "NONE")
PY
```

**Expected:** a line per file. `cm`, `cn`, `ccl`, `indiv`, `pas2` and `oth` each end in a date no later than
`2026-11-16`, and `weball` and `webk` in `2026-11-19`, as in the reference. `oppexp` ends in a date from
2026-11-21, the NEU-2152 run's download, and `committee_summary` in `2026-11-19` or later: step 2 downloads both
again. A v1 file dated after 2026-11-16 means someone extracted 2024 since the live build, so transform would read
FEC's amendments since then. Stop and find out who.

## 2. Extract the two files

```bash
# VM, in tmux
time (for f in oppexp committee_summary; do docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --file "$f" 2>&1 | grep -v '^{'; done | tee extract.log)
```

**Expected:** two lines: `oppexp: downloaded bronze/cycle=2024/oppexp/<today>.zip` (about 64 MB) and
`committee_summary: downloaded bronze/cycle=2024/committee_summary/<today>.csv`. `unchanged` in place of
`downloaded` for `oppexp` is fine: FEC has not changed the zip since 2026-11-21, so step 4's spending line is the
reference's to the cent. FEC rewrites `committee_summary_2024.csv` daily, so it is usually `downloaded`. Under a
minute. `--file` writes no `extracted` marker, as intended.

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

The raw log is kept: its JSON lines hold the spending line and the `memory after <step>` lines (NEU-2408), which
the plain output leaves out.

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens transform --cycle 2024 --build-id "$B" 2>&1 | tee transform-raw.log | grep -v '^{' | tee transform.log
mk transformed "$B" | tee transformed.json
jq -rn --slurpfile o ref-transformed.json --slurpfile n transformed.json '$n[0].row_counts | to_entries[] | select($o[0].row_counts[.key] != .value) | "\(.key): \($o[0].row_counts[.key] // "none") -> \(.value)"'
grep -o '"message": "operating_expenditure 2024[^"]*"' transform-raw.log | tee spending-line.txt
```

**Expected:** a `<table>: <n> rows` line per silver table, then `wrote …` lines and a `transformed` marker. Then the
tables whose row count differs from the reference's, which should be at most two:

```
reported_total: <about 13994> -> <about 13994>
operating_expenditure: 2246038 -> <about 2246038>
```

`reported_total` moves with NEU-2454 and today's `committee_summary`. `operating_expenditure` moves only if step 2
downloaded a new `oppexp`. Any other line, a v1 table such as `contribution` or `committee`, means transform did not
read what the reference read: stop, and go back to step 1.3's list.

Then the spending line: `operating_expenditure 2024: <rows> rows, <counted> counted, $<dollars> counted, $<u> (<p>%)
unclassified`. With `oppexp` unchanged, it is the reference's line of the Facts exactly. With a new file, expect
counted rows and dollars within 1% of the reference's 1,550,225 and $9,594,284,292.22 (spec §5.1). The unclassified
share is the classifier's check on purposes nobody labelled: 3.78% on the reference, against the 10% bar (spec §5.3).
Over 10% is a defect in the classifier: file a Bug ticket with the line, link it from NEU-2160, and stop. Write the
line in the Log.

**Estimated:** about 31 min. A failed check stops the run before anything is uploaded. The traceback names the
`sql/checks/silver_*.sql` file whose query returned rows, and Bugsink gets an issue tagged `pipeline_mode=transform`.
The four `silver_operating_expenditure_*.sql` checks are the ones this table adds (spec §5.1). File a Bug ticket with
the check's name and a few of its rows, link it from NEU-2160, and stop. The live build is untouched.

### 4.1 Memory, against NEU-2149's estimate

```bash
# VM, in tmux
docker exec -i "$(fl pipeline)" python -c '
import json, sys
for line in sys.stdin:
    if line.startswith("{"):
        entry = json.loads(line)
        if entry["message"].startswith("memory after "):
            print(entry["ts"][11:19], entry["message"][13:])' < transform-raw.log | tee memory.txt
tail -1 memory.txt
peak=$(tail -1 memory.txt | grep -o 'peak resident [0-9.]* GiB'); grep -m1 "$peak" memory.txt
grep 'spilled' memory.txt | grep -v ' 0.00 GiB spilled' | head -1
grep -E '^[0-9:]+ (views|silver (candidate_reported_total|operating_expenditure|contribution)|write (operating_expenditure|contribution)) 2024' memory.txt
```

**Expected:**

1. The last line: the process's peak resident memory over the whole transform (`VmHWM`). 27.44 GiB on the
   reference; within about 2 GiB of it is the run-to-run spread [capacity.md](../capacity.md) records. Above
   29.80 GiB means the transform went past DuckDB's limit and lived on spill: write it in the Log, and file a
   ticket against the memory budget.
2. The first step whose line carries that peak: **the step that set it**. `write contribution 2024` on the
   reference.
3. The first step at which DuckDB held spilled bytes, if any.
4. The baseline and the five lines the estimate is read from. `operating_expenditure`'s own cost is DuckDB's
   in-memory figure after `silver operating_expenditure 2024` less the figure after `silver
   candidate_reported_total 2024`: 0.68 GiB on the reference, against NEU-2149's 0.87 GiB. After `write
   operating_expenditure 2024` DuckDB's figure falls back to the earlier one: the table is gone before
   `contribution`'s write.

Write all four in the Log, beside NEU-2149's estimate (27.35 GiB peak, 0.87 GiB table). Step 11 adds the row to
`docs/capacity.md`.

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
attach: …
overrides: …
adjudications: …
crosswalk: 0 new donors, 0 keys re-pointed, 0 redirects
model 20261116T224205Z: the live model, untrained
…
DuckDB memory limit: 29.8 GiB
```

`0 new contributor keys`: NEU-2401 reads repeated `indiv` rows once, so this build's keys are those of the live
build or fewer, every one already in the crosswalk. New keys mean transform read other files: stop, and go back to
step 1.3. A `warning: … keys that stood were re-pointed` line means an override or verdict new since the last
`--full`: the run can go on, but write it in the Log and do [weekly.md](weekly.md)'s re-resolving with `--full`
afterwards. Then a `resolved` marker for `<B>`. About 8 min.

If it stops with exit 1 and a message, [weekly.md](weekly.md)'s *A run missed* says what each one means.

## 6. Load

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens load --cycle 2024 --build-id "$B" 2>&1 | grep -v '^{' | tee load.log
mk loaded "$B" | jq '{step, duration_s}'
```

**Expected:** a `<table>: <n> rows` line per gold table, with `committee_spending_category`, `committee_top_payee`,
`payee`, `payee_cycle`, `payee_top_payer` and `reconciliation` among them, each larger than in the live gold, which
holds 2026's alone. Then `quality: precision …` with `/v1/meta`'s figures, a `resolution: release <sha>, <o>
overrides, <a> adjudications applied` line, and `loaded build <B> into gold_build (aggregates <a> s, copy <c> s)`.
That last line means every `sql/checks/gold_*.sql` passed, the four spending checks of spec §5.5 among them
(`gold_committee_spending_category_total.sql`, `gold_committee_top_payee_amount.sql`,
`gold_payee_top_payer_amount.sql`, `gold_payee_page.sql`). A failed check leaves no `gold_build` and names the
check: file a Bug ticket with its rows, link it from NEU-2160, and stop. Then a `loaded` marker. About 28 min: a
load rebuilds gold from every cycle's live build, this cycle's from `<B>`.

## 7. Check the figures before publishing

Both builds are in Postgres now: `gold` is the live gold and `gold_build` is `<B>`. Nothing is live yet.

### 7.1 Ten committees against FEC

The script copies the `committee_summary_2024.csv` transform read out of bronze into a temporary directory, and
sets gold's spending figures beside the file's:

```bash
# VM, in tmux
docker exec -i "$(fl pipeline)" python - <<'PY' 2>&1 | grep -v '^{' | tee comparisons.txt
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

import psycopg

from fundlens import paths
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform import runner

# The Facts' ten, in their order.
COMMITTEES = [
    "C00840017", "C00264697", "C00703975", "C00853473", "C00835959",
    "C00571703", "C00494021", "C00003418", "C00010603", "C00401224",
]
GROUPS = {"H": "candidate", "S": "candidate", "P": "candidate", "X": "party", "Y": "party", "O": "super PAC",
          "U": "super PAC"}
settings = get_settings()
store = R2.from_settings(settings)
summary = CATALOGUE["committee_summary"]


def amount(column):
    return f"CAST(nullif(trim({column}), '') AS DECIMAL(16, 2))"


def shown(value):
    return "—" if value is None else f"{value:,.2f}"


work = Path(tempfile.mkdtemp())
try:
    print("read", sorted(store.list_keys(paths.bronze_dir(2024, summary.name)))[-1])
    text = runner.fetch_bulk(store, 2024, summary, data_dir=settings.data_dir, work=work)
    con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
    # Form 3 and 3P fill OP_EXP, Form 3X TTL_OP_EXP (09_reported_total.sql). A committee's rows can repeat, one per
    # CAND_ID, or span two periods (NEU-2454): `figures` counts the distinct ones.
    fec = {row[0]: row[1:] for row in con.execute(
        "SELECT CMTE_ID, count(DISTINCT figure), max(figure) FROM ("
        f" SELECT CMTE_ID, CASE WHEN {amount('OP_EXP')} IS NOT NULL OR {amount('TTL_OP_EXP')} IS NOT NULL"
        f"  THEN coalesce({amount('OP_EXP')}, 0) + coalesce({amount('TTL_OP_EXP')}, 0) END AS figure"
        f" FROM read_csv({runner.literal(text)}, header = true, all_varchar = true))"
        " WHERE list_contains(?, CMTE_ID) GROUP BY CMTE_ID", [COMMITTEES]).fetchall()}
    with psycopg.connect(settings.database_url) as conn:
        build_rows = {row[0]: row[1:] for row in conn.execute(
            "SELECT committee_id, c.name, c.type, cc.total_operating_expenditures,"
            " cc.reported_operating_expenditures"
            " FROM gold_build.committee_cycle AS cc JOIN gold_build.committee AS c USING (committee_id)"
            " WHERE cc.cycle = 2024 AND committee_id = ANY(%s)", (COMMITTEES,)).fetchall()}
    print("\n| Id | Name | Group | Counted (fundlens) | Reported (gold) | FEC's file | Equal | Counted ÷ reported"
          " | Reported − counted |")
    print("| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: |")
    equal = over = 0
    for committee in COMMITTEES:
        name, kind, counted, reported = build_rows.get(committee, ("(not in gold)", None, None, None))
        figures, figure = fec.get(committee, (0, None))
        same = figures == 1 and reported == figure
        equal += same
        ratio = f"{counted / reported:.2%}" if counted is not None and reported else "—"
        gap = shown(reported - counted) if counted is not None and reported is not None else "—"
        over += counted is not None and reported is not None and counted - reported > Decimal("0.01") * reported
        listed = shown(figure) if figures <= 1 else f"{shown(figure)} ({figures} figures)"
        print(f"| {committee} | {name} | {GROUPS.get(kind, 'other')} | {shown(counted)} | {shown(reported)}"
              f" | {listed} | {'yes' if same else 'NO'} | {ratio} | {gap} |")
    print(f"\ncomparisons: {len(COMMITTEES)}; reported equal to the file: {equal}; counted over reported by more"
          f" than 1%: {over}")
finally:
    shutil.rmtree(work)
PY
```

**Expected,** in a minute or two: `read bronze/cycle=2024/committee_summary/<step 2's date>.csv`, then ten rows in
the Facts' order, each with a counted figure, a reported one and `yes`. Then `comparisons: 10; reported equal to the
file: 10; counted over reported by more than 1%: <n>`, with `<n>` 2 on the measurement's figures: Nez and
CatholicVote. Copy the table into the Log.

A `NO` is a defect in `reported_total` or gold: it reads FEC's figure as something other than the file's. A row
showing `(2 figures)` is a committee the file lists over two periods: gold should hold the cycle-to-date one
(NEU-2454), so check it against the row whose `CVG_START_DT` is earliest before calling it a defect. File a defect as
a Bug ticket with the row, link it from NEU-2160, and stop before `publish`.

Every row needs a line in the Log that explains its gap against Q11. Each is one of:

- **Within the unitemized.** Counted a little under reported, at about the group's Q11b median or above:
  candidates 99.20%, super PACs 99.49%, others 98.14%. The gap is payments of $200 or less a year to one payee,
  which FEC's figure holds and the file does not itemize. Explained; say so with the ratio.
- **A party's line 21(a).** The RNC and DNC sit well under 1 (the parties' Q11b dollar-weighted figure is
  83.83%): `oppexp` holds no row on Form 3X line 21(a), the shared federal and nonfederal spending, which
  `TTL_OP_EXP` includes (spec §5.2). FEC's `/totals/` endpoint gives that line:

  ```bash
  # laptop. C is the party's committee id.
  C=C00003418
  curl -sS "https://api.open.fec.gov/v1/committee/$C/totals/?cycle=2024&api_key=DEMO_KEY" | jq '.results[0] | with_entries(select(.key | test("operating_expenditures")))'
  ```

  **Expected:** the committee's operating-expenditure fields, the shared federal and nonfederal ones among them.
  The row is explained if its *Reported − counted* is about the shared federal and nonfederal figures added
  together, the remainder within the unitemized. Write both figures in the Log.
- **Counted above reported.** Nez and CatholicVote: Q11d listed them, undiagnosed, as the two largest excesses,
  $306,953 and $199,517. Diagnose each now, report by report. `OVER` holds the committees to diagnose. First where fundlens's counted
  money sits:

  ```bash
  # VM, in tmux
  OVER="C00853473 C00494021"
  docker exec -i "$(fl pipeline)" python - "$B" $OVER <<'PY' 2>&1 | grep -v '^{' | tee -a over-detail.txt
  import sys

  from fundlens import paths
  from fundlens.r2 import R2
  from fundlens.settings import get_settings
  from fundlens.transform import runner

  build, committees = sys.argv[1], sys.argv[2:]
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
  for committee in committees:
      print(committee)
      con.sql(
          "SELECT report_type, amendment_indicator AS amndt, file_num, count(*) AS rows,"
          " sum(amount) FILTER (WHERE counted) AS counted, count(*) FILTER (WHERE NOT counted) AS not_counted,"
          " min(date) AS first, max(date) AS last"
          f" FROM {parquet('operating_expenditure')} WHERE committee_id = ? GROUP BY ALL ORDER BY first, file_num",
          params=[committee],
      ).show(max_width=250, max_rows=100)
  PY
  ```

  Then what FEC's reports say, period by period:

  ```bash
  # laptop. The same committees.
  OVER="C00853473 C00494021"
  for C in $OVER; do echo "$C"; curl -sS "https://api.open.fec.gov/v1/committee/$C/reports/?cycle=2024&per_page=100&api_key=DEMO_KEY" | jq -r '.results[] | [.report_type, .report_year, .file_number, .amendment_indicator, .most_recent, .coverage_end_date, (to_entries | map(select(.key | test("operating_expenditures_period$"))) | map("\(.key)=\(.value)") | join(" "))] | @tsv'; done
  ```

  **Expected:** for each committee, a row per filing fundlens counted, and a row per report FEC holds. Read them against each other, as
  NEU-2147's reconciliation was read:
  - **Two filings of one report counted.** A report type with two filing numbers in the first output, both
    counted, where FEC's second output has one of them as `most_recent` false. That is a superseded filing
    `contribution`'s set does not name, the payment-side rule spec §5.1 did not adopt (Q6e). Explained if the
    excess is that filing's counted dollars; name it in the Log. Not a Bug: §5.1 measured the rule and rejected
    it.
  - **FEC's figure lags.** The excess is a filing dated after the summary's period, or one FEC's summary has not
    folded in. Explained; name the filing.
  - Anything else: a Bug ticket in NEU with both outputs, linked from NEU-2160.

  Neither stops the run: reconciliation never fails a build (spec §5.6).
- **The handoff.** `C00703975`'s row is the committee's whole, Biden's and Harris's spending together, against the
  committee's whole reported figure: it compares like the other campaigns. The candidate split is §5.5's and is not
  compared here.

### 7.2 The spending reconciliation

```bash
# VM
pg <<'SQL' | tee reconciliation.txt
select measure, count(*) as rows, sum(fundlens - reported) as excess, count(*) filter (where ratio is null) as reported_zero
from gold_build.reconciliation where cycle = 2024 group by measure order by measure;
select r.committee_id, c.name, c.type, r.fundlens, r.reported, round(r.ratio::numeric, 4) as ratio,
    r.fundlens - r.reported as excess
from gold_build.reconciliation r join gold_build.committee c using (committee_id)
where r.cycle = 2024 and r.measure = 'operating_expenditures'
order by excess desc, r.committee_id
limit 20;
SQL
```

**Expected:**

- Two rows. `operating_expenditures`: about 75 rows, Q11's 63 committees over by about $1.09M and about 12 with a
  reported $0 beside counted money (spec §5.6). `individual_itemized`: near NEU-2147's 163, fewer if NEU-2400 to
  NEU-2402 took their committees off. Not a gate: write both rows in the Log.
- The 20 largest spending excesses, Nez and CatholicVote first if Q11d still holds. Set the list beside Q11d's in
  the Log: a committee in the top 20 that Q11d lacks, by more than $50,000, is the one to diagnose: paste step 7.1's
  two `OVER` blocks with `OVER="<its id>"`, and read them as 7.1 says. Reconciliation never fails a build, so none of this stops the run.

### 7.3 What else moved

The receipt-side fixes since the live build (Facts) move some 2024 receipt figures. They are recorded here, not
checked:

```bash
# VM
pg <<'SQL' | tee moved.txt
select count(*) filter (where o.committee_id is null or n.committee_id is null) as missing,
    count(*) filter (where o.itemized_total is distinct from n.itemized_total) as itemized_moved,
    sum(n.itemized_total - o.itemized_total) as itemized_change
from (select * from gold.committee_cycle where cycle = 2024) o
full join (select * from gold_build.committee_cycle where cycle = 2024) n using (committee_id);
select committee_id, o.itemized_total as live, n.itemized_total as new
from gold.committee_cycle o join gold_build.committee_cycle n using (committee_id, cycle)
where cycle = 2024 and committee_id in ('C00808998', 'C00834424', 'C00041269') order by committee_id;
select o.total_amount as live, n.total_amount as new from gold.cycle o join gold_build.cycle n using (cycle)
where cycle = 2024;
SQL
```

**Expected:** `missing` 0. Then how many 2024 committees' itemized totals moved, and by how much in all. Then the
three committees NEU-2147's reconciliation filed (NEU-2400 DemocracyFirst, NEU-2401 Williamson, NEU-2402 the
Georgia party), each lower in `new` than in `live`. Then 2024's `cycle.total_amount`, which spending never enters
(spec §5.5): it moves only with NEU-2401's repeated rows. Write all three outputs in the Log. A committee `missing`
means the two builds' committees differ, which no change since the live build explains: stop, and file a Bug ticket.

## 8. Publish

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens publish --cycle 2024 --build-id "$B" 2>&1 | grep -v '^{' | tee publish.log
mk published "$B" | jq '{step, duration_s}'
gmeta
live
pg -Atc "select count(total_operating_expenditures) from gold.committee_cycle where cycle = 2024"
```

**Expected:** `published build <B> of 2024`, `previous build: 20261119T212247Z`, `cloudflare purge: done`,
`wrote resolution/build=<B>/crosswalk.parquet` and `pruned <n> silver builds (<m> objects)`. Prune removes only
builds older than `20261119T212247Z`: never the live build, nor the one before it. Then a Kuma line (Facts). Then:

- a `published` marker;
- `gold` naming `<B>` and model `20261116T224205Z`, `published_at` now; `gold_prev` the `gold` line of step 1.2;
- `markers/live.json` with 2024 at `<B>`, every other cycle as in step 1.2;
- the 2024 committees with spending, about 8,800: Q11's 9,909 with a reported figure less the 1,114 of them with no
  `oppexp` row, and about a dozen more with a reported $0 or none (Q11c).

About 3 min: the purge waits 75 s after the swap on purpose (spec §5.5). The merge freeze holds until step 10's
review has run: it is a `docker exec` on `pipeline` too.

**If a check in step 9 fails.** Roll back:

```bash
# VM
docker exec "$(fl pipeline)" fundlens publish --rollback
```

**Expected:** `rolled back: build <step 1.2's gold> is live`, then `build <B> is now gold_prev`. 2024 has no spending
again and its pages say "not available", as before the run; 2026's spending is unaffected, since the rollback
target holds it. File a Bug ticket with the failed check's output and link it from NEU-2160.

## 9. Verify

### 9.1 The API serves the build

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/meta?nocache=$(date +%s)" | jq '{build_id, published_at, model_version}'
curl -sS "https://api.fundlens.org/v1/committees/C00840017?nocache=$(date +%s)" | jq '{name, c: [.cycles[] | select(.cycle == 2024) | {total_operating_expenditures, reported_operating_expenditures: .reported.operating_expenditures, spending_by_category, top_payees: .top_payees[:5]}]}' | tee ~/fundlens-spending-run-committee.json
curl -sS "https://api.fundlens.org/v1/committees/C00840017/expenditures?cycle=2024&nocache=$(date +%s)" | jq '{rows: (.expenditures | length), next: (.next_cursor != null), first: .expenditures[0]}'
```

**Expected:** `build_id` `<B>`, `published_at` now, model `20261116T224205Z`. Then Alsobrooks's 2024: the counted
and reported figures of step 7.1's first row, a `spending_by_category` list adding up to the counted figure, most
first, and five top payees, each with a `payee_id`, or `null` for a person or a name like petty cash. Then the
itemized list's first page, `next` true, and its first row a payment with a payee, a category and `counted`. Copy
the total, the categories and the five payees into the Log. Note the first top payee with a `payee_id`: step 9.2
opens its page.

```bash
# laptop. P is the payee_id noted above.
P=<payee_id>
curl -sS "https://api.fundlens.org/v1/payees/$P?cycle=2024&nocache=$(date +%s)" | jq '{display_name, payee_key, total_all_cycles, first_cycle, last_cycle, cycles, payers: [.top_payers[:5][] | {rank, committee_id, committee_name, amount}], alsobrooks: [.top_payers[] | select(.committee_id == "C00840017") | {rank, amount}]}'
N=$(curl -sS "https://api.fundlens.org/v1/payees/$P" | jq -r .display_name); echo "$N"
curl -sS --get "https://api.fundlens.org/v1/search" --data-urlencode "q=$N" --data-urlencode "kind=payee" | jq '.[:3]'
```

**Expected:** the payee, with a 2024 row in `cycles` (and a 2026 row, if 2026's committees paid it), `first_cycle`
2024 or earlier, its five largest 2024 payers, and `alsobrooks` holding Alsobrooks's rank and amount. An empty
`alsobrooks` means the committee is not among the payee's 100 largest 2024 payers (`25_payee_top_payer.sql`): note
the next top payee with a `payee_id` from step 9.1's list instead, and run this block with it. Then its display name, and search by it: the
payee first, its `id` `<P>`. Copy both into the Log.

### 9.2 The pages

Open `https://fundlens.org/committee/C00840017` in a browser and choose 2024 if it is not shown.

**Expected:** a **Spending** section reading "Operating expenditures in 2024: <step 9.1's total>", with **By
category** (a chart of step 9.1's categories), **Top payees** (step 9.1's names, linked where they have a page) and
**Itemized spending** (payments, newest first, a category filter and a card bill's charges listed under it). A page
that still says "not available" is served from an old cache: reload with the cache bypassed (Shift-reload) once.
If it still does, go back to step 9.1.

Click the top payee noted in step 9.1.

**Expected:** `/payee/<P>`, headed with the payee's display name, "<total> paid by committees <first>–<last>", a
**Totals by cycle** chart and table with a 2024 row, and **Paid by** for 2024 listing ALSOBROOKS FOR SENATE at step 9.1's
rank. This is the ticket's definition of done. Write what both pages show in the Log.

### 9.3 Signals

- **Bugsink** → `fundlens`: no new `pipeline` issue since step 2, and no new `api` issue since step 8. A `pipeline`
  issue is from a step that crashed and was run again: note it in the Log, then resolve it. An `api` issue after the
  publish means a route reads something gold does not have: read it before anything else.

## 10. The payee review

The top 2024 payees, read by eye, on the live gold and the build's silver (spec §5.4). Nothing here stops anything:
each finding is a Bug ticket or a line for `fec/payee_no_page.csv`, and step 11 says which.

```bash
# VM, in tmux
docker exec -i "$(fl pipeline)" python - "$B" <<'PY' 2>&1 | grep -v '^{' | tee payee-review.md
import sys
from decimal import Decimal

import psycopg

from fundlens import paths
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.settings import get_settings
from fundlens.transform import runner

build = sys.argv[1]
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


with psycopg.connect(settings.database_url) as conn:
    pages = dict(conn.execute("SELECT payee_key, payee_id FROM gold.payee").fetchall())
con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
con.execute(f"CREATE TEMP VIEW oe AS SELECT * FROM {parquet('operating_expenditure')}")
# The rows payee figures read (22_payee.sql's payee_row): counted, with a key, no in-kind outlay.
con.execute("CREATE TEMP VIEW payee_row AS SELECT * FROM oe WHERE counted AND payee_key IS NOT NULL AND NOT is_in_kind")


def cell(value):
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    return str(value).replace("|", "\\|")


def table(title, sql, params=None):
    """Print a query as a Markdown table; a `payee_key` column gets its page beside it."""
    cursor = con.execute(sql, params or [])
    names = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    keyed = "payee_key" in names
    print(f"\n**{title}** ({len(rows)} rows)\n")
    print("| " + " | ".join(names + (["page"] if keyed else [])) + " |")
    print("|" + " --- |" * (len(names) + keyed))
    for row in rows:
        cells = [cell(value) for value in row]
        if keyed:
            cells.append(pages.get(row[names.index("payee_key")]) or "no page")
        print("| " + " | ".join(cells) + " |")


SPELLINGS = """
spelling AS (
    SELECT payee_key, payee_name, sum(amount) AS d,
        row_number() OVER (PARTITION BY payee_key ORDER BY sum(amount) DESC, payee_name) AS n
    FROM payee_row WHERE payee_key IN (SELECT payee_key FROM k) GROUP BY payee_key, payee_name),
names AS (
    SELECT payee_key, string_agg(payee_name || ' (' || format('{:,.0f}', d) || ')', '; ' ORDER BY n)
        FILTER (WHERE n <= 6) AS spellings
    FROM spelling GROUP BY payee_key)"""

table("A. The top 20 payees of 2024: wrong merges", f"""
WITH k AS (
    SELECT payee_key, sum(amount) AS dollars, count(DISTINCT committee_id) AS committees,
        count(DISTINCT payee_name) AS spellings, count(DISTINCT payee_state) AS states,
        round(100 * coalesce(sum(amount) FILTER (WHERE payee_is_person), 0) / sum(amount), 1) AS person_pct
    FROM payee_row GROUP BY payee_key ORDER BY dollars DESC, payee_key LIMIT 20),
{SPELLINGS}
SELECT k.*, names.spellings AS top_spellings FROM k JOIN names USING (payee_key) ORDER BY dollars DESC, payee_key""")

FIRMS = [["AX MEDIA", "AXMEDIA"], ["TEAM DIRECT", "TEAMDIRECT"],
         ["MISSIONWIRED", "ANNE LEWIS STRATEGIES", "ANNE LEWIS STRATEGIES LLC DBA MISSIONWIRED"]]
for firm in FIRMS:
    keys = sorted({key for key in map(normalize.organization_key, firm) if key})
    table(f"B. The measurement's split firm {' / '.join(firm)}: keys {keys}", """
        SELECT payee_key, sum(amount) AS dollars, count(DISTINCT committee_id) AS committees
        FROM payee_row WHERE list_contains(?, payee_key) GROUP BY payee_key ORDER BY dollars DESC""", [keys])
table("B. Other split firms among the top 1,000 keys: one key with its spaces taken out, or DBA", """
WITH k AS (SELECT payee_key, sum(amount) AS dollars FROM payee_row GROUP BY payee_key
           ORDER BY dollars DESC, payee_key LIMIT 1000),
j AS (SELECT payee_key, dollars, replace(regexp_replace(payee_key, ' DBA .*', ''), ' ', '') AS joined FROM k)
SELECT joined, payee_key, dollars FROM j
WHERE joined IN (SELECT joined FROM j GROUP BY joined HAVING count(*) > 1) OR payee_key LIKE '% DBA %'
ORDER BY joined, dollars DESC""")

# 12_operating_expenditure.sql's structural arm: a BACK_REF_TRAN_ID naming another row, with no parent in the file.
STRUCTURAL = ("nullif(nullif(trim(back_ref_tran_id), ''), nullif(trim(tran_id), '')) IS NOT NULL"
              " AND parent_source_record_id IS NULL")
table("C. In-kind outlays: the structural rule and the purpose pattern, counted rows", f"""
SELECT CASE WHEN {STRUCTURAL} THEN 'structural' ELSE 'purpose only' END AS arm,
    count(*) AS rows, sum(amount) AS dollars
FROM oe WHERE counted AND is_in_kind GROUP BY arm ORDER BY arm""")
table("C. The 20 largest counted rows the purpose pattern alone flags: its precision", f"""
SELECT committee_id, payee_name, entity_type, purpose, memo_text, amount FROM oe
WHERE counted AND is_in_kind AND NOT ({STRUCTURAL})
ORDER BY amount DESC, source_record_id LIMIT 20""")
# Words a gift received is written in, on a payee row the purpose pattern did not flag.
GIFT = (r"regexp_matches(upper(coalesce(purpose, '') || ' ' || coalesce(memo_text, '')), 'IN[- ]?KIND|INKND|IN KND"
        r"|NOT LIQUIDATED|\bUSDC\b|BITCOIN|CRYPTO|DONATED|NON-?CASH|GOODS RECEIVED|SERVICES RECEIVED"
        r"|CONTRIBUTION RECEIVED|RECEIVED AS')")
table("C. Every payee row that reads as a gift received, against all payee rows: how rare a miss is", f"""
SELECT count(*) FILTER (WHERE {GIFT}) AS gift_rows, sum(amount) FILTER (WHERE {GIFT}) AS gift_dollars,
    count(*) AS payee_rows, sum(amount) AS payee_dollars
FROM payee_row""")
table("C. The 20 largest of them: what the pattern missed", f"""
SELECT committee_id, payee_name, payee_key, entity_type, purpose, memo_text, amount FROM payee_row
WHERE {GIFT}
ORDER BY amount DESC, source_record_id LIMIT 20""")

table("D. Keys with a page whose name may name nobody: for fec/payee_no_page.csv", r"""
WITH k AS (SELECT payee_key, sum(amount) AS dollars, count(DISTINCT committee_id) AS committees,
               count(*) AS rows
           FROM payee_row GROUP BY payee_key)
SELECT payee_key, dollars, committees, rows FROM k
WHERE regexp_matches(payee_key, 'UNITEMIZ|PETTY|\bCASH\b|\bATM\b|VARIOUS|PAYROLL|\bSEE\b|\bMEMO\b|\bVENDORS\b|^NONE$|^N ?A$|UNKNOWN|REQUESTED|MULTIPLE|\bSTAFF\b|EMPLOYEES|INDIVIDUALS|WITHDRAW|^BANK$|\bDEBIT\b|AGGREGATE|^SAME$|^SELF$|^CANDIDATE$|REIMBURSE')
ORDER BY dollars DESC, payee_key LIMIT 40""")
PY
```

**Expected,** in a few minutes, Markdown tables in `payee-review.md`. Rows marked `no page` in D are already off the
pages and need nothing. Read each table:

- **A, wrong merges.** For each of the 20: do the spellings name one business? A key that groups two firms (two
  unrelated names that normalize alike, or one name used by two firms in different states) is a **wrong merge**:
  file a Bug ticket in NEU for each, titled with the key, its spellings and their dollars from the table. The
  measurement found none in the top 100 (Q9b). `AMERICAN EXPRESS`, ActBlue and WinRed are among the top keys by
  design (spec §5.4): a card issuer's total is bills, and a conduit's is fees. A high `person_pct` on a key with a
  page means its person rows are under half of its dollars over every cycle (spec §5.4): a firm paid under a
  person's name, a known gap (spec §5.5). Write each of the 20 as one Log line: the key, its dollars, and "one firm"
  or the Bug.
- **B, split firms.** For each of the measurement's three, two or three keys with their dollars: file a **Bug
  ticket for each firm** that adds an alias to `src/fundlens/resolve/aliases.yaml`. Its canonical name is the key
  with the most dollars, and the other spellings go under it (spec §5.4). Say in the ticket that an alias regroups
  employers and organizations too (ADR-0011, ADR-0012), and that it takes effect at the next transform. Then the
  other pairs among the top 1,000: each pair that is one firm is a Bug ticket the same way; a pair that is two
  firms is a line in the Log.
- **C, in-kind outlays.** The two arms' rows and dollars: spec §5.4 measured about $20.2M structural (7,284
  parentless sub-items: $18,833,378 naming a receipt and $1,327,593 not) and $53.3M on the `IN-KIND CONTRIBUTION`
  purpose alone. Then the pattern's precision: each of the 20 rows names an in-kind gift (its
  payee is the giver), or it does not (a payment that mentions in-kind, such as a fee for handling one). Write the
  count of the 20 that are gifts in the Log: it replaces spec §5.4's "asserted, not measured" in step 11. Then the
  misses: the count is every payee row whose words read as a gift, an upper bound on the misses, beside all payee
  rows; the 20 largest are read. Each that is a gift received is an in-kind outlay the pattern missed, on a payee
  page as money paid. Write in the Log how many of the 20 are gifts, their dollars, and the bound against payee
  dollars: that is how rare a miss is, the second half of spec §5.4's note. File one Bug ticket for the misses
  together, with the rows and a pattern that would catch them.
- **D, names that name nobody.** Each key whose name names no payee (`UNITEMIZED …`, `PETTY CASH`, `VARIOUS
  VENDORS`, a cash withdrawal) is a line for `fec/payee_no_page.csv`, written in step 11 with its `reason`. A key
  that is a real firm or person despite its name (`VARIOUS PRESSURES` may be a firm, spec §5.4) is left alone. Say
  which in the Log.

Link every Bug ticket from NEU-2160. None of them stops the run: spec §5.5 counts split firms and a firm paid under
a person's name as known gaps, not defects of the gold tickets.

Nothing runs on `pipeline` after this, so merging to `main` is safe again:

```bash
# laptop
gh workflow enable dependencies --repo neuroticsasquat-ch/fundlens
```

**Expected:** no output; Dependabot's auto-merge runs on its schedule again.

## 11. Record the run

Gather the run's identifiers and step times in one file:

```bash
# VM
{
  date -u +%Y-%m-%d
  docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES | sed 's/.*service.version=/sha /; s/,.*//'
  echo "live before $OLD"
  echo "build $B"
  cat extract.log
  for s in transformed resolved loaded published; do mk "$s" "$B" | grep -E '"step"|"duration_s"'; done | paste - - | tr -d ' ,"'
  cat spending-line.txt
  tail -1 memory.txt
  grep -E 'new contributor keys|^crosswalk:' resolve.log
  grep -E '^(committee_spending_category|committee_top_payee|payee|payee_cycle|payee_top_payer|reconciliation): ' load.log
  free_gb
} | tee run-record.txt
```

The braces stay outside the quotes, so the laptop's shell expands them into one `hetzner-01:` path per file. Since
OpenSSH 9, `scp` copies over SFTP, which does not expand braces in a remote path:

```bash
# laptop
mkdir -p ~/fundlens-spending-run
cd ~/fundlens-spending-run
scp hetzner-01:fundlens-spending-run/{run-record.txt,bronze-before.txt,transformed.json,memory.txt,comparisons.txt,reconciliation.txt,moved.txt,payee-review.md} .
scp hetzner-01:fundlens-spending-run/over-detail.txt . 2>/dev/null || echo "no over-detail"
```

**Expected:** `run-record.txt` holds the date, the SHA, the two builds, step 2's two lines, four `step:<name>`
lines with their `duration_s`, the spending line, the last memory line, resolve's two lines, the six spending and
payee tables' row counts and the free disk. The other files are the output of steps 1.3, 4, 7 and 10.

Append a Log entry from them, headed `### <date> — 2024 with spending and payees (NEU-2160)`:

- the date, the SHA, build `<B>` (live before: `20261119T212247Z`), step 2's and `seats`' `real`, the four marker
  step times, and the two files' bronze keys from step 2;
- step 4's spending line, and the tables whose row count moved from the reference's;
- step 4.1's four figures, set beside NEU-2149's estimate: the peak against 27.35 GiB, and the table's own DuckDB
  figure against 0.87 GiB;
- step 5's `new contributor keys` and `crosswalk:` lines;
- step 7.1's table and its `comparisons:` line, with a line per row explaining its gap against Q11 (the unitemized,
  the party's line 21(a) with FEC's figures, or the diagnosis of an excess);
- step 7.2's two measure rows and its top 20 set beside Q11d;
- step 7.3's three outputs;
- steps 9.1 and 9.2: Alsobrooks's total, categories and top payees, the payee's figures and payers, and what both
  pages showed;
- step 10's review: the 20 keys, one line each; the split firms with their Bug tickets; the in-kind arms, the
  pattern's precision (how many of the 20 are gifts) and the misses; the no-page names added and those left alone;
- every deviation, each filed as a ticket and linked from NEU-2160.

In the same PR:

- **`docs/capacity.md`:** a Per cycle row for `<B>`: its date and SHA; step 2's and `seats`' `real` as Extract s and
  Seats s; transform, load and publish from their markers, load as `<total> (<aggregates> + <copy>)` from load's last
  line (resolve has no column there); and as peak the process's peak resident memory from step 4.1, which is the process's own figure, not a
  sampler's. Its note: "First published 2024 build with `operating_expenditure` (NEU-2160). DuckDB held <x> GiB for the
  table against NEU-2149's 0.87 GiB estimate; the peak <y> GiB against its 27.35 GiB, set in <step>."
- **`src/fundlens/fec/payee_no_page.csv`:** step 10 D's names, one `payee_key,reason` row each, the reason in the
  file's own words ("Names no payee: …"). They take effect at the next load: the Sunday run.
- **`docs/specs/fundlens-every-fec-dollar-project-spec.md` §5.4:** the in-kind bullet's "**Asserted, not
  measured:** the pattern's precision, and that a purpose avoiding the words … is rare; NEU-2160's payee review
  checks both" becomes what step 10 C measured, citing this Log.

Open one PR, `docs(runbooks): log the 2024 spending run (NEU-2160)`, with the entry. Merging it redeploys
`pipeline`, which is safe now that nothing is running.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-22 — 2024 with spending and payees (NEU-2160)

Run 2026-11-22 20:26 to 23:31 UTC. Started on `bc60bbce14215fd80d76a6f6b6e8e1c9fb2fce66`, and from step 2 on
`f4ad07f090ee978b5905e1d561efe8b2bbacf7c9` (below). Build `20261122T205402Z`; live before: `20261120T212246Z`.
`gold_prev` after publish: `20261122T030019Z`, 2026's build as reloaded at 18:48 UTC, with 2026's spending, so a
rollback stays safe.

**The Facts were stale in two places.**

- **2024's live build was `20261120T212246Z`, not `20261119T212247Z`.** No Log records it. It started at 21:22 UTC
  on 2026-11-20, after NEU-2402 merged at 20:48, and its `transformed` marker equals the reference's on every v1
  table (`contribution` 50,085,820), so NEU-2400 to NEU-2402 were already live. Step 7.3 therefore expected
  nothing to move, and nothing did.
- **`gold` had been reloaded at 18:48 UTC** with the same 2026 build `gold_prev` held.

**Deviation: nameparser re-keyed contributors (NEU-2458).** Step 1.2's markers differed on `contributor`: 5,504,651
on the live build, 5,504,466 on the reference. Dependabot's group bump `ddff7ef` (2026-11-21) had moved
nameparser from 3.0.1 to 3.1.0. It reads dotted initials differently (`SHROLL, C.J.`: `SHROLL, CJ` →
`SHROLL, C J`; `KELSEY, T.D.`: `KELSEY` → `KELSEY, T D`), and so re-keyed 11,198 2024 contributions: 1,749 keys
only in the live build, 1,753 only in the reference. Step 5's gate would have stopped on about 1,750 new keys.
PR #225 pinned `nameparser==3.0.1`, added a test that fails on 3.1.0, and set Dependabot to ignore it. It merged
at 20:48 UTC, before step 2, and the run continued on `f4ad07f`. 2026's live build was transformed on 3.1.0; its
next weekly transform gives the 3.0.1 keys back.

**Bronze.** The v1 files were the live build's: `cm`, `cn`, `ccl` of 2026-11-15; `indiv`, `pas2`, `oth` of
2026-11-16; `weball`, `webk` of 2026-11-19. Downloaded: `bronze/cycle=2024/oppexp/2026-11-22.zip` and
`bronze/cycle=2024/committee_summary/2026-11-22.csv`.

| Step | Time | Notes |
| --- | ---: | --- |
| extract | 26.2 s | `oppexp` and `committee_summary` |
| seats | 5.2 s | 441 House, 35 Senate (2 special), 1 presidential race; 49 unmatched filings |
| transform | 1854.7 s (31m0s) | only `contributor` moved from the reference, back to the live build's 5,504,651 |
| resolve | 421.0 s (7m7s) | `0 new contributor keys of 5504651`; crosswalk 0 new donors, 0 re-pointed, 0 redirects |
| load | 1766.0 s (29m32s) | aggregates 852.91 s, copy 883.45 s; every gold check passed |
| publish | 144.6 s (2m36s) | pruned 1 silver build (267 objects) |

**Spending line:** `operating_expenditure 2024: 2,246,038 rows, 1,550,225 counted, $9,594,284,292.22 counted,
$362,505,186.62 (3.78%) unclassified`. It is identical to the reference's on FEC's 2026-11-22 zip, and to spec
§5.1's derived 1,550,225 rows and $9,594,284,292. The unclassified share is 3.78%, against the 10% bar. Load:
`committee_spending_category` 91,646, `committee_top_payee` 273,858, `payee` 93,386 (51,507 before),
`payee_cycle` 112,497, `payee_top_payer` 231,201, `reconciliation` 385 rows. 8,821 committees have 2024 spending.
167 GB free after publish.

**Memory (step 4.1), against NEU-2149's estimate.** Peak resident 28.53 GiB, set in `write contribution 2024`, 1.27
GiB under DuckDB's 29.80 GiB limit: the reference's 27.44 GiB plus 1.09, inside the 2 GiB run-to-run spread, and
NEU-2149's estimated 27.35 GiB plus 1.18. The table held 0.69 GiB in DuckDB (19.43 → 20.12 GiB across
`silver operating_expenditure 2024`), against the estimate's 0.87. It was gone (19.43 GiB) after its write,
before `contribution`'s. DuckDB first spilled 0.42 GiB in `write contribution`. All 83 lines logged. NEU-2455's
falling peak (PR #221, held during the run) did not occur: the peak only rose.

**Step 7.1, ten committees against FEC** (`read bronze/cycle=2024/committee_summary/2026-11-22.csv`):

| Id | Name | Group | Counted (fundlens) | Reported (gold) | FEC's file | Equal | Counted ÷ reported | Reported − counted |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| C00840017 | ALSOBROOKS FOR SENATE | candidate | 30,482,880.86 | 30,486,006.44 | 30,486,006.44 | yes | 99.99% | 3,125.58 |
| C00264697 | DIGNITY OF WORK PAC | other | 97,460,584.55 | 97,467,283.58 | 97,467,283.58 | yes | 99.99% | 6,699.03 |
| C00703975 | FIGHT FOR THE PEOPLE PAC | other | 1,153,258,804.61 | 1,154,387,275.14 | 1,154,387,275.14 | yes | 99.90% | 1,128,470.53 |
| C00853473 | JONATHAN NEZ FOR CONGRESS | candidate | 5,359,336.00 | 5,052,382.61 | 5,052,382.61 | yes | 106.08% | -306,953.39 |
| C00835959 | FAIRSHAKE | super PAC | 68,913,945.83 | 68,914,690.82 | 68,914,690.82 | yes | 100.00% | 744.99 |
| C00571703 | SLF PAC | super PAC | 18,069,706.89 | 18,070,266.21 | 18,070,266.21 | yes | 100.00% | 559.32 |
| C00494021 | CATHOLICVOTE.ORG CANDIDATE FUND | super PAC | 321,708.24 | 122,191.24 | 122,191.24 | yes | 263.28% | -199,517.00 |
| C00003418 | REPUBLICAN NATIONAL COMMITTEE | party | 246,620,959.33 | 254,881,719.72 | 254,881,719.72 | yes | 96.76% | 8,260,760.39 |
| C00010603 | DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE | party | 420,805,013.05 | 432,917,394.22 | 432,917,394.22 | yes | 97.20% | 12,112,381.17 |
| C00401224 | ACTBLUE | other | 87,074,366.99 | 87,074,366.99 | 87,074,366.99 | yes | 100.00% | 0.00 |

`comparisons: 10; reported equal to the file: 10; counted over reported by more than 1%: 2`. `gold.committee`
names a committee by its latest cycle. `C00264697` is Brown's 2024 Senate campaign and `C00703975` the
Biden-then-Harris committee, both since turned PACs and counted whole (spec §5.5). Each gap:

- **Within the unitemized:** Alsobrooks, Brown and Fairshake at 99.99–100.00%, SLF at 100.00%, the Biden/Harris
  committee at 99.90%, all above Q11b's group medians. ActBlue is exact.
- **Nez, +$306,953.39.** On the same eight filings FEC lists as most recent, the filer's itemized line 17 exceeds
  its own summary on the 12G 2024 (`1842067`: $1,195,143.66 against $1,096,187.77, +$98,955.89) and the 30G 2024
  (`1858999`: $1,669,033.51 against $1,455,401.62, +$213,631.89). The other six reports are $5,634.39 under,
  within the unitemized. The filer's summary disagrees with its own Schedule B; fundlens counts the Schedule B
  as filed.
- **CatholicVote, +$199,517.00.** Seven reports match FEC's period figures within $483 in all. On the 30G 2024
  (`1859042`), FEC's summary is −$233,861.28, while the four itemized rows net −$33,861.28. The filer reversed the
  12G's $250,000 to Schedule E on its summary, but itemized only RumbleUp's −$50,000 ("IE PAID 10/8, SEE SCH E").
- **RNC 96.76% (−$8,260,760.39) and DNC 97.20% (−$12,112,381.17): a gap in FEC's bulk file.** Step 7.1's "party's
  line 21(a)" explanation does not fit national committees. FEC's `/totals/` gives both $0.00 shared federal and
  nonfederal spending, so their figure is line 21(b) alone. Their uncounted memo rows net to about $0 (the RNC's
  HQ and convention transfers to itself), and sub-items do not track the gaps. Small itemized rows hold
  $2,000–11,000 a month, so the gap is not unitemized payments. Silver equals FEC's raw `oppexp` (read through
  `register_bulk`) on all 48 filings to the cent, and the repeated-row rule drops nothing. FEC's bulk file holds
  less than FEC's own summaries: the RNC $208K–$841K short on every report from M2 2023 to M5 2024 and exact from M6
  2024; the DNC $36K–$2.02M short to M2 2024 (and on M5 2024), within a few hundred dollars from M6 2024. A gap in
  FEC's bulk data, for §9's raw filings to recover.

**Step 7.2, reconciliation:**
- `operating_expenditures`: 79 rows, $1,123,069.57 over, 11 at a reported $0 (spec §5.6: 63 over by $1.09M,
  plus about 12). The top 20 are Q11d's 20, in Q11d's order, with Q11d's excesses, so none needed diagnosing.
- `individual_itemized`: 150 rows, $50,312,619.95 over, 23 at a reported $0. NEU-2147 had 163 rows and
  $55,349,367.42; NEU-2400 to NEU-2402 took 13 off.

**Step 7.3, what else moved: nothing.** 2024's `committee_cycle`: 0 missing, 0 `itemized_total` and 0
`total_individual` moved, $0.00 in all. DemocracyFirst, Williamson and the Georgia party are equal in both golds.
`cycle` 2024 is $9,970,861,678 over 50,085,820 contributions, and there are 12,564,389 donors, both the same in
both golds. Spending enters no receipt total.

**Steps 9.1 to 9.3.**
- `/v1/meta` served `20261122T205402Z`.
- Alsobrooks's 2024: $30,482,880.86 in 15 categories summing to it, media $18,083,857.26 first. Top payees
  GRASSROOTS MEDIA $16,429,616.69, BREAK SOMETHING INC $3,861,818.06, WAVELENGTH STRATEGY LLC $2,379,000.00, GUSTO
  $2,140,663.90 and RWT PRODUCTIONS $725,854.24, each with a page. Her itemized list pages by 100.
- `/payee/c18850fc2fa9d913` (GRASSROOTS MEDIA, Bala Cynwyd PA): $143,249,030.40 over 2024–2026, of it 2024
  $135,292,306.40 from 9 committees. Its 2024 payers are Brown, Casey, Baldwin, then ALSOBROOKS FOR SENATE 4th at
  $16,429,616.69. Payee search finds it first, with `GRASSROOTS MEDIA LLC; GRASSROOTS MEDIA, LLC`.
- Both pages showed this in the browser.
- Bugsink: nothing new.

**Step 10, the payee review.**

- **Wrong merges: none in the top 20.** Each key groups one firm's spellings, and none is a person
  (`person_pct` 0.0):
  - MEDIA BUYING ANALYTICS $333.8M, STRATEGIC MEDIA SERVICES $287.2M, AMERICAN EXPRESS $195.2M (631 committees)
  - GAMBIT STRATEGIES $176.1M, SCREEN STRATEGIES MEDIA $142.7M, GRASSROOTS MEDIA $135.3M
  - ACTBLUE TECHNICAL SERVICES $125.7M, TARGETED VICTORY $123.3M, DUPONT CIRCLE STRATEGIES $122.6M
  - BULLY PULPIT INTERACTIVE $114.7M, GUSTO $113.1M, META $107.0M (holding `FACEBOOK` through the employer alias)
  - WINRED TECHNICAL SERVICES $97.2M, AL MEDIA $93.3M, GOOGLE $88.0M, ONMESSAGE $85.4M
  - MOTHERSHIP STRATEGIES $83.1M, LAUNCHPAD STRATEGIES $79.6M, MISSIONWIRED $72.0M, FLEXPOINT MEDIA $70.8M
- **Split firms.**
  - The measurement's three are confirmed, each filed: NEU-2460 (`AX MEDIA` $44.1M, `AXMEDIA` $18.9M), NEU-2461
    (`TEAM DIRECT` $27.9M, `TEAMDIRECT` $20.0M), NEU-2462 (MissionWired).
  - MissionWired has a fourth key: `MISSIONWIRED` $72.0M, `ANNE LEWIS STRATEGIES` $22.8M, `… LLC DBA MISSIONWIRED`
    $18.7M and `MISSION WIRED` $11.6M.
  - Nine more space splits are one ticket, NEU-2463, rather than one per firm, since each is a line in the same
    file: `ON MESSAGE`, `SKD KNICKERBOCKER`, `WIN RED TECHNICAL SERVICES`, `WIN RED`, `ACT BLUE TECHNICAL
    SERVICES`, `BRABENDER COX`, `DONOR BUREAU`, `ABDATA` and `GRASS ROOTS MEDIA`. NEU-2463 also lists five DBA keys
    to check.
- **In-kind outlays (spec §5.4's two assertions).**
  - The structural rule flags 6,973 counted rows ($19,625,238), and the pattern alone 14,454 ($139,958,524).
  - Precision: of the pattern's 20 largest rows, 16 are gifts. They include Coinbase's $23.0M of bitcoin and
    $15.5M of USDC, two "petition incentives" rows of $40.5M and $11.2M, and candidates' own in-kind. Three are
    payments the committee made, $1,339,000 together: "IN-KIND CONTRIBUTION MADE: POLLING" to House Majority PAC,
    and two SEIU "ADVANCE PAYMENT FOR FUTURE INDEPENDENT EXPENDITURES & IN-KIND CONTRIBUTIONS". One is unclear:
    RYFF INC., "IN-KIND: GOTV ADVERTISING", $410,000.
  - Misses: at most 1,000 payee rows and $27,585,850.38 read as a gift received, 0.29% of $9,434,666,487.83. But all
    20 of the largest are crypto received that the pattern misses. Coinbase's `24,999,995 USDC RECEIVED, NOT
    LIQUIDATED` shows on its payee page as $24,999,995 paid.
  - Both directions are filed as NEU-2464.
- **No-page names.** `THE PAYROLL` ($816,512, one committee) is added to `fec/payee_no_page.csv` in this PR.
  - The other 27 `… PAYROLL …` keys with a page are payroll processors (Payroll Data Processing $37.4M, ADP, Paychex, Gusto Payroll
    Services and others), and keep them.
  - So do the card issuers' product names (`AM EX SIMPLY CASH`, `CITI BANK DOUBLE CASH`), the union pension
    funds and the employee associations.

**Deviations, each filed:** NEU-2458 (nameparser, fixed in the run); NEU-2460, NEU-2461, NEU-2462, NEU-2463 (split
firms); NEU-2464 (in-kind pattern). The RNC and DNC gap is FEC's bulk file, so nothing is filed. Dependabot was
re-enabled after step 10.
