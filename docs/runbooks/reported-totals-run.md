# Runbook: the 2024 production run with reported totals

How to put reported totals live on real data (NEU-2147; every-FEC-dollar spec §4). Extract FEC's three summary
files for 2024, transform a new 2024 build with `reported_total`, load gold with its reported fields, coverage,
`reconciliation` and `candidate_gift_size`, and publish it. Check fifteen figures against FEC's
`committee_summary_2024.csv`, record the `reconciliation` table and disposition its top ten, and check that no
itemized total moved. Run it once, top to bottom, on `music-box-dancer`, one step at a time. Append to the
[Log](#log) at the bottom; never rewrite it.

**Why now.** NEU-2142 to NEU-2146 are merged, and since 2026-11-19 gold has every reported column. But no live build
has a `reported_total` partition: 2024's live build was transformed on 2026-11-16, before NEU-2143. Load reads a
backfill-pending table as having no rows (spec §2, older builds), so every reported field on fundlens.org is NULL
and every page says "not reported". This run gives 2024 its partition. Every other cycle waits for NEU-2180's
backfill.

**Why only the summary files are extracted.** 2024's live build read `indiv`, `pas2` and `oth` as FEC published them
on 2026-11-16. A full extract would download them again with FEC's amendments since, and step 7.2 could not tell
an amendment from a bug. `extract --file` downloads only the three new files, so transform reads every v1 file
exactly as the live build did. Step 1.3 checks that. The summary files are then a few days newer than the itemized
ones, which moves a 2024 coverage figure by no more than FEC's late amendments do.

**Why no `run`.** `fundlens run --from transform` would still run `extract` in full, because this build has no
`extracted` marker. The steps are run one by one, as `run` orders them.

**Not in this runbook:** cycles before 2024 and 2026 (NEU-2180's backfill), the dataset snapshot (Sunday's
`run --dataset` takes it), and the spending tables (NEU-2160).

## Before you start

- NEU-2146 (`e681faa`, PR #193) is merged, and so is this runbook. Step 1.1 checks that the deployed code includes
  it.
- **Nothing merges to `main` from step 2 until step 8 has printed its last line.** Every merge redeploys
  `pipeline` and kills a running `docker exec`. On 2026-11-02 a docs merge killed a `publish` part way. Step 1.1
  turns Dependabot's auto-merge off.
- Not within 4 h of Sunday 03:00 UTC: the scheduled `fundlens weekly` task runs then, and two pipeline runs at once
  do not fit the box.
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo, `gh`
  and `jq` are installed, and you can sign in to Bugsink (`https://bugsink.neuroticsasquat.ch`) and Linear.
- Allow about two hours. Transform took 1,728 s on 2024's live build, and the load and publish of every cycle
  1,402 + 157 s ([`docs/capacity.md`](../capacity.md)).

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycle | `2024` |
| 2024's live build before this run | `20261116T005426Z`, transformed from `1250468` (NEU-2324), resolved under model `20261116T224205Z` ([backfill.md](backfill.md) Log, 2026-11-16 and 2026-11-17). 50,104,322 contributions |
| Silver and transform changes since | `47907ef` (NEU-2138, CSV files), `6b9e88a` (NEU-2142, the catalogue), `1945501` (NEU-2143, `reported_total` and `candidate_reported_total`), `d0421ec` (NEU-2144, which reads them). None of them changes a v1 table |
| New silver | `reported_total`: one row per 2024 committee of `committee_summary`, 13,994 on FEC's file of 2026-11-18 (spec §4.1; the measurement's Q1i). `candidate_reported_total`: 0 rows from 2008 (spec §4.2) |
| The fifteen comparisons | Ten candidates: `S4MD00327`, the ticket's, and the nine House and Senate candidates of 2024 with the most reported receipts whose figures include no converted committee. Five committees: `S4MD00327`'s principal committee, two super PACs (`C00835959` Fairshake, `C00571703` Senate Leadership Fund) and two party committees (`C00003418` RNC, `C00010603` DNC) |
| What a comparison checks | The source file, which should be `committee_summary`, and twelve measures (the reporting period, `receipts`, `disbursements`, `cash_on_hand_start`, `cash_on_hand_end`, `debts_owed_by`, `individual_itemized`, `individual_unitemized`, `individual_total`, `candidate_loans`, `other_loans`) against the `committee_summary_2024.csv` transform read. A committee's are its row. A candidate's are the sum over the rows the file links to the candidate with designation P or A, which for a candidate with no handoff and no converted committee are the committees fundlens credits (spec §4.3) |
| What the spec leaves to this run | The coverage counts on the gross basis (spec §4.4: on the net basis, 5,114 committees within 1% of FEC's itemized figure, 802 of them super PACs) and the `reconciliation` row count (spec §4.5: 71 committees, $10,791,881, on the net basis after NEU-2276). Step 10 writes the measured figures into the spec |
| Monitors | `fundlens/publish` gets a push from `publish`. If the monitor is still paused, `publish` ends with `kuma push (up) failed: HTTPError: HTTP Error 404: Not Found`: the paused monitor refusing the push, not a fault |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-reported
```

In the tmux session, define the helpers. Paste the whole block:

```bash
# VM, in tmux
mkdir -p ~/fundlens-reported-run && cd ~/fundlens-reported-run
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

**Expected:** no output. If the tmux session is lost, run `tmux attach -t fundlens-reported`. If the session itself
is gone, paste the helpers again, `cd ~/fundlens-reported-run`, and export what earlier steps saved:
`export OLD=$(cat old-build.txt)` from step 1.2 on and `export B=$(cat build-id.txt)` from step 3 on.

## 1. Preflight

### 1.1 The deployed code, and the merge freeze

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
git merge-base --is-ancestor e681faa "$SHA" && echo "reported totals deployed"
git log --oneline 1250468.."$SHA" -- sql/silver src/fundlens/transform src/fundlens/fec src/fundlens/resolve/normalize.py
gh workflow disable dependencies --repo neuroticsasquat-ch/fundlens
gh pr list --repo neuroticsasquat-ch/fundlens --state open
```

**Expected:** `service.version=<sha>` and `32GB`; `postgres: ok`, `r2: ok`, `exit=0`. Then the SHA, `reported totals
deployed`, and exactly the four commits of the Facts: `d0421ec`, `1945501`, `6b9e88a`, `47907ef`. If the `deployed`
line is missing: Coolify → the `fundlens` resource → *Deploy*, wait for it to finish, and run this step again. A
fifth commit changed silver since the live build, so step 7.2 would blame its differences on reported totals: stop
and find out what it changes. Then no output from `gh workflow disable`, and the open PRs: none of them merges
until step 8 is done. Write the SHA in the Log.

### 1.2 The live state

```bash
# VM
gmeta
live
live | grep -o "2024: '[0-9TZ]*'" | grep -o '[0-9]\{8\}T[0-9]\{6\}Z' | tee old-build.txt
export OLD=$(cat old-build.txt)
mk transformed "$OLD" | tee old-transformed.json
pg -Atc "select count(*), count(reported_receipts) from gold.committee_cycle where cycle = 2024"
docker exec "$(fl pipeline)" python -c 'from fundlens.r2 import R2; from fundlens.resolve import runner; from fundlens.settings import get_settings; s = get_settings(); print("incremental ready" if runner.incremental_ready(R2.from_settings(s), s.data_dir) else "NOT READY")' 2>&1 | grep -v '^{'
free_gb
```

**Expected:**

- `gold` and `gold_prev` lines, `gold`'s `published_at` on or after 2026-11-19, when gold was reloaded with
  NEU-2144's columns. Write both lines in the Log: `gold_prev` is what step 8's rollback would not reach, and
  `gold` is what it would.
- `markers/live.json` with 2024 at `20261116T005426Z`, and `old-build.txt` holding it. Another build means someone
  published 2024 since the Facts were written: stop, and read [backfill.md](backfill.md) and
  [weekly.md](weekly.md)'s Logs to find out what it is.
- A `transformed` marker whose `row_counts` has `contribution: 50104322` and no `reported_total`.
- Two numbers: the 2024 committees in gold, and `0`. A reported figure in 2024 already means a 2024 build with
  `reported_total` is live: stop and find out which.
- `incremental ready`, and at least 100 GB free: `transform` can spill up to 60 GB of DuckDB scratch
  (`DUCKDB_MAX_TEMP_DIRECTORY_SIZE`). With less, free some first.

Then what the site serves for the ticket's candidate before the run:

```bash
# laptop
curl -sS -o /dev/null -w "S4MD00327 %{http_code}\n" "https://api.fundlens.org/v1/candidates/S4MD00327?nocache=$(date +%s)"
curl -sS "https://api.fundlens.org/v1/candidates/S4MD00327?cycle=2024&nocache=$(date +%s)" | jq '{name, c: [.cycles[] | select(.cycle == 2024) | {reported, itemized_total, coverage, buckets: [.gift_sizes[].bucket]}]}'
```

**Expected:** `S4MD00327 200`, then the candidate's name and 2024 with `reported: null`, an `itemized_total`,
`coverage: null` and five buckets, `unitemized` not among them. A 500 instead means the live gold predates NEU-2144:
step 7.2 reads its tables in `gold`, so stop, and reload gold first with [weekly.md](weekly.md)'s re-resolving with
`--full`, step 5 alone (`fundlens run --cycle 2026 --build-id <2026's live build> --from load`, about 30 min), as on
2026-11-19.

### 1.3 Transform will read the live build's v1 files

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
`2026-11-16`, the live build's extract. `weball`, `webk` and `committee_summary` may say `NONE`, or a date from
NEU-2142's or NEU-2143's prod checks: step 2 downloads them again. A v1 file dated after 2026-11-16 means someone
extracted 2024 since the live build. Transform would read FEC's amendments since, and step 7.2 would find totals
moved. Stop and find out who; going on means step 7.2's expectation becomes "moved by the new files only", which is
a decision for the ticket, not this runbook.

## 2. Extract the summary files

```bash
# VM, in tmux
for f in weball webk committee_summary; do docker exec "$(fl pipeline)" fundlens extract --cycle 2024 --file "$f" 2>&1 | grep -v '^{'; done | tee extract.log
```

**Expected:** three lines, `weball: downloaded bronze/cycle=2024/weball/<today>.zip`, the same for `webk`, and
`committee_summary: downloaded bronze/cycle=2024/committee_summary/<today>.csv`. `unchanged` in place of
`downloaded` is fine for `weball` and `webk`: FEC has not changed the zip since an earlier download. FEC rewrites
`committee_summary_2024.csv` daily, so it is usually `downloaded`. Under a minute. `--file` writes no `extracted`
marker, as intended.

## 3. Seats

`transform` reads the unmatched filings `seats --report` records, and `load` reads the `race` partition of the same
build. Fix the build ID here:

```bash
# VM, in tmux
export B=$(date -u +%Y%m%dT%H%M%SZ)
echo "$B" | tee build-id.txt
time docker exec "$(fl pipeline)" fundlens seats --cycle 2024 --report --build-id "$B" 2>&1 | grep -v '^{' | tee seats.log
```

**Expected:** `house: 441 races (0 special)`, `senate: 35 races (2 special)`, `president: 1 races (0 special)`,
`wrote silver/race/cycle=2024/build=<B>/…`, and the unmatched filings recorded, as in every 2024 run since
NEU-2324. Under a minute.

## 4. Transform

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens transform --cycle 2024 --build-id "$B" 2>&1 | grep -v '^{' | tee transform.log
mk transformed "$B" | tee transformed.json
jq -rn --slurpfile o old-transformed.json --slurpfile n transformed.json '$n[0].row_counts | to_entries[] | select($o[0].row_counts[.key] != .value) | "\(.key): \($o[0].row_counts[.key] // "none") -> \(.value)"'
```

**Expected:** a `<table>: <n> rows` line per silver table, then `wrote …` lines and a `transformed` marker. Then the
tables whose row count differs from the live build's, which should be exactly two:

```
candidate_reported_total: none -> 0
reported_total: none -> <about 13994>
```

`reported_total` is the 2024 committees of `committee_summary` that are silver committees: 13,994 on FEC's file of
2026-11-18, a few more or fewer on today's. Any other line, a v1 table such as `contribution` or `committee`, means
transform did not read what the live build read: stop, and go back to step 1.3's list.

**Estimated:** about 30 min. A failed check stops the run before anything is uploaded. The traceback names the
`sql/checks/silver_*.sql` file whose query returned rows, and Bugsink gets an issue tagged `pipeline_mode=transform`.
`silver_reported_total_repeat.sql` is the one this run adds: a committee whose repeated rows differ in more than
`CAND_ID` and `Link_Image` (spec §4.1). File a Bug ticket with the check's name and a few of its rows, link it from
NEU-2147, and stop. The live build is untouched.

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

`<k>` is the `contributor` count of both `transformed` markers. `0 new contributor keys` follows from step 4: the
same `indiv` gives the same keys, every one already in the crosswalk. New keys mean transform read other files:
stop, and go back to step 1.3. A `warning: … keys that stood were re-pointed` line means an override or verdict new
since the last `--full`: the run can go on, but write it in the Log and do [weekly.md](weekly.md)'s
re-resolving with `--full` afterwards. Then a `resolved` marker for `<B>`. Write its `duration_s` in the Log: no
2024 incremental resolve has been timed.

If it stops with exit 1 and a message, [weekly.md](weekly.md)'s *A run missed* says what each one means.

## 6. Load

```bash
# VM, in tmux. The open-file limit is raised for this command alone until NEU-2399 sets it on the container.
time docker exec "$(fl pipeline)" sh -c 'ulimit -n 65536 && exec fundlens load --cycle 2024 --build-id "$1"' sh "$B" 2>&1 | grep -v '^{' | tee load.log
mk loaded "$B" | jq '{step, duration_s}'
```

**Expected:** a `<table>: <n> rows` line per gold table, `reconciliation` and `candidate_gift_size` among them. Then
`quality: precision …` with `/v1/meta`'s figures (not `quality: not validated for model …`), a `resolution: release
<sha>, <o> overrides, <a> adjudications applied` line, and `loaded build <B> into gold_build (aggregates <a> s, copy
<c> s)`. That last line means every `sql/checks/gold_*.sql` passed, `gold_committee_cycle_coverage.sql` and
`gold_candidate_gift_size_total.sql` among them. A failed check leaves no `gold_build` and names the check: file a
Bug ticket with its rows, link it from NEU-2147, and stop. Then a `loaded` marker. About 25 min: a load rebuilds
gold from every cycle's live build, this cycle's from `<B>`.

## 7. Check the figures before publishing

Both builds are in Postgres now: `gold` is the live gold and `gold_build` is `<B>`. Nothing is live yet.

### 7.1 Fifteen figures against FEC

The script copies the `committee_summary_2024.csv` transform read out of bronze into a temporary directory, and
sets gold's reported figures beside the file's:

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

CANDIDATE = "S4MD00327"
# Fairshake and Senate Leadership Fund (super PACs), then the RNC and the DNC.
COMMITTEES = ["C00835959", "C00571703", "C00003418", "C00010603"]


def amount(column):
    return f"CAST(nullif(trim({column}), '') AS DECIMAL(16, 2))"


# Gold's reported_<measure>; committee_summary's figure for it (every-FEC-dollar spec §4.1); and how a
# candidate's committees' figures combine (§4.3).
MEASURES = {
    "period_start": ("CAST(try_strptime(CVG_START_DT, '%Y%m%d') AS DATE)", "min"),
    "period_end": ("CAST(try_strptime(CVG_END_DT, '%Y%m%d') AS DATE)", "max"),
    "receipts": (amount("TTL_RECEIPTS"), "sum"),
    "disbursements": (amount("TTL_DISB"), "sum"),
    "cash_on_hand_start": (amount("COH_BOP"), "sum"),
    "cash_on_hand_end": (amount("COH_COP"), "sum"),
    "debts_owed_by": (amount("DEBTS_OWED_BY_CMTE"), "sum"),
    "individual_itemized": (amount("INDV_ITEM_CONTB"), "sum"),
    "individual_unitemized": (amount("INDV_UNITEM_CONTB"), "sum"),
    "individual_total": (amount("INDV_CONTB"), "sum"),
    "candidate_loans": (amount("CAND_LOAN"), "sum"),
    "other_loans": (
        f"coalesce({amount('OTH_LOANS')}, {amount('TTL_LOANS')} - coalesce({amount('CAND_LOAN')}, 0))", "sum"
    ),
}
RECEIPTS = list(MEASURES).index("receipts")
NONE = (None,) * len(MEASURES)
settings = get_settings()
store = R2.from_settings(settings)
summary = CATALOGUE["committee_summary"]


def shown(value):
    if value is None:
        return "—"
    return f"{value:,.2f}" if isinstance(value, Decimal) else str(value)


work = Path(tempfile.mkdtemp())
try:
    print("read", sorted(store.list_keys(paths.bronze_dir(2024, summary.name)))[-1])
    text = runner.fetch_bulk(store, 2024, summary, data_dir=settings.data_dir, work=work)
    con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
    figures = ", ".join(f"{figure} AS {measure}" for measure, (figure, _) in MEASURES.items())
    con.execute(
        f"CREATE TABLE cs AS SELECT CMTE_ID, CAND_ID, CMTE_DSGN, {figures}"
        f" FROM read_csv({runner.literal(text)}, header = true, all_varchar = true)"
    )
    principal = con.execute(
        "SELECT DISTINCT CMTE_ID FROM cs WHERE CAND_ID = ? AND CMTE_DSGN = 'P' ORDER BY CMTE_ID", [CANDIDATE]
    ).fetchall()
    committees = [row[0] for row in principal] + COMMITTEES
    columns = ", ".join(f"reported_{measure}" for measure in MEASURES)
    with psycopg.connect(settings.database_url) as conn:
        candidates = [CANDIDATE] + [row[0] for row in conn.execute(
            "SELECT candidate_id FROM gold_build.candidate_cycle JOIN gold_build.candidate USING (candidate_id)"
            " WHERE cycle = 2024 AND office IN ('H', 'S') AND reported_receipts IS NOT NULL"
            " AND NOT reported_includes_converted_committee AND candidate_id <> %s"
            " ORDER BY reported_receipts DESC, candidate_id LIMIT 9", (CANDIDATE,)).fetchall()]
        gold = {("candidate", row[0]): (row[1], row[2], row[3:]) for row in conn.execute(
            f"SELECT candidate_id, name, reported_source_file, {columns} FROM gold_build.candidate_cycle"
            " JOIN gold_build.candidate USING (candidate_id)"
            " WHERE cycle = 2024 AND candidate_id = ANY(%s)", (candidates,)).fetchall()}
        gold |= {("committee", row[0]): (row[1], row[2], row[3:]) for row in conn.execute(
            f"SELECT committee_id, name, reported_source_file, {columns} FROM gold_build.committee_cycle"
            " JOIN gold_build.committee USING (committee_id)"
            " WHERE cycle = 2024 AND committee_id = ANY(%s)", (committees,)).fetchall()}
    measures = ", ".join(MEASURES)
    fec = {("committee", row[0]): (row[0], row[1:]) for row in con.execute(
        f"SELECT CMTE_ID, {measures} FROM cs WHERE list_contains(?, CMTE_ID)"
        " QUALIFY row_number() OVER (PARTITION BY CMTE_ID ORDER BY CAND_ID) = 1", [committees]).fetchall()}
    combined = ", ".join(f"{combine}({measure})" for measure, (_, combine) in MEASURES.items())
    fec |= {("candidate", row[0]): (row[1], row[2:]) for row in con.execute(
        f"SELECT CAND_ID, string_agg(CMTE_ID, ' ' ORDER BY CMTE_ID), {combined}"
        f" FROM (SELECT DISTINCT CMTE_ID, CAND_ID, {measures} FROM cs"
        "  WHERE CMTE_DSGN IN ('P', 'A') AND list_contains(?, CAND_ID))"
        " GROUP BY CAND_ID", [candidates]).fetchall()}
    entities = [("candidate", c) for c in candidates] + [("committee", c) for c in committees]
    print("\n| | Id | Name | Source | FEC's committees | Receipts | Equal | Differing (gold / FEC) |")
    print("| --- | --- | --- | --- | --- | ---: | ---: | --- |")
    equal = 0
    for kind, entity in entities:
        name, source, ours = gold.get((kind, entity), ("(not in gold)", None, NONE))
        listed, theirs = fec.get((kind, entity), ("(not in the file)", NONE))
        differing = [f"{m} {shown(a)} / {shown(b)}" for m, a, b in zip(MEASURES, ours, theirs) if a != b]
        equal += not differing and source == "committee_summary"
        print(f"| {kind} | {entity} | {name} | {source} | {listed} | {shown(ours[RECEIPTS])}"
              f" | {len(MEASURES) - len(differing)} of {len(MEASURES)} | {'; '.join(differing)} |")
    print(f"\ncomparisons: {len(entities)}; from committee_summary and equal on every measure: {equal}")
finally:
    shutil.rmtree(work)
PY
```

**Expected,** in a minute or two: `read bronze/cycle=2024/committee_summary/<step 2's date>.csv`, then fifteen rows,
ten candidates and five committees, the first committee `S4MD00327`'s principal committee, each with source
`committee_summary` and `12 of 12`. Then `comparisons: 15; from committee_summary and equal on every measure: 15`.
Should FEC list two principal committees for `S4MD00327`, there are sixteen, and both are compared. Copy the table into the Log.

A row with measures differing is a finding, not yet a failure. Each one is one of:

- **A candidate whose committees differ from FEC's links.** fundlens credits linked P and A committees and the
  committee `principal_committee_id` names (spec §4.3); the file links by `CAND_ID`. List the new build's links and
  principal committee for the row's candidate, to set beside the row's *FEC's committees*:

  ```bash
  # VM, in tmux. C is the differing row's candidate id.
  C=<candidate id>
  docker exec -i "$(fl pipeline)" python - "$B" "$C" <<'PY' 2>&1 | grep -v '^{'
  import sys

  from fundlens import paths
  from fundlens.r2 import R2
  from fundlens.settings import get_settings
  from fundlens.transform import runner

  build, candidate = sys.argv[1:3]
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
  con.sql(
      f"SELECT 'linked' AS how, committee_id, designation, committee_type"
      f" FROM {parquet('candidate_committee_link')} WHERE candidate_id = ?"
      f" UNION ALL SELECT 'principal', principal_committee_id, NULL, NULL"
      f" FROM {parquet('candidate')} WHERE candidate_id = ? ORDER BY committee_id, how",
      params=[candidate, candidate],
  ).show(max_width=250)
  PY
  ```

  fundlens credits the `linked` committees with designation P or A and the `principal` one, unless a handoff or a
  lower `candidate_id` takes it (spec §4.3). The row is explained if its gap is exactly the figures of a committee
  one side has and the other lacks, and the credit rule says why. Write that in the Log.
- **A committee whose figure is gold's from `webk`.** Only a Form 5 or Form 7 filer takes `webk`'s figures (spec
  §4.1); none of the five is one. A committee row that differs is a defect.
- Anything else is a defect in silver or gold. File a Bug ticket with the row, link it from NEU-2147, and stop
  before `publish`. `gold` stays the live gold; the next `load` replaces `gold_build`.

### 7.2 No itemized total moved

The two golds should differ only in the new reported fields, coverage, `reconciliation` and the `unitemized` gift-size
rows. Every itemized figure, in every cycle, should be the same:

```bash
# VM
pg <<'SQL' | tee unmoved.txt
select 'committee_cycle' as tbl, count(*) filter (where o.committee_id is null or n.committee_id is null) as missing,
    count(*) filter (where (o.total_individual, o.self_funding, o.total_from_committees, o.total_from_organizations,
        o.total_non_contribution_account, o.total_other_lines, o.total_refunds, o.total_to_candidates,
        o.total_returned_by_candidates, o.ie_total, o.itemized_total)
      is distinct from (n.total_individual, n.self_funding, n.total_from_committees, n.total_from_organizations,
        n.total_non_contribution_account, n.total_other_lines, n.total_refunds, n.total_to_candidates,
        n.total_returned_by_candidates, n.ie_total, n.itemized_total)) as moved
from gold.committee_cycle o full join gold_build.committee_cycle n using (committee_id, cycle)
union all
select 'candidate_cycle', count(*) filter (where o.candidate_id is null or n.candidate_id is null),
    count(*) filter (where (o.total_individual, o.total_committee, o.total_jfc_transfers, o.self_funding, o.ie_support,
        o.ie_oppose, o.contributor_count, o.itemized_total)
      is distinct from (n.total_individual, n.total_committee, n.total_jfc_transfers, n.self_funding, n.ie_support,
        n.ie_oppose, n.contributor_count, n.itemized_total))
from gold.candidate_cycle o full join gold_build.candidate_cycle n using (candidate_id, cycle)
union all
select 'race', count(*) filter (where o.race_id is null or n.race_id is null),
    count(*) filter (where (o.candidate_count, o.total_individual, o.total_committee, o.total_jfc_transfers,
        o.ie_support, o.ie_oppose)
      is distinct from (n.candidate_count, n.total_individual, n.total_committee, n.total_jfc_transfers,
        n.ie_support, n.ie_oppose))
from gold.race o full join gold_build.race n using (race_id)
union all
select 'cycle', count(*) filter (where o.cycle is null or n.cycle is null),
    count(*) filter (where (o.race_count, o.contribution_count, o.total_amount)
      is distinct from (n.race_count, n.contribution_count, n.total_amount))
from gold.cycle o full join gold_build.cycle n using (cycle)
union all
select 'candidate_gift_size, itemized', count(*) filter (where o.candidate_id is null or n.candidate_id is null),
    count(*) filter (where (o.amount, o.donors) is distinct from (n.amount, n.donors))
from (select * from gold.candidate_gift_size where bucket <> 'unitemized') o
full join (select * from gold_build.candidate_gift_size where bucket <> 'unitemized') n using (candidate_id, cycle, bucket);
SQL
```

**Expected:** five rows, every `missing` and every `moved` `0`. Copy them into the Log.

A row that moved means money moved for a reason other than reported totals. List the rows that did, for the table
named, before anything else:

```bash
# VM
pg -c "select cycle, committee_id, o.total_individual as live, n.total_individual as new from gold.committee_cycle o full join gold_build.committee_cycle n using (committee_id, cycle) where o.total_individual is distinct from n.total_individual order by cycle, committee_id limit 20"
```

Stop here, before `publish`, file a Bug ticket with both outputs, and link it from NEU-2147.

### 7.3 Coverage and reconciliation

```bash
# VM
pg <<'SQL' | tee coverage.txt
select count(*) filter (where coverage is not null) as with_coverage,
    count(*) filter (where abs(coverage - 1) <= 0.01) as within_1pct,
    count(*) filter (where coverage > 1.01) as over_1pct,
    count(*) filter (where c.type = 'O' and coverage is not null) as super_pacs_with_coverage,
    count(*) filter (where c.type = 'O' and abs(coverage - 1) <= 0.01) as super_pacs_within_1pct
from gold_build.committee_cycle cc join gold_build.committee c using (committee_id)
where cc.cycle = 2024;
select count(*) as rows, sum(fundlens - reported) as excess, count(*) filter (where ratio is null) as reported_zero
from gold_build.reconciliation where cycle = 2024;
SQL
pg <<'SQL' | tee reconciliation-top10.txt
select r.committee_id, c.name, c.type, c.designation, r.fundlens, r.reported, round(r.ratio::numeric, 4) as ratio,
    r.fundlens - r.reported as excess, cc.total_individual, cc.total_from_organizations, cc.total_refunds,
    cc.reported_period_start, cc.reported_period_end
from gold_build.reconciliation r
join gold_build.committee c using (committee_id)
join gold_build.committee_cycle cc using (committee_id, cycle)
where r.cycle = 2024
order by excess desc, r.committee_id
limit 10;
SQL
```

**Expected:**

- A coverage row. `within_1pct` is the gross-basis count the spec leaves to this run, against 5,114 on the net
  basis; `super_pacs_within_1pct` against 802. Gross is FEC's own basis, so expect both at least as high. Write all
  five figures in the Log. `gold.committee.type` is a committee's type in its latest cycle, not necessarily 2024's,
  so a committee that became a super PAC after 2024, or stopped being one, is counted by its current type. Say so
  beside the super PAC figures in the Log.
- A reconciliation row: `rows`, the dollars over, and how many reported 0. `over_1pct` above equals `rows` less
  `reported_zero`; a committee that reported a negative itemized figure is listed but has no coverage over 1.01,
  which is the only other difference. The spec's figure on the net basis after NEU-2276 was 71 committees and
  $10,791,881. Gross adds each committee's refunds back, so more rows are plausible. Not a gate: write the figures
  in the Log.
- The top ten, the largest excess first.

Each of the top ten needs a disposition in the Log, either explained or filed. To see where a committee's itemized
money sits, this lists the new build's counted rows for the ten by report and filing:

```bash
# VM, in tmux
docker exec -i "$(fl pipeline)" python - "$B" <<'PY' 2>&1 | grep -v '^{' | tee reconciliation-detail.txt
import sys

import psycopg

from fundlens import paths
from fundlens.r2 import R2
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
    top = [row[0] for row in conn.execute(
        "SELECT committee_id FROM gold_build.reconciliation WHERE cycle = 2024"
        " ORDER BY fundlens - reported DESC, committee_id LIMIT 10").fetchall()]
con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
counted = (
    "recipient_committee_id, report_type, amendment_indicator, file_num, amount FROM {}"
    " WHERE NOT is_other_line AND NOT is_non_contribution_account AND list_contains(?, recipient_committee_id)"
)
con.sql(
    f"SELECT recipient_committee_id AS committee, report_type, amendment_indicator AS amndt,"
    f" count(*) AS rows, sum(amount) AS dollars, count(DISTINCT file_num) AS filings,"
    f" string_agg(DISTINCT CAST(file_num AS VARCHAR), ' ') AS file_nums"
    f" FROM (SELECT {counted.format(parquet('contribution'))} AND NOT is_self_funding"
    f"  UNION ALL SELECT {counted.format(parquet('organization_receipt'))})"
    f" GROUP BY ALL ORDER BY committee, report_type, amndt",
    params=[top, top],
).show(max_width=250, max_rows=300)
PY
```

**Expected:** for each of the ten, its counted rows by report type and amendment indicator, with the filings each
came from. Read each committee against the causes the measurement found:

- **Two filings of one report counted.** A report type listed with more than one filing number, an `N` and an `A`
  both counted, or two `A`s, is an amendment fundlens counted beside the filing it replaced: a defect
  (NEU-2192 to NEU-2199 fixed the patterns found so far). File it. A two-year cycle has two of most report types,
  though (M2 2023 and M2 2024, YE 2023 and YE 2024): before calling two filing numbers a double count, check each
  one's `report_year` against FEC's `/v1/committee/<id>/reports/?cycle=2024`.
- **Money on a line the bulk file does not show** (spec §4.4, Q6 after NEU-2276): fundlens counts it as 11(a)(i)
  where the filer reported it elsewhere. Explained; name the line.
- **FEC's figure lags an amendment:** the excess is the rows of a filing newer than `reported_period_end`, or one FEC
  has not yet folded into its summary. Explained; name the filing.

A committee none of these explains gets a Bug ticket in NEU with its rows from both outputs, linked from NEU-2147.
None of these stops the run: reconciliation never fails a build (spec §4.5).

### 7.4 The ticket's candidate in `gold_build`

```bash
# VM
pg -c "select bucket, amount, donors from gold_build.candidate_gift_size where cycle = 2024 and candidate_id = 'S4MD00327' order by array_position(array['unitemized', '200_or_less', 'under_500', 'under_1000', 'under_2000', '2000_or_more'], bucket)"
pg -c "select total_individual, itemized_total, reported_individual_itemized, reported_individual_unitemized, round(coverage::numeric, 4) as coverage, reported_source_file from gold_build.candidate_cycle where cycle = 2024 and candidate_id = 'S4MD00327'"
```

**Expected:** six buckets, `unitemized` first with `donors` empty, its `amount` the candidate's
`reported_individual_unitemized`; the five itemized amounts add up to `total_individual` (the gold check
`gold_candidate_gift_size_total.sql` made sure of it). Then one row with `reported_source_file` `committee_summary`
and a coverage near 1.

## 8. Publish

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" sh -c 'ulimit -n 65536 && exec fundlens publish --cycle 2024 --build-id "$1"' sh "$B" 2>&1 | grep -v '^{' | tee publish.log
mk published "$B" | jq '{step, duration_s}'
gmeta
live
pg -Atc "select count(reported_receipts) from gold.committee_cycle where cycle = 2024"
```

**Expected:** `published build <B> of 2024`, `previous build: 20261116T005426Z`, `cloudflare purge: done`,
`wrote resolution/build=<B>/crosswalk.parquet` and `pruned <n> silver builds (<m> objects)`. Prune removes only
builds older than `20261116T005426Z`: never the live build, nor the one before it. Then a Kuma line (Facts). Then:

- a `published` marker;
- `gold` naming `<B>` and model `20261116T224205Z`, `published_at` now; `gold_prev` the `gold` line of step 1.2;
- `markers/live.json` with 2024 at `<B>`, every other cycle as in step 1.2;
- the 2024 committees with a reported figure, about step 4's `reported_total` count.

About 3 min: the purge waits 75 s after the swap on purpose (spec §5.5). From here, merging to `main` is safe again:

```bash
# laptop
gh workflow enable dependencies --repo neuroticsasquat-ch/fundlens
```

**Expected:** no output; Dependabot's auto-merge runs on its schedule again.

**If a check in step 9 fails.** Roll back:

```bash
# VM
docker exec "$(fl pipeline)" fundlens publish --rollback
```

**Expected:** `rolled back: build <step 1.2's gold> is live`, then `build <B> is now gold_prev`. Every reported
field is NULL again and the pages say "not reported", as before the run. File a Bug ticket with the failed check's
output and link it from NEU-2147.

## 9. Verify

### 9.1 The API serves the build

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/meta?nocache=$(date +%s)" | jq '{build_id, published_at, model_version, precision, recall}'
curl -sS "https://api.fundlens.org/v1/candidates/S4MD00327?cycle=2024" | jq '{name, c: [.cycles[] | select(.cycle == 2024) | {reported, reported_includes_converted_committee, itemized_total, coverage, gift_sizes}]}' | tee ~/fundlens-reported-run-candidate.json
```

**Expected:** `build_id` `<B>`, `published_at` now, the model and figures of step 6's `quality:` line. Then the
candidate's 2024 with `reported` filled: `source_file` `committee_summary`, `period_start` and `period_end`, and the
figures step 7.1 compared, equal to its gold row; `reported_includes_converted_committee` false; `itemized_total`
and `coverage` as step 7.4's; six `gift_sizes`, `unitemized` first with `donors: null`. This is the ticket's
definition of done. Copy `reported.receipts`, `reported.cash_on_hand_end`, `coverage` and the six buckets into the
Log.

```bash
# laptop
curl -sS "https://api.fundlens.org/v1/reconciliation?cycle=2024" | jq '{rows: (.rows | length), next: (.next_cursor != null), first: .rows[0]}'
curl -sS "https://api.fundlens.org/v1/committees/C00835959?cycle=2024" | jq '.cycles[] | select(.cycle == 2024) | {reported: (.reported | {source_file, receipts, individual_itemized, cash_on_hand_end}), itemized_total, coverage}'
```

**Expected:** `rows` the smaller of 100 and step 7.3's row count, `next` true only when there are more than 100, and
`first` step 7.3's top row. Then Fairshake's 2024: `source_file` `committee_summary`, its receipts and itemized
figure as step 7.1 printed them, and a coverage. Most of Fairshake's money is organization money, which its
`itemized_total` counts (spec §4.4, Decision 4).

### 9.2 The candidate page

Open `https://fundlens.org/candidate/S4MD00327` in a browser and choose 2024 if it is not shown.

**Expected:**

- A **Reported to the FEC** section with `Reporting period <start> to <end> · source committee_summary`, then
  *Raised*, *Spent*, *Cash on hand*, *Debts*, *Loans from the candidate*, *Other loans*, *Unitemized from
  individuals* and *Itemized from individuals*, each a figure or "not reported", never `$0` for a blank. Then
  *Itemized by fundlens*, and the line "fundlens itemizes <n>% of the itemized individual money this campaign
  reported." with a Methodology link.
- A **Gift sizes** section whose chart has the unitemized bucket beside the five itemized ones.

A page that still says "not reported" everywhere is served from an old cache: reload with the cache bypassed
(Shift-reload) once. If it still does, go back to step 9.1. Write what the page shows in the Log, with its coverage
line as written.

### 9.3 A super PAC's page

Open `https://fundlens.org/committee/C00835959` and choose 2024.

**Expected:** a **Reported to the FEC** section with source `committee_summary` and the figures of step 9.1, and a
coverage line ending "this committee reported." Write the coverage in the Log.

### 9.4 Signals

- **Bugsink** → `fundlens`: no new `pipeline` issue since step 2, and no new `api` issue since step 8. A `pipeline`
  issue is from a step that crashed and was run again: note it in the Log, then resolve it. An `api` issue after the
  publish means a route reads something gold does not have: read it before anything else.

## 10. Record the run

Gather the run's identifiers and step times in one file:

```bash
# VM
{
  date -u +%Y-%m-%d
  docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES | sed 's/.*service.version=/sha /; s/,.*//'
  echo "live before $OLD"
  echo "build $B"
  for s in transformed resolved loaded published; do mk "$s" "$B" | grep -E '"step"|"duration_s"'; done | paste - - | tr -d ' ,"'
  grep -E 'new contributor keys|^crosswalk:' resolve.log
  grep -E '^(reconciliation|candidate_gift_size): ' load.log
  free_gb
} | tee run-record.txt
```

The braces stay outside the quotes, so the laptop's shell expands them into one `hetzner-01:` path per file. Since
OpenSSH 9, `scp` copies over SFTP, which does not expand braces in a remote path:

```bash
# laptop
mkdir -p ~/fundlens-reported-run
cd ~/fundlens-reported-run
scp hetzner-01:fundlens-reported-run/{run-record.txt,bronze-before.txt,extract.log,transformed.json,comparisons.txt,unmoved.txt,coverage.txt,reconciliation-top10.txt,reconciliation-detail.txt} .
```

**Expected:** `run-record.txt` holds the date, the SHA, the two builds, four `step:<name>` lines with their
`duration_s`, resolve's two lines, the two new gold tables' row counts and the free disk. The other files are the
output of steps 1.3, 2, 4 and 7.

Append a Log entry from them, headed `### <date> — 2024 with reported totals (NEU-2147)`:

- the date, the SHA, build `<B>` (live before: `20261116T005426Z`), the four step times, and the three summary files'
  bronze keys from step 2;
- step 4's `reported_total` count, and that no other table's count moved;
- step 5's `new contributor keys` and `crosswalk:` lines;
- step 7.1's table and its `comparisons:` line, with a line for each differing row;
- step 7.2's five rows;
- step 7.3's coverage figures, the reconciliation row count and dollars, and its top ten as a table with a
  disposition per row: the cause, or the Bug ticket filed;
- steps 9.1 to 9.3: the candidate's figures, coverage and buckets, the reconciliation endpoint's first row,
  Fairshake's coverage, and what both pages showed;
- every deviation, each filed as a ticket and linked from NEU-2147.

In the same PR, replace the two **Asserted, not measured** notes the spec leaves to this run with what step 7.3
measured, citing this Log: in `docs/specs/fundlens-every-fec-dollar-project-spec.md`, §4.4's coverage bullet ("the
counts on the gross basis; NEU-2147's runbook records them") and §4.5's last bullet ("the table's row count on a
current build; NEU-2147's runbook records it and dispositions its top ten").

Open one PR, `docs(runbooks): log the 2024 reported totals run (NEU-2147)`, with the entry. Merging it redeploys
`pipeline`, which is safe now that nothing is running.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-20 — 2024 with reported totals (NEU-2147)

Run 2026-11-19 21:01 to 2026-11-20 01:35 UTC on `6e01035a11c171cef169de7c2477879b708f1178`. Build `20261119T212247Z`;
live before: `20261116T005426Z`. `gold_prev` after publish: `20261117T030329Z`, which has NEU-2144's columns, so a
rollback stays safe.

**Bronze.** The v1 files were the live build's: `cm`, `cn`, `ccl` of 2026-11-15, `indiv`, `pas2`, `oth` of
2026-11-16. The summary files, none in bronze before, were downloaded:
`bronze/cycle=2024/weball/2026-11-19.zip`, `bronze/cycle=2024/webk/2026-11-19.zip`,
`bronze/cycle=2024/committee_summary/2026-11-19.csv`.

| Step | Time | Notes |
| --- | ---: | --- |
| seats | 5.5 s | 441 House, 35 Senate (2 special), 1 presidential race; 49 unmatched filings, all seats outside the calendar |
| transform | 1926.8 s (32m12s) | `reported_total` 13,994 rows, `candidate_reported_total` 0; no other table's count moved |
| resolve | 467.1 s (7m53s) | the first timed 2024 incremental resolve |
| load | 1695.1 s (28m20s) | the second attempt, below; aggregates 852.4 s, copy 820.2 s |
| publish | 158.9 s (2m50s) | pruned 2 silver builds (275 objects) |

Resolve: `0 new contributor keys of 5504651, 0 pairs scored at or above the match threshold`, `crosswalk: 0 new
donors, 0 keys re-pointed, 0 redirects`; overrides 1 merge, adjudications 130 verdicts (4 splits); live model
`20261116T224205Z`, untrained. Load: `reconciliation: 163 rows`, `candidate_gift_size: 224686 rows`, quality
precision 0.8122, recall 0.8993, as `/v1/meta` had. Disk free: 101 GB before, 97 after transform, 104 after load,
118 at the end.

**Load's first attempt failed** after 56m26s. Bugsink had a "too many open files" opening a parquet, and five minutes
later the first CSV copy died with `IOException: Cannot open file
"/data/fundlens/scratch/load-2024-20261119T212247Z/committee_cycle.csv": No such file or directory`. Every gold model
and check had passed, and Postgres was untouched. The container's soft `nofile` limit is 1024 (hard 524288), and the
local silver cache holds 7,062 parquet files. The retry, with the limit raised to 65536 inside the one command
(§6 above), passed in half the time. A watcher sampling once a minute during the retry saw at most 454 open files,
so the limit is the likely cause but not a proven one: NEU-2399 sets it on the containers before the next weekly run.
Publish was wrapped the same way.

**§7.1, fifteen figures against FEC** (`read bronze/cycle=2024/committee_summary/2026-11-19.csv`):

| | Id | Name | Source | FEC's committees | Receipts | Equal | Differing (gold / FEC) |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| candidate | S4MD00327 | ALSOBROOKS, ANGELA | committee_summary | C00840017 | 31,077,805.53 | 12 of 12 |  |
| candidate | S6OH00163 | BROWN, SHERROD | committee_summary | C00264697 | 96,530,240.72 | 12 of 12 |  |
| candidate | S4TX00722 | ALLRED, COLIN | committee_summary | C00839597 | 94,674,182.67 | 12 of 12 |  |
| candidate | S6MT00162 | TESTER, R. JON | committee_summary | C00412304 C00887521 | 93,570,122.72 | 12 of 12 |  |
| candidate | S2TX00312 | CRUZ, RAFAEL EDWARD  TED | committee_summary | C00492785 | 74,050,030.94 | 12 of 12 |  |
| candidate | S4AZ00139 | GALLEGO, RUBEN | committee_summary | C00558627 | 64,657,199.96 | 12 of 12 |  |
| candidate | S4MD00319 | TRONE, DAVID | committee_summary | C00653196 | 63,833,136.59 | 12 of 12 |  |
| candidate | S6PA00217 | CASEY, ROBERT P. JR. | committee_summary | C00431056 | 58,147,345.34 | 12 of 12 |  |
| candidate | S4MI00470 | SLOTKIN, ELISSA | committee_summary | C00834218 | 51,937,060.20 | 12 of 12 |  |
| candidate | S2WI00219 | BALDWIN, TAMMY | committee_summary | C00326801 | 50,228,545.14 | 12 of 12 |  |
| committee | C00840017 | ALSOBROOKS FOR SENATE | committee_summary | C00840017 | 31,077,805.53 | 12 of 12 |  |
| committee | C00835959 | FAIRSHAKE | committee_summary | C00835959 | 260,070,709.37 | 12 of 12 |  |
| committee | C00571703 | SLF PAC | committee_summary | C00571703 | 298,859,706.60 | 12 of 12 |  |
| committee | C00003418 | REPUBLICAN NATIONAL COMMITTEE | committee_summary | C00003418 | 475,764,008.28 | 12 of 12 |  |
| committee | C00010603 | DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE | committee_summary | C00010603 | 683,665,789.81 | 12 of 12 |  |

`comparisons: 15; from committee_summary and equal on every measure: 15`. Tester's two committees are summed on both sides and equal.

**§7.2, no itemized total moved:** `cycle`, `race`, `candidate_cycle`, `candidate_gift_size, itemized` and
`committee_cycle` each with `missing` 0 and `moved` 0.

**§7.3, coverage, 2024, gross basis:** 8,721 committees with a coverage, 6,525 within 1% (5,114 on the net basis),
131 over 1%. Super PACs: 1,035 with a coverage, 893 within 1% (802 net). `committee.type` is a committee's latest
type, so a committee that became a super PAC after 2024, or stopped being one, counts by its current type.

**Reconciliation:** 163 rows, $55,349,367.42 over, 23 reported 0. Nine reported a negative figure: listed, with no
coverage over 1.01, so `over_1pct` is 163 − 23 − 9 = 131. Each of the top ten was checked report by report against
FEC's API (`/v1/committee/<id>/reports/?cycle=2024`): each one's line 11(a)(i) per report adds up to `reported`, and
the excess sits on the filings named.

| # | Committee | fundlens | reported | Excess | Disposition |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | C00835959 FAIRSHAKE | 242,219,082 | 217,419,084.11 | 24,799,997.89 | Explained: Coinbase's $25,000,000 (type 10) in M7 2024 (`1804981`), filed on line 15 |
| 2 | C00627372 UNITE HERE PAC | 5,000,000 | 0.00 | 5,000,000.00 | Explained: UNITE HERE's type-10 gifts, filed on line 12 ($4M, 30G 2024) and line 15 ($1M, YE 2023) |
| 3 | C00754051 WORKERS VOTE | 6,545,484 | 1,754,905.50 | 4,790,578.50 | Explained: line 15 on seven reports (12G 2024: $695,000, line 15 exactly), and 11(c) in MY 2023 |
| 4 | C00887182 PLANNED PARENTHOOD VOTES NORTH CAROLINA | 3,678,228 | 0.00 | 3,678,228.00 | Explained: line 15 on every report (Q3 2024 $3.5M) |
| 5 | C00808998 DEMOCRACYFIRST PAC | 2,137,585 | 25,295.00 | 2,112,290.00 | **NEU-2400**: type-10 gifts with memo `NON-CONTRIBUTION ACCOUNT` (MY and YE 2023, line 15) counted as 11(a)(i) |
| 6 | C00620971 FOR OUR FUTURE | 4,228,896 | 2,147,547.69 | 2,081,348.31 | Explained: For Our Future Action Fund's type-10 gifts in the 30G amendment `1931997`, $2.01M of them in-kind, filed on line 13 ($2,081,349.79) |
| 7 | C00804856 LF PAC | 40,563,770 | 39,216,319.73 | 1,347,450.27 | Explained: line 15 in Q3 and 12G 2024 (12G: $91,354 against line 15's $91,357) |
| 8 | C00041269 GEORGIA FEDERAL ELECTIONS COMMITTEE | 3,684,047 | 2,681,478.34 | 1,002,568.66 | **NEU-2402**: $851,493 of IRS payroll-tax refunds from the Department of the Treasury, typed 15, in M8 2024 (`1812392`) |
| 9 | C00834424 MARIANNE WILLIAMSON FOR PRESIDENT | 3,157,883 | 2,273,142.00 | 884,741.00 | **NEU-2401**: 16,510 `15E` rows ($1,221,546) in the YE 2023 amendment `1764677`, more than FEC's itemized and unitemized together ($1,078,175) |
| 10 | C00693382 DEMOCRACY PAC | 70,740,507 | 70,002,500.00 | 738,007.00 | Explained: line 15 in Q1 and Q2 2024 ($238,033 and $493,925, exactly) |

No report counted two filings of itself: every report type with two filing numbers is a two-year cycle's two
reports (M2 2023 and M2 2024).

**§7.4 and §9, the ticket's candidate.** `S4MD00327` 2024: `reported` from `committee_summary`, 2023-05-01 to
2024-12-31, receipts $31,077,805.53; `itemized_total` $15,492,756 against $15,550,208.26, coverage 0.9963. Six gift
sizes: `unitemized` $8,214,278.15 with no donor count, then $444,982 (4,470 donors), $2,061,587 (6,896), $2,476,685
(4,256), $3,166,808 (2,768), $6,843,102 (2,016), the five adding up to `total_individual` $14,993,164.
`/v1/meta` served `20261119T212247Z`; `/v1/reconciliation?cycle=2024` pages by 100, its first row Fairshake; Fairshake's
committee read `committee_summary`, receipts $260,070,709.37, coverage 1.1141. `/candidate/S4MD00327` and
`/committee/C00835959` showed the Reported to the FEC panel, the coverage line and (for the candidate) the six gift
sizes as the API had them. Bugsink: nothing new but load's first attempt.

**Deviations, each filed:** NEU-2399 (load's open-file limit), NEU-2400, NEU-2401, NEU-2402 (reconciliation).
