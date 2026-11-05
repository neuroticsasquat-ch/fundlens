# Runbook: the 2024 production run with organization money

How to put organization money live on real data (NEU-2136; spec §4, §7.1; ADR-0011). Run 2024's silver again
with NEU-2131's `organization_receipt` and NEU-2132's blank-entity-type classifier, then resolve, validate, load
and publish it. Check what moved against what NEU-2132's prod query predicted, then check seven committees against
FEC's own summary. Run it once, top to bottom, on `music-box-dancer`, one step at a time. Append to the [Log](#log)
at the bottom; never rewrite it.

**Why now.** NEU-2134's API reads `gold.committee_top_organization` and `committee_cycle.total_from_organizations`.
It has been live since 2026-11-05, but the live gold predates NEU-2133, so every uncached `GET /v1/committees/{id}`
answers 500, and Bugsink's `fundlens` project collects them as an `UndefinedTable` issue from the `api` service. This run's publish
creates both objects and purges the edge, which ends the 500s.

**Why no `extract`.** The live build was transformed from the 2026-10-31 bronze files. NEU-2131's and NEU-2132's
prod checks ran on the same files. Transforming those files again means every difference from the live build
comes from the code, so step 7 can hold each moved figure to the classifier's rows. A fresh extract would mix in
FEC's amendments since 2026-10-31.

**Why `validate` before `load`.** `resolve --full` trains a new model. `load` copies only the newest model's DIME
figures into `gold.meta`, so without a `validate` first, `/v1/meta` and the methodology page would lose their
resolution quality ([refreshing-dime.md](refreshing-dime.md) §5).

**Not in this runbook:** cycles before 2024 (NEU-2060's backfill runs them with the classifier in place), the
capacity record (nothing here is new work for the box), and resuming the Kuma monitors (NEU-2063).

## Before you start

- NEU-2131 to NEU-2135 are merged (`52506b2`, NEU-2135's merge, is on `main`), and so is this runbook. Step 1.1
  checks that the deployed code includes them.
- **Nothing merges to `main` from step 2 until step 8 has printed its last line.** Every merge redeploys
  `pipeline` and kills a running `docker exec`. On 2026-11-02 a docs merge killed a `publish` part way.
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo, `gh`
  and `jq` are installed, and you can sign in to Bugsink (`https://bugsink.neuroticsasquat.ch`).
- Allow about two hours. Transform took 22–31 min on 2024 ([`docs/capacity.md`](../capacity.md)) and a
  `resolve --full` about 10 min. Validate, load and publish take a few minutes each.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycle | `2024` |
| Live build before this run | `20261103T175128Z`, transformed from `dd56128` (NEU-2183's merge). Its model is `20261104T173004Z`, NEU-2055's adjudicated one: 357 merges and 458 splits applied ([refreshing-dime.md](refreshing-dime.md) Log, 2026-11-04) |
| Silver changes since | `de34d38` (NEU-2131: `organization_receipt` and the committee name match) and `4da8db8` (NEU-2132: the classifier). Neither changes `contribution` except to remove the classified rows |
| What the classifier moves (NEU-2132's prod query, PR #90) | 70 blank-entity-type counted rows, $233,837. 6 of them ($59,784) name exactly one `cm` committee, so they become `committee_transfer` receipts, or are dropped where `oth` already holds the gift. The other 64 ($174,053) become organization receipts. The largest share is C90020454's: 3 rows, $84,694 |
| `organization_receipt` target | 18,398 rows: NEU-2131's prod transform found 18,334 (PR #89), and the classifier adds 64 |
| Committees checked against FEC | Five super PACs, the five with the most ORG-typed `indiv` dollars in [the measurement](../measurements/organization-money-2024.md) Q7: `C00835959` Fairshake, `C00484642` SMP, `C00834077` Never Back Down, `C00825851` Make America Great Again Inc., `C00571703` Senate Leadership Fund. Two party committees: `C00003418` RNC, `C00010603` DNC |
| FEC's figure | `INDV_CONTRIB` in FEC's PAC and party summary file `webk24.zip`, from Form 3X line 11(a)(iii). It counts every person who is not a committee, corporations included, with individuals, so it is fundlens's `total_individual + total_from_organizations` plus what the bulk files do not itemize. Bulk files have no unitemized receipts. Step 9.3 lists the gaps the measurement's Q7 already shows; explaining them belongs to NEU-2140 (FEC's summary files against fundlens gold) |
| Organizations resolved as donors | Before this run, `GROUNDSWELL ACTION FUND` and `TIDES ADVOCACY` were served at `/v1/donors/<id>`: their blank-type rows counted as individuals' (NEU-2132 spec §1). A `donor_id` whose every key is classified away has no `gold.donor` row and answers 404 (spec §1.1) |
| Monitors | `fundlens/weekly` and `fundlens/publish` stay **paused** until NEU-2063. `publish` therefore ends with `kuma push (up) failed: HTTPError: HTTP Error 404: Not Found`. That is the paused monitor refusing the push, not a fault: leave both paused |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-organizations
```

In the tmux session, define the helpers:

```bash
# VM, in tmux
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# A step's completion marker for one 2024 build, or MISSING: `mk <step> <build>`.
mk() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; m = markers.read(sys.argv[1], R2.from_settings(get_settings()), cycle=2024, build_id=sys.argv[2]); print(m.model_dump_json(indent=2) if m else "MISSING")' "$1" "$2"; }
# psql in the fundlens database.
pg() { docker exec "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
mkdir -p ~/fundlens-organization-run && cd ~/fundlens-organization-run
```

**Expected:** no output. If the tmux session is lost, run `tmux attach -t fundlens-organizations`. If the
session itself is gone, define the helpers again, `cd ~/fundlens-organization-run`, and export what earlier
steps saved: `export OLD=$(cat old-build.txt)` from step 1.2 on, `export B=$(cat build-id.txt)` from step 2 on,
and `export M=$(cat model-version.txt)` from step 4 on.

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

Then check what the deployed code changed in silver since the live build, and that no PR is about to merge:

```bash
# laptop
cd ~/projects/fundlens
git fetch origin
SHA=$(ssh hetzner-01 'docker exec "$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)" printenv OTEL_RESOURCE_ATTRIBUTES' | sed 's/.*service.version=//; s/,.*//')
echo "$SHA"
git merge-base --is-ancestor 52506b2 "$SHA" && echo "organization money deployed"
git log --oneline dd56128.."$SHA" -- sql/silver src/fundlens/transform src/fundlens/fec src/fundlens/resolve/normalize.py
gh pr list --repo neuroticsasquat-ch/fundlens --state open
```

**Expected:** the SHA from the VM, then `organization money deployed`, then exactly two commits, `4da8db8` (NEU-2132)
and `de34d38` (NEU-2131). A third commit means something else changed silver since the live build: step 7 would
blame its differences on the classifier. Stop and find out what it changes. Note the open PRs: none of them merges
until step 8 is done.

### 1.2 The live build

```bash
# VM
pg -Atc "select build_id from gold.meta" | tee old-build.txt
export OLD=$(cat old-build.txt)
pg -Atc "select coalesce(to_regclass('gold.committee_top_organization')::text, 'no gold.committee_top_organization')"
docker exec "$(fl pipeline)" python -c 'from fundlens.r2 import R2; from fundlens.settings import get_settings; from fundlens.resolve.runner import transformed_builds; print(transformed_builds(R2.from_settings(get_settings())))'
mk transformed "$OLD" | tee old-transformed.json
docker exec "$(fl pipeline)" sh -c 'grep -c "^- " /app/resolution/overrides.yaml'
```

**Expected:**

- `20261103T175128Z`. Another build means someone published since the Facts were written. Stop and read the
  Logs of [refreshing-dime.md](refreshing-dime.md) and [adjudicating.md](adjudicating.md) to find out what it is.
- `no gold.committee_top_organization`: the live gold predates NEU-2133, which is why committee pages answer 500.
- `{2024: '20261103T175128Z'}`, or `{2024: '20261105T145236Z'}` if NEU-2131's trial transform was kept. Either
  is fine: step 3's build is newer than both, and `resolve` reads the newest.
- A `transformed` marker whose `row_counts` has `contributor: 5620495`. Write down its `contribution`,
  `committee_transfer` and `jfc_attribution` counts: step 3 compares against them.
- The number of overrides, at least `1` (NEU-2121's Musk merge). Step 4's `overrides:` line counts them.

### 1.3 Disk

```bash
# VM
df -h / | tee disk-before.txt
```

**Expected:** at least 100 GB available on `/`. `transform` and `resolve` can each spill up to 60 GB of DuckDB
scratch (`DUCKDB_MAX_TEMP_DIRECTORY_SIZE`). With less free space, free some first.

## 2. Seats

`transform` reads the unmatched filings `seats --report` records, and `load` reads the `race` partition of the
same build. Fix the build ID here:

```bash
# VM, in tmux
export B=$(date -u +%Y%m%dT%H%M%SZ)
echo "$B" | tee build-id.txt
time docker exec "$(fl pipeline)" fundlens seats --cycle 2024 --report --build-id "$B" 2>&1 | tee seats.log
```

**Expected:** `house: 441 races (0 special)`, `senate: 35 races (2 special)`, `president: 1 races (0 special)`,
`wrote silver/race/cycle=2024/build=<B>/…`, and about 51 unmatched filings recorded, as in every 2024 run so far.
Under a minute.

## 3. Transform

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens transform --cycle 2024 --build-id "$B" 2>&1 | tee transform.log
mk transformed "$B" | tee transformed.json
```

**Expected:** a `<table>: <n> rows` line per silver table, then `wrote …` lines, and a `transformed` marker
with the same row counts. Compared with `old-transformed.json` from step 1.2:

- `organization_receipt: 18398 rows`. The live build has none.
- `contribution`: about 70 fewer, the classified rows.
- `committee_transfer`: NEU-2131's 358,914 plus at most 6. The live build's count is lower by NEU-2131's
  2,463 name-matched receipts.
- `contributor`: a few dozen below 5,620,495. These are the keys only the classified rows used.
- `jfc_attribution`: the same, or a few fewer. A classified 15J line is in no table.

**Estimated:** 20–35 min. A failed check stops the run before anything is uploaded. The traceback names the
`sql/checks/silver_*.sql` file whose query returned rows, and Bugsink gets an issue `pipeline_mode=transform`.
Stop, file a ticket with the check's name and a few of its rows, and link it from NEU-2136. The live build is
untouched.

## 4. Resolve

Fix the model version, then retrain and re-cluster with the classified keys gone:

```bash
# VM, in tmux
export M=$(date -u +%Y%m%dT%H%M%SZ)
echo "$M" | tee model-version.txt
time docker exec "$(fl pipeline)" fundlens resolve --full --build-id "$M" 2>&1 | tee resolve.log
mk resolved "$B" | tee resolved.json
```

**Expected:**

```
2024: build <B>
<k> contributor keys in <C> clusters
recluster: …
overrides: <o> merges joining <j> clusters into others, <s> splits
adjudications: <v> verdicts: <a> merges joining <j> clusters into others, <s> splits
crosswalk: <n> new donors, <r> keys re-pointed, <d> redirects
model <M>: trained, wrote resolution/model/<M>.json
load <s> s, train <s> s, cluster <s> s, recluster <s> s, overrides <s> s, adjudications <s> s, save <s> s, crosswalk <s> s, silver <s> s
DuckDB memory limit: <about 26 GiB>
```

- `2024: build <B>`. Another build means step 3's build is not the newest transformed one: stop.
- `<k>` is step 3's `contributor` count.
- The `overrides:` line counts the entries from step 1.2. If instead the run stops with exit 1 and a line starting
  `overrides:` on stderr, an override names a key the classifier moved away. The crosswalk has not changed.
  Remove that entry in a PR ([adding-an-override.md](adding-an-override.md)), let it deploy, and run this step
  again.
- `<v>` is close to 815, NEU-2055's 357 merges and 458 splits. A verdict whose cluster lost a classified key no
  longer matches its candidate and is not applied. That cluster held an organization's key, so its verdict was
  about an organization and is moot.
- `crosswalk:` numbers are small. No key is new, so a new donor comes only from a cluster that lost a key and
  split. Write all three numbers in the Log.
- The `resolved` marker's `row_counts` has `cluster: <k>`. Its `contribution` count is step 3's.

**Estimated:** 10–15 min. If it fails part way, run the same command again with the same `M`, as
[first-resolved-run.md](first-resolved-run.md) step 3 describes.

### 4.1 Candidates no verdict covers

A record, not a gate. Nothing is sent, so nothing is billed:

```bash
# VM
docker exec "$(fl pipeline)" fundlens adjudicate --dry-run > adjudicate-dry-run.txt; echo "exit=$?"
head -2 adjudicate-dry-run.txt
```

**Expected:** `exit=0`, a `candidates: …; <d> already decided by …` line and `chosen: <k>`. `<k>` counts the
candidates with no verdict yet: clusters whose sides changed when a classified key left, and candidates the last
run's model answered invalidly. Write `<k>` in the Log. Asking about them is an [adjudicating.md](adjudicating.md)
run of its own, after this one, and not part of it: a verdict applied here would move donors for a reason other
than the classifier, and step 7.1 could no longer tell the two apart.

## 5. Validate

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens validate --cycle 2024 | tee validate.txt
```

**Expected:** the `scope precision recall …` table, then `matched <m> of <n> counted contributions (<pct>%)` and
`model <M>, DIME v4.0, build <B>`. The figures should be close to NEU-2056's: overall 0.8244 / 0.9075, top 10,000
0.9762 / 0.7867. A move of more than 0.005 in any of them is more than 70 rows can explain: write it in the Log,
and file a ticket linked from NEU-2136 before you publish. About 4 min.

## 6. Load

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens load --cycle 2024 --build-id "$B" 2>&1 | tee load.log
mk loaded "$B"
```

**Expected:** a `<table>: <n> rows` line per gold table, `committee_top_organization` among them. Then
`quality: precision …` with step 5's figures (not `quality: not validated for model …`), a `resolution:
release <sha>, <o> overrides, <a> adjudications applied` line, and `loaded build <B> into gold_build
(aggregates <a> s, copy <c> s)`. That last line means every `sql/checks/gold_*.sql` passed. A failed check leaves
no `gold_build` and names the check: file a ticket with its rows and stop. Then a `loaded` marker. About 3 min.

## 7. Check the money before publishing

Both builds are in Postgres now: `gold` is the live build `$OLD` and `gold_build` is `$B`. Nothing is live yet.

### 7.1 Every candidate's `total_individual`

The rows that left `contribution` between the two builds should be exactly the classified ones. Each
candidate's `total_individual` should move by exactly the dollars of those rows that were theirs. The script
diffs the two builds' `contribution` partitions in DuckDB. It downloads a partition from R2 first where the volume
lacks one. Then it compares the result with the two gold schemas:

```bash
# VM, in tmux
docker exec -i "$(fl pipeline)" python - "$OLD" "$B" <<'PY' 2>&1 | grep -v '^{' | tee candidates.txt
import sys
from decimal import Decimal

import psycopg

from fundlens import paths
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.settings import get_settings
from fundlens.transform import runner

old, new = sys.argv[1:3]
settings = get_settings()
store = R2.from_settings(settings)


def parquet(table, build):
    """One build's 2024 partition of a silver table, downloaded first where the volume lacks it."""
    prefix = paths.silver_partition(table, 2024, build)
    for key in store.list_keys(prefix + "/"):
        local = paths.local_path(settings.data_dir, key)
        if not local.exists():
            store.download_to(key, local)
    files = paths.local_path(settings.data_dir, prefix) / "**" / "*.parquet"
    return f"read_parquet({runner.literal(files)}, hive_partitioning = false)"


con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
normalize.register(con)
con.execute(f"CREATE VIEW old_c AS SELECT * FROM {parquet('contribution', old)}")
con.execute(f"CREATE VIEW new_c AS SELECT * FROM {parquet('contribution', new)}")
con.execute(f"CREATE VIEW org AS SELECT * FROM {parquet('organization_receipt', new)}")
con.execute(f"CREATE VIEW xfer AS SELECT * FROM {parquet('committee_transfer', new)}")
con.execute("CREATE TABLE removed AS SELECT * FROM old_c"
            " WHERE source_record_id NOT IN (SELECT source_record_id FROM new_c)")
con.execute("CREATE TABLE added AS SELECT * FROM new_c"
            " WHERE source_record_id NOT IN (SELECT source_record_id FROM old_c)")


def show(title, sql):
    print(f"\n## {title}")
    con.sql(sql).show(max_width=250, max_rows=50)


show("Rows that left contribution, and rows that joined it", """
SELECT 'left' AS rows_that, count(*) AS rows, sum(amount) AS dollars FROM removed
UNION ALL SELECT 'joined', count(*), sum(amount) FROM added
""")
show("Rows that left and are not blank-type rows the classifier calls organizations", """
SELECT count(*) AS rows, sum(amount) AS dollars FROM removed
WHERE nullif(trim(entity_type), '') IS NOT NULL OR NOT is_organization_name(contributor_name)
""")
show("Where the rows that left went", """
SELECT CASE
        WHEN source_record_id IN (SELECT source_record_id FROM org WHERE classified)
            THEN 'organization_receipt, classified'
        WHEN source_record_id IN (SELECT source_record_id FROM xfer WHERE side = 'receipt')
            THEN 'committee_transfer, by name'
        ELSE 'neither: oth holds the gift'
    END AS went, count(*) AS rows, sum(amount) AS dollars
FROM removed GROUP BY ALL ORDER BY rows DESC
""")
show("organization_receipt", """
SELECT count(*) AS rows, count(*) FILTER (WHERE classified) AS classified_rows,
    sum(amount) FILTER (WHERE classified) AS classified_dollars, sum(amount) AS dollars
FROM org
""")
show("The rows that left by recipient, top 10", """
SELECT recipient_committee_id, count(*) AS rows, sum(amount) AS dollars
FROM removed GROUP BY ALL ORDER BY dollars DESC LIMIT 10
""")

left = dict(con.execute("""
    SELECT candidate_id, sum(amount) FROM removed
    WHERE candidate_id IS NOT NULL AND NOT is_self_funding GROUP BY candidate_id
""").fetchall())
with psycopg.connect(settings.database_url) as conn:
    moved = dict(conn.execute("""
        SELECT candidate_id, coalesce(o.total_individual, 0) - coalesce(n.total_individual, 0)
        FROM (SELECT candidate_id, total_individual FROM gold.candidate_cycle WHERE cycle = 2024) AS o
        FULL JOIN (SELECT candidate_id, total_individual FROM gold_build.candidate_cycle WHERE cycle = 2024) AS n
            USING (candidate_id)
        WHERE o.total_individual IS DISTINCT FROM n.total_individual
    """).fetchall())

print("\n## Candidates whose total_individual moved (live less new) beside their rows that left")
print("| Candidate | Moved | Left | |\n| --- | ---: | ---: | --- |")
differing = 0
for candidate in sorted(moved.keys() | left.keys()):
    m, r = moved.get(candidate, Decimal(0)), left.get(candidate, Decimal(0))
    differing += m != r
    print(f"| {candidate} | {m:,.2f} | {r:,.2f} | {'' if m == r else 'DIFFERS'} |")
print(f"\ncandidates moved: {len(moved)}; differing: {differing}")
PY
```

**Expected,** in a minute or two:

- `left` 70 rows, $233,837, and `joined` 0 rows.
- `0` rows that left that are not classified organizations.
- `organization_receipt, classified` 64 rows, $174,053. The other 6 rows, $59,784, are under
  `committee_transfer, by name` or `neither: oth holds the gift`.
- `organization_receipt`: 18,398 rows, 64 classified, $174,053 classified.
- The top recipients as NEU-2132's query found them: `C90020454` 3 rows $84,694, then `C00852699` $27,069,
  `C00877670` $25,000.
- A table of the candidates that moved, then `differing: 0`. Each candidate moved by exactly the dollars of
  their rows that left, and none moved for any other reason. Copy the table into the Log.

A count that differs from NEU-2132's by a few rows is not by itself a failure, if `differing` is 0 and every row
that left is classified. Write the difference in the Log. **A `DIFFERS` row, or rows that left that the classifier
does not call organizations, mean some money moved for another reason.** Stop here, before `publish`, file a
ticket with this output, and link it from NEU-2136. `gold` stays the live build; the next `load` replaces
`gold_build`.

### 7.2 The seven committees

```bash
# VM
pg -c "select committee_id, o.total_individual as live_individual, n.total_individual,
  o.total_from_committees as live_from_committees, n.total_from_committees, n.total_from_organizations
  from gold.committee_cycle o join gold_build.committee_cycle n using (committee_id, cycle)
  where cycle = 2024 and committee_id in ('C00835959', 'C00484642', 'C00834077', 'C00825851', 'C00571703', 'C00003418', 'C00010603')
  order by n.total_from_organizations desc" | tee committees-before-after.txt
```

**Expected:** seven rows.

- `total_individual` is unchanged unless step 7.1's recipients name the committee.
- `total_from_committees` is higher in the new build wherever NEU-2131's name match found PAC- or COM-typed
  rows with no committee ID.
- `total_from_organizations` is about the measurement's ORG-typed `indiv` dollars (Q7) for the five super
  PACs: Fairshake $166,692,432, SMP $117,131,062, Never Back Down $95,595,613, MAGA Inc. $83,345,136, SLF
  $79,260,000.
- `total_from_organizations` is above 0 for both party committees.

### 7.3 Organizations resolved as donors

```bash
# VM
pg -c "select donor_id, display_name from gold.donor where display_name ilike 'GROUNDSWELL ACTION%' or display_name ilike 'TIDES ADVOCACY%' order by donor_id"
pg -Atc "select donor_id from gold.donor where display_name ilike 'GROUNDSWELL ACTION%' or display_name ilike 'TIDES ADVOCACY%'" | tee org-donor-ids.txt
pg -Atc "select count(*) from gold_build.donor where display_name ilike 'GROUNDSWELL ACTION%' or display_name ilike 'TIDES ADVOCACY%'"
```

**Expected:** one or more live `gold.donor` rows named for each organization, their `donor_id`s in
`org-donor-ids.txt`, and `0` in the new build: their keys are classified away. A count above 0 means a key of
theirs is still in `contribution`, so the classifier did not call its name an organization. List those rows:

```bash
# VM
pg -c "select donor_id, display_name, contributor_key_count from gold_build.donor where display_name ilike 'GROUNDSWELL ACTION%' or display_name ilike 'TIDES ADVOCACY%'"
```

Write them in the Log. If a name has no comma or ends in `INC` or `LLC`, file a ticket linked from NEU-2136,
because V8 should have called it an organization. It does not stop the run.

## 8. Publish

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens publish --cycle 2024 2>&1 | tee publish.log
mk published "$B"
pg -c "select build_id, published_at, model_version, precision, recall from gold.meta"
pg -Atc "select build_id from gold_prev.meta"
pg -Atc "select coalesce(to_regclass('gold.committee_top_organization')::text, 'missing'), (select count(*) from gold.committee_top_organization)"
```

**Expected:** `published build <B> of 2024`, `previous build: 20261103T175128Z`, `cloudflare purge: done`,
`wrote resolution/build=<B>/crosswalk.parquet` and `pruned <n> silver builds (<m> objects)`. Prune removes only
builds older than `20261103T175128Z`: never the live build, nor the one before it. Then the expected
`kuma push (up) failed: HTTPError: HTTP Error 404: Not Found`: the monitors are paused (Facts). Then:

- a `published` marker;
- `gold.meta` naming `<B>` and `<M>`, with `published_at` set and step 5's precision and recall;
- `gold_prev` holding `20261103T175128Z`;
- `gold.committee_top_organization` and its row count, above 0.

About 75 s to 3 min: the purge waits 75 s after the swap on purpose (spec §5.5). From here, merging to `main`
is safe again.

**If a check in step 9 fails.** Roll back to the live build:

```bash
# VM
docker exec "$(fl pipeline)" fundlens publish --rollback
```

**Expected:** `rolled back: build 20261103T175128Z is live`, then `build <B> is now gold_prev`. Committee pages
answer 500 again, because the API needs the new gold objects. File a ticket with the failed check's output.

## 9. Verify

### 9.1 The API serves the build

```bash
# laptop
curl -sS https://api.fundlens.org/v1/meta | jq '{build_id, model_version, overrides_count, adjudications_applied, precision, recall, precision_top, recall_top}'
```

**Expected:** `build_id` is `<B>` and `model_version` is `<M>`. `overrides_count` and `adjudications_applied` are
step 6's. The four figures are step 5's.

### 9.2 Committee pages answer again

`nocache` makes each URL new to the edge, so the request reaches the API:

```bash
# laptop
for c in C00835959 C00401224; do curl -sS -o /dev/null -w "$c %{http_code}\n" "https://api.fundlens.org/v1/committees/$c?nocache=$(date +%s)"; done
curl -sS "https://api.fundlens.org/v1/committees/C00835959?cycle=2024" | jq '.cycles[] | select(.cycle == 2024) | {total_individual, total_from_committees, total_from_organizations, top_organizations: [.top_organizations[:5][] | {rank, name, amount}]}'
```

**Expected:** `C00835959 200` and `C00401224 200`. `C00401224` answered 500 on 2026-11-05. Then Fairshake's
2024: `total_from_organizations` as step 7.2's new figure, not 0, and five `top_organizations`, ranked 1 to 5,
the largest first. Copy the figure and the five names into the Log.

### 9.3 The seven committees against FEC

The script downloads FEC's `webk24.zip` into a temporary directory and deletes it at the end. The file is not
catalogued and not kept in bronze, as in the measurement's Q7. It sets fundlens's live figures beside FEC's:

```bash
# VM
docker exec -i "$(fl pipeline)" python - <<'PY' 2>&1 | grep -v '^{' | tee fec-committees.txt
import shutil
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg

from fundlens import paths
from fundlens.fec.extract import USER_AGENT
from fundlens.settings import get_settings
from fundlens.transform import runner

COMMITTEES = ["C00835959", "C00484642", "C00834077", "C00825851", "C00571703", "C00003418", "C00010603"]
# webk has no header file; the columns are FEC's file description's, in order
# (https://www.fec.gov/campaign-finance-data/pac-and-party-summary-file-description/), as in the measurement's Q7.
HEADER = ["CMTE_ID", "CMTE_NM", "CMTE_TP", "CMTE_DSGN", "CMTE_FILING_FREQ", "TTL_RECEIPTS",
          "TRANS_FROM_AFF", "INDV_CONTRIB", "OTHER_POL_CMTE_CONTRIB", "CAND_CONTRIB", "CAND_LOANS",
          "TTL_LOANS_RECEIVED", "TTL_DISB", "TRANF_TO_AFF", "INDV_REFUNDS", "OTHER_POL_CMTE_REFUNDS",
          "CAND_LOAN_REPAY", "LOAN_REPAY", "COH_BOP", "COH_COP", "DEBTS_OWED_BY",
          "NONFED_TRANS_RECEIVED", "CONTRIB_TO_OTHER_CMTE", "IND_EXP", "PTY_COORD_EXP",
          "NONFED_SHARE_EXP", "CVG_END_DT"]
settings = get_settings()


def usd(value):
    return "—" if value is None else f"{value:,.0f}"


work = Path(tempfile.mkdtemp())
try:
    url = f"{settings.fec_bulk_url.rstrip('/')}/2024/webk24.zip"
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT})) as response:
        (work / "webk24.zip").write_bytes(response.read())
        print(url, "| Last-Modified:", response.headers.get("Last-Modified"))
    with zipfile.ZipFile(work / "webk24.zip") as archive:
        member = archive.namelist()[0]
        archive.extract(member, work)
    con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
    columns = "{" + ", ".join(f"'{h}': 'VARCHAR'" for h in HEADER) + "}"
    con.execute(f"CREATE VIEW webk AS SELECT * FROM read_csv({runner.literal(work / member)}, delim = '|',"
                f" quote = '', escape = '', header = false, auto_detect = false, columns = {columns})")
    fec = {row[0]: row[1:] for row in con.execute(
        "SELECT CMTE_ID, CMTE_NM, CAST(INDV_CONTRIB AS DECIMAL(16, 2)), CAST(INDV_REFUNDS AS DECIMAL(16, 2))"
        " FROM webk WHERE list_contains(?, CMTE_ID)", [COMMITTEES]).fetchall()}
    with psycopg.connect(settings.database_url) as conn:
        live = {row[0]: row[1:] for row in conn.execute(
            "SELECT committee_id, total_individual, total_from_organizations FROM gold.committee_cycle"
            " WHERE cycle = 2024 AND committee_id = ANY(%s)", (COMMITTEES,)).fetchall()}
    print("\n| Committee | FEC name | FEC INDV_CONTRIB | FEC INDV_REFUNDS | Individual | Organizations"
          " | fundlens | Gap | Gap net of refunds |")
    print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for committee in COMMITTEES:
        name, contrib, refunds = fec.get(committee, ("(not in webk)", None, None))
        individual, organizations = live.get(committee, (Decimal(0), Decimal(0)))
        fundlens = individual + organizations
        gap = None if contrib is None else contrib - fundlens
        net = None if contrib is None or refunds is None else contrib - refunds - fundlens
        print(f"| {committee} | {name} | {usd(contrib)} | {usd(refunds)} | {usd(individual)}"
              f" | {usd(organizations)} | {usd(fundlens)} | {usd(gap)} | {usd(net)} |")
finally:
    shutil.rmtree(work)
PY
```

**Expected:** the URL with FEC's `Last-Modified`, then a table of seven rows, each with FEC's name for the
committee. *Gap* is `INDV_CONTRIB` less fundlens's `total_individual + total_from_organizations`. *Gap net of
refunds* takes FEC's `INDV_REFUNDS` off first, because fundlens's figures are net of refunds and
`INDV_CONTRIB` is gross.

The measurement's Q7 already shows the five super PACs' gaps, from the live gold's `total_individual` and the
ORG-typed `indiv` dollars, against the file dated 2026-11-04. Expect each gap within about $1M of these, or
different only by what a newer FEC file changed:

| Committee | FEC `INDV_CONTRIB` | fundlens, predicted | Gap, predicted |
| --- | ---: | ---: | ---: |
| `C00835959` Fairshake | 217,423,881 | 174,019,082 | 43,404,799 |
| `C00484642` SMP | 288,693,799 | 271,631,553 | 17,062,246 |
| `C00834077` Never Back Down | 144,591,259 | 141,012,317 | 3,578,942 |
| `C00825851` MAGA Inc. | 383,797,396 | 389,299,300 | −5,501,904 |
| `C00571703` SLF | 220,738,384 | 255,310,171 | −34,571,787 |

The ticket expects the remainder to be unitemized receipts, which the bulk files do not carry. That fits a
positive gap, and it is large for the RNC and DNC, which take many small gifts. **It does not fit a negative gap
(fundlens above FEC), nor Fairshake's $43M, at a super PAC that takes few small gifts.** The measurement found
these gaps before this run, so they are not this run's doing. Copy the table into the Log, with a line per
committee: does unitemized money explain its gap, or not? Then add the table and the unexplained rows to NEU-2140
(FEC's summary files against fundlens gold) as a comment. NEU-2140 is where they get explained. A gap more than
$1M away from its prediction is this run's: file a ticket linked from NEU-2136. It does not roll the build back,
because fundlens shows what the bulk files itemize.

### 9.4 The committee page

Open `https://fundlens.org/committee/C00835959` in a browser.

**Expected:** the cycles table has a **From organizations** column, with 2024's figure as in step 9.2. Below it
is a **Top organizations** section that reads "Grouped by reported name; not resolved like individual donors.",
links to Methodology, and lists the organizations of step 9.2 first. A page that still shows no organization
money is served from an old cache: reload with the cache bypassed (Shift-reload) once. If it still shows none,
the build is not live: go back to step 9.1.

### 9.5 The organizations are no longer served as donors

```bash
# laptop
for d in $(ssh hetzner-01 cat fundlens-organization-run/org-donor-ids.txt); do curl -sS -o /dev/null -w "$d %{http_code}\n" "https://api.fundlens.org/v1/donors/$d?nocache=$(date +%s)"; done
curl -sS 'https://api.fundlens.org/v1/search?q=groundswell%20action%20fund&kind=donor' | jq -r '.[] | [.id, .name] | @tsv'
```

**Expected:** `<id> 404` for every id step 7.3 saved. Then search lists no donor named `GROUNDSWELL ACTION FUND`.
It may list people whose names are near it by trigrams. Their `app.crosswalk` rows stay, because ids are
never reused (NEU-2132 spec §1.1).

### 9.6 Signals

- **Bugsink** → `fundlens`: the `api` service's `UndefinedTable` issue from the committee 500s gets no new event
  after step 8's publish. Resolve it. A new event after the publish means a committee route still reads a missing
  object: go back to step 9.2.
- **Bugsink** → `fundlens`: no new `pipeline` issue since step 2. An issue there is from a step that crashed and was run
  again. Note it in the Log, then resolve it.

## 10. Record the run

Gather the run's identifiers and step times in one file:

```bash
# VM
{
  date -u +%Y-%m-%d
  docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES | sed 's/.*service.version=/sha /; s/,.*//'
  echo "live before $OLD"
  echo "build $B"
  echo "model $M"
  for s in transformed resolved loaded published; do mk "$s" "$B" | grep -E '"step"|"duration_s"'; done | paste - - | tr -d ' ,"'
  grep -E '^[0-9]+ contributor keys in|^overrides:|^adjudications:|^crosswalk:' resolve.log
  grep '^chosen:' adjudicate-dry-run.txt
  grep -E '^(overall|top)' validate.txt
} | tee run-record.txt
```

```bash
# laptop
scp hetzner-01:'fundlens-organization-run/{run-record.txt,transformed.json,old-transformed.json,candidates.txt,committees-before-after.txt,fec-committees.txt}' .
```

**Expected:** `run-record.txt` holds the date, the SHA, the two builds, the model, four `step:<name>` lines with
their `duration_s`, resolve's four summary lines, the `chosen:` count and validate's two figure lines. The other
files are the output of steps 3, 1.2, 7.1, 7.2 and 9.3.

Append a Log entry from them, headed `### <date> — 2024 with organization money (NEU-2136)`:

- the date, the SHA, build `<B>` (live before: `<OLD>`) and model `<M>`, and the four step times;
- step 3's row counts beside the live build's (`organization_receipt`, `contribution`, `committee_transfer`,
  `contributor`, `jfc_attribution`);
- resolve's `overrides:`, `adjudications:` and `crosswalk:` lines, and step 4.1's `chosen:` count;
- step 5's figures;
- step 7.1's output: rows that left, where they went, and the candidate table with `differing: 0`;
- step 9.2's Fairshake figures and top five, and step 9.3's table with each gap's line;
- step 7.3's `donor_id`s and their 404s;
- every deviation, each filed as a ticket and linked from NEU-2136.

Open one PR, `docs(runbooks): log the 2024 organization money run (NEU-2136)`, with the entry. Merging it
redeploys `pipeline`, which is safe now that nothing is running.

## Log

<!-- Append entries below; never rewrite one. -->
