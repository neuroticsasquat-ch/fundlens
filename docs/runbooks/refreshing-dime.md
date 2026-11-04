# Runbook: refreshing the DIME file and validating resolution

How to bring one cycle's DIME contribution file into R2 and score fundlens's resolved donors against it
(NEU-2054; [ADR-0009](../adr/0009-resolution-quality-is-scored-against-dime-by-fec-ids.md), spec §6.9).
It runs on `music-box-dancer`, one step at a time: download the file into the `pipeline` container,
`fundlens dime --import` it, then `fundlens validate`. The next `load` and `publish` of the cycle carry the
figures into `gold.meta`. Run it once per cycle and DIME release; the backfill (NEU-2060) repeats steps 2–4
per cycle. Append to the [Log](#log) at the bottom; never rewrite it.

**Why the raw file is archived too.** Only the slim Parquet is read, but DIME's download links are Dropbox
links that rot, and `bonica.cid` values change between DIME releases (codebook §14). A published figure
must be reproducible from what R2 holds (ADR-0002).

**Not in this runbook:** the methodology page and the `/v1/meta` fields (NEU-2056). Tuning the cluster cap
against the figures is [step 8](#8-tuning-the-cluster-cap); taking the wrong pairs apart and sweeping the cluster
threshold is [step 9](#9-diagnosing-the-wrong-pairs).

## Before you start

- The cycle has a resolved build: [first-resolved-run.md](first-resolved-run.md) (NEU-2079) for 2024, the
  backfill (NEU-2060) for the rest.
- The PR for NEU-2054 is merged and deployed (step 1 checks), and `alembic upgrade head` has created
  `app.resolution_quality`.
- The laptop is on the tailnet and `ssh hetzner-01` works.
- Allow an hour for 2024: the import decompresses 19 GB single-threaded and uploads it to R2.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| DIME release | Public version 4.0 (`DIME_VERSION` in `src/fundlens/resolve/validate.py`) |
| Download page | `https://data.stanford.edu/dime`: one `contribDB_<cycle>.csv.gz` Dropbox link per even year |
| Licence | ODC-BY 1.0 (the page's "Data Use Agreement"). Attribution is the only condition; fundlens publishes derived figures, never DIME rows |
| Citation | Bonica, Adam. 2024. Database on Ideology, Money in Politics, and Elections: Public version 4.0 [Computer file]. Stanford, CA: Stanford University Libraries. https://data.stanford.edu/dime |
| 2024 file size | 19,158,623,840 bytes gzipped (`Content-Length`, checked 2026-11-01), about 200M rows |
| R2 keys | `reference/dime/v4.0/contribDB_<cycle>.csv.gz` (the raw file) and `reference/dime/v4.0/cycle=<cycle>/fec_individual.parquet` (the slim file `validate` reads) |
| Where the figures go | `app.resolution_quality`, two rows per model and cycle (`overall`, `top`); then `gold.meta` at the next `load` |

## 0. Session setup

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps the long import running if the SSH session drops.
tmux new -s fundlens-dime
```

In the tmux session, define the helpers and fix the cycle and the DIME version:

```bash
# VM, in tmux
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# psql in the fundlens database.
pg() { docker exec "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
export C=2024
export V=4.0
mkdir -p ~/fundlens-dime && cd ~/fundlens-dime
```

**Expected:** no output. If the tmux session is lost, define the helpers again, `cd ~/fundlens-dime`,
`export C=2024` and `export V=4.0`.

## 1. Preflight

### 1.1 The DIME release

Open `https://data.stanford.edu/dime` in a browser and read the version the page offers.

**Expected:** "Public version 4.0". If it names another version, stop: a new release is a PR that bumps
`DIME_VERSION` in `src/fundlens/resolve/validate.py` (and this runbook's Facts), then a re-import and
re-validation of every cycle. Nothing under the old version's keys is touched.

### 1.2 The deployed code and the table

```bash
# VM
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES
git ls-remote https://github.com/neuroticsasquat-ch/fundlens main
docker exec "$(fl pipeline)" alembic upgrade head
docker exec "$(fl pipeline)" fundlens validate --help | head -3
pg -c '\d app.resolution_quality'
```

**Expected:** the `service.version=<sha>` in `OTEL_RESOURCE_ATTRIBUTES` is the SHA `ls-remote` prints (if
not: Coolify → the `fundlens` resource → *Deploy*, then run this step again); Alembic reaches head with no
error; the `validate` usage line; the table's fourteen columns.

### 1.3 Disk

```bash
# VM
df -h / | tee disk-before.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null' | tee -a disk-before.txt
```

**Expected:** at least 60 GB free: the 19 GB download, the slim Parquet and the import's staging file
(a few GB each), and `validate`'s unpacked `indiv` text (about 20 GB for 2024, deleted when it ends). If
less, stop and free space first.

## 2. Download the file

The file goes into the `scratch` volume, under `scratch/dime-raw/`. Not under `reference/`: the `pipeline`
container mounts volumes only for `bronze`, `silver`, `scratch` and `resolution` (`docker-compose.prod.yml`), so
anything else under `/data/fundlens` lives in the container and a redeploy deletes it (a 19 GB download was lost
that way on 2026-11-01). Not under `scratch/dime-<cycle>/` either: that is the import's own working directory,
deleted when it ends.

Copy the cycle's `contribDB_<cycle>.csv.gz` link from the download page (right-click → *Copy link*), then
set it, with its `dl=0` changed to `dl=1` so Dropbox sends the file rather than a preview page:

```bash
# VM
export DIME_URL='<the copied link, ending dl=1>'
```

```bash
# VM
docker exec "$(fl pipeline)" mkdir -p "/data/fundlens/scratch/dime-raw/v$V"
time docker exec -e DIME_URL="$DIME_URL" "$(fl pipeline)" python -c 'import os, sys, urllib.request; urllib.request.urlretrieve(os.environ["DIME_URL"], sys.argv[1])' "/data/fundlens/scratch/dime-raw/v$V/contribDB_$C.csv.gz"
docker exec "$(fl pipeline)" ls -l "/data/fundlens/scratch/dime-raw/v$V/contribDB_$C.csv.gz"
docker exec "$(fl pipeline)" python -c 'import sys; print(open(sys.argv[1], "rb").read(2).hex())' "/data/fundlens/scratch/dime-raw/v$V/contribDB_$C.csv.gz"
```

**Expected:** for 2024, a size of `19158623840` bytes; every cycle prints `1f8b` (a gzip file). A
size of a few kB, or anything else in place of `1f8b`, is an HTML page: check the link ends `dl=1` and download again.

## 3. Import

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens dime --cycle "$C" --import "/data/fundlens/scratch/dime-raw/v$V/contribDB_$C.csv.gz" | tee import.txt
```

**Expected:** after tens of minutes (decompression, then the 19 GB upload),

```
rows read: <about 200,000,000 for 2024>
rows kept: <the FEC individual rows>
distinct cids: <n>
rows dropped (bad amount, date or cid): <a handful>
wrote reference/dime/v4.0/cycle=2024/fec_individual.parquet
wrote reference/dime/v4.0/contribDB_2024.csv.gz
```

and `real` from `time`. `has no <column> column` means the release renamed a column: stop and file a
ticket. Record the counts and the time in the Log.

## 4. Validate

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" | tee validate.txt
pg -c "SELECT model_version, cycle, scope, top_limit, matched_rows, contribution_rows, labelled_keys, precision, recall, validated_at FROM app.resolution_quality WHERE cycle = $C ORDER BY validated_at DESC, scope LIMIT 2"
```

**Expected:** a table like

```
scope    precision    recall       keys      correct    predicted         true
overall     0.9xxx    0.9xxx    <keys>    <pairs>      <pairs>      <pairs>
top 10000   0.9xxx    0.9xxx    <keys>    <pairs>      <pairs>      <pairs>
matched <m> of <n> counted contributions (<pct>%)
model <M>, DIME v4.0, build <B>
```

and the same figures in the two rows `pg` prints. `no resolved build` means the cycle needs `resolve --full`
first; `import it as docs/runbooks/refreshing-dime.md says` means step 3 has not run for this cycle. Copy the
figures and the `real` time into the Log, and add a row to the Validation table in
[`docs/capacity.md`](../capacity.md) (date, model, cycle, matched, precision, recall, wall s).

## 5. Into `gold.meta`

Nothing to run here. The next `fundlens load --cycle <C>` and `publish` copy the newest model's figures
into `gold.meta` (`precision`, `recall`, `precision_top`, `recall_top`, `matched_rows`, `dime_version`);
they ride the next scheduled run or the backfill. After that run:

```bash
# VM
pg -c 'SELECT build_id, precision, recall, precision_top, recall_top, matched_rows, dime_version FROM gold.meta'
```

**Expected:** the figures from step 4. NULLs mean the load ran under a model this cycle was not validated
under (the load's output says `quality: not validated for model <M>`): run step 4 again, then load again.

## 6. Clean up

The import printed both R2 keys, so R2 holds the raw file (ADR-0002) and the local copy can go:

```bash
# VM
docker exec "$(fl pipeline)" rm "/data/fundlens/scratch/dime-raw/v$V/contribDB_$C.csv.gz"
df -h / | tee disk-after.txt
```

**Expected:** about 19 GB more free than before step 2, for 2024. The slim Parquet's local copy is under
`reference/`, inside the container, so a redeploy drops it; `validate` downloads it again from R2 when it is
missing.

## 7. Other cycles

For the backfill (NEU-2060), repeat steps 2–4 and 6 with `export C=<cycle>`. Cycles before electronic filing
(roughly before 2001) carry few `efec.*` ids, so `matched` will be low; that is expected, and `matched_rows`
publishes it.

## 8. Tuning the cluster cap

Re-clustering (NEU-2122, [ADR-0010](../adr/0010-clusters-are-re-clustered-by-constrained-single-linkage.md))
cuts every component holding two first names the model vetoes, or more than `RESOLVE_MAX_CLUSTER_KEYS` keys
(the cluster cap, default 200). This step picks the cap against DIME. `fundlens recluster --max-keys <N>`
rewrites the working file's `cluster` table under another cap in about a minute, and
`fundlens validate --clusters` scores that table, writing nothing; neither touches the crosswalk, silver or R2.
Run it after a deploy that changes resolution, after the backfill (NEU-2060), and after a retrained model.

**Never merge to `main` while this step runs:** a merge redeploys `pipeline` and kills the running command.

Steps 0, 1.2 and 3 must have run for the cycle (helpers defined, `export C=2024`, DIME imported).

### 8.1 The deployed code

```bash
# VM, in tmux
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES
```

**Expected:** `service.version=<sha>` is the merge commit of the code you mean to tune (`git log -1 origin/main`
on the laptop). Anything older: wait for the deploy.

### 8.2 Resolve under the default cap

The working file must come from a `resolve --full` run by code with re-clustering: an older one holds no
`edge` or `component` table, and `recluster` says `no components in the working file`.

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens resolve --full | tee resolve-cap.txt
docker exec "$(fl pipeline)" du -h /data/fundlens/resolution/resolve.duckdb | tee -a resolve-cap.txt
```

**Expected:** about 10 minutes, ending with lines like

```
<keys> contributor keys in <clusters> clusters
recluster: <n> components (<o> oversized, <i> inconsistent) into <p> pieces; largest <before> → <after>
overrides: <m> merges joining <j> clusters into others, <s> splits
crosswalk: <new> new donors, <repointed> keys re-pointed, <redirects> redirects
model <M>: trained, wrote resolution/model/<M>.json
load <s> s, train <s> s, cluster <s> s, recluster <s> s, overrides <s> s, save <s> s, crosswalk <s> s, silver <s> s
```

Copy `largest <before>` from the `recluster` line: the veto-only candidate in 8.4 needs a cap above it.
Add a row to the Resolution table in [`docs/capacity.md`](../capacity.md) (phases, wall s, working file size;
the `recluster` line, `repointed` and `redirects` in Notes).

### 8.3 Validate the default

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" | tee validate-cap-200.txt
```

**Expected:** the step 4 table. These are the live figures, written to `app.resolution_quality`. Copy them into
the Log and the Validation table (`N = 200` in Notes).

### 8.4 The loop

Each candidate is two commands: re-cluster under the cap, then score. First veto-only: a cap above the largest
component, so only the first-name rule cuts.

```bash
# VM, in tmux
export N=1000000
time docker exec "$(fl pipeline)" fundlens recluster --max-keys "$N" | tee "recluster-$N.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-cap-$N.txt"
```

**Expected:** `recluster: … largest <before> → <after>` with no `oversized` component, then the step 4 table,
ending `clusters from /data/fundlens/resolution/resolve.duckdb; nothing written`. Copy both scopes' precision
and recall.

```bash
# VM, in tmux
export N=500
time docker exec "$(fl pipeline)" fundlens recluster --max-keys "$N" | tee "recluster-$N.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-cap-$N.txt"
```

```bash
# VM, in tmux
export N=100
time docker exec "$(fl pipeline)" fundlens recluster --max-keys "$N" | tee "recluster-$N.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-cap-$N.txt"
```

```bash
# VM, in tmux
export N=50
time docker exec "$(fl pipeline)" fundlens recluster --max-keys "$N" | tee "recluster-$N.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-cap-$N.txt"
```

**Expected:** each as the first, `largest … → <N>` or less. Copy every candidate's figures into the Log and a
Validation-table row each (`N = <N>, validate --clusters` in Notes).

### 8.5 Choose the cap

The winner is the candidate meeting NEU-2122's targets (overall precision ≥ 0.8 and recall ≥ 0.88; top 10,000
precision ≥ 0.92 and recall ≥ 0.81). When none does, it is the candidate with the highest overall precision whose
overall recall stays ≥ 0.88 and whose top scope stays ≥ 0.92 / 0.81 (NEU-2122 spec §1.1). When none keeps that floor
either, choose by hand and say why in the Log (2026-11-02 kept 200: below the veto's largest cluster, a cap cut
top-scope recall for little precision). Set it:

```bash
# VM, in tmux. The chosen cap.
export WINNER=200
```

**If the winner is 200**, put the working file back to it, so its `cluster` table matches the crosswalk:

```bash
# VM, in tmux
docker exec "$(fl pipeline)" fundlens recluster --max-keys "$WINNER"
```

**Expected:** the same `recluster:` line as 8.2.

**If the winner is not 200**, change the default instead: open a PR that sets `resolve_max_cluster_keys` in
`src/fundlens/settings.py` to the winner and records the figures (the compose file passes `pipeline` no
`RESOLVE_MAX_CLUSTER_KEYS`, so a Coolify entry would never reach it). Its merge redeploys `pipeline`, so merge it
only now, with nothing running. After the deploy, run 8.1, 8.2 and 8.3 again: 8.2's `recluster:` line ends
`→ <winner>` or less.

### 8.6 Check the crosswalk

```bash
# VM, in tmux
pg -c "SELECT donor_id, count(*) AS keys FROM app.crosswalk GROUP BY donor_id HAVING count(*) > $WINNER ORDER BY keys DESC"
```

**Expected:** `(0 rows)`. A row is a donor an override merged past the cap (overrides apply unconstrained):
check `resolution/overrides.yaml` names its keys. Any other row is a bug: stop and file it.

The next `load` and `publish` carry the figures into `gold.meta` (step 5).

## 9. Diagnosing the wrong pairs

`fundlens diagnose` (NEU-2182) builds the labelled keys `validate --clusters` scores, through the same
function, and takes the working file's wrong pairs apart: by cluster size and matched dollars, by how the pair
was joined (`same key`: DIME splits one of our keys; `direct`: an `edge` between the keys, by probability band;
`chained`: no edge), by the field agreement of the direct wrong pairs (the 20 patterns with the most), and by
how many keys share the pair's name. `--sample <N>` adds N wrong pairs from clusters of 50 keys or fewer, the
same N every time for the same working file, to classify by hand. `fundlens recluster --cluster-threshold <T>`
rebuilds the components from `edge` at or above T into a temp table, leaving `component` alone, then re-clusters
them as usual: the threshold sweep, with no re-predict (`edge` holds every pair at or above 0.9). Both write
nothing to Postgres, R2 or the crosswalk; `recluster` rewrites only the working file's `cluster` table.

**Never merge to `main` while this step runs:** a merge redeploys `pipeline` and kills the running command.

Steps 0, 1.2 and 3 must have run for the cycle, and the working file must come from 8.2 (or a later
`resolve --full`).

### 9.1 The deployed code

```bash
# VM, in tmux
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES
```

**Expected:** `service.version=<sha>` is the merge commit of NEU-2182 or later.

### 9.2 The working file at the default

```bash
# VM, in tmux
docker exec "$(fl pipeline)" fundlens recluster | tee recluster-default.txt
```

**Expected:** the same `recluster:` line as the last 8.2 run (the Log), and no `components rebuilt` line.

### 9.3 Diagnose

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens diagnose --cycle "$C" --sample 100 | tee diagnose.txt
```

**Expected:** a few minutes (it builds what `validate` builds, then the pairs). The first line is
`pairs: <predicted> predicted, <correct> correct, <wrong> wrong (precision <p>)`, and `<p>` is the overall
precision `validate --clusters` gives for the same working file. Then the tables `cluster keys`,
`cluster dollars`, `link`, `keys sharing name`, the patterns, 100 `sample <n>:` blocks, and the last line
`clusters from /data/fundlens/resolution/resolve.duckdb; nothing written`. Copy every table into the Log.

Classify each sampled pair by hand from its two keys' fields and `cid`s as one of: DIME's error, household or
Jr/Sr, common name in one area, junk data, other. Copy the count per class into the Log.

### 9.4 The threshold sweep

Each value is two commands: re-cluster at the threshold, then score.

```bash
# VM, in tmux
export T=0.95
time docker exec "$(fl pipeline)" fundlens recluster --cluster-threshold "$T" | tee "recluster-t$T.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-t$T.txt"
```

```bash
# VM, in tmux
export T=0.97
time docker exec "$(fl pipeline)" fundlens recluster --cluster-threshold "$T" | tee "recluster-t$T.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-t$T.txt"
```

```bash
# VM, in tmux
export T=0.99
time docker exec "$(fl pipeline)" fundlens recluster --cluster-threshold "$T" | tee "recluster-t$T.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-t$T.txt"
```

```bash
# VM, in tmux
export T=0.999
time docker exec "$(fl pipeline)" fundlens recluster --cluster-threshold "$T" | tee "recluster-t$T.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-t$T.txt"
```

```bash
# VM, in tmux
export T=0.9999
time docker exec "$(fl pipeline)" fundlens recluster --cluster-threshold "$T" | tee "recluster-t$T.txt"
time docker exec "$(fl pipeline)" fundlens validate --cycle "$C" --clusters | tee "validate-t$T.txt"
```

**Expected:** each `recluster` prints `components rebuilt from the edges at or above <T>` and its
`recluster:` line, and each `validate` the step 4 table ending `nothing written`. Copy both scopes' precision and
recall for every T into the Log.

### 9.5 Put the working file back

```bash
# VM, in tmux
docker exec "$(fl pipeline)" fundlens recluster
```

**Expected:** the same `recluster:` line as 9.2, so the working file's `cluster` table matches the crosswalk.

### 9.6 Record

Add a Findings entry to [`docs/capacity.md`](../capacity.md) stating which causes make up the wrong pairs, by
count, from 9.3's tables and the hand classification, and the sweep's figures. File a ticket for each fix the
figures point at, with the expected precision gain taken from them.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-02 — First import and validation, 2024 (NEU-2054)

DIME v4.0, cycle 2024, build `20261031T202003Z`, model `20261101T205049Z`.

- **Download** 12m17s: 19,158,623,840 bytes, `1f8b`. The first download went to `reference/dime/v4.0/` inside the
  container and was lost when the deploy of PR #58 recreated it; step 2 now downloads into the `scratch` volume (PR #59).
- **Import** 10m18s, from `6f92e66`: 210,900,861 rows read, 194,682,505 kept, 13,738,582 distinct cids, 0 dropped. The
  first attempt, from `2b670db`, ran DuckDB's 26 GiB limit out of memory four minutes in: `read_csv(…, parallel = false)`
  holds what it decompresses under DuckDB 2.0 (fixed in PR #58).
- **Validate** 2m56s, from `6f92e66`: 25,958,825 of 51,014,276 matched (50.9%); overall 0.3825 / 0.9131, top 10,000
  0.9197 / 0.8143. A read-only diagnosis found about 4.2M rows whose ids were in DIME but whose amount carried cents the
  bulk file drops. Matching in whole dollars (PR #60) and validating again, 3m29s from `b77792d`: **30,175,706 matched
  (59.2%); overall precision 0.3657, recall 0.9149; top 10,000 0.9209 / 0.8120** (2,046,173 correct, 5,594,548 predicted,
  2,236,402 true pairs overall).
- **What the rest of the gap is.** Unmatched: about 6.2M gifts to ActBlue and WinRed themselves, which DIME leaves out
  (only 50 of them match, though the id formats agree), and committees DIME barely holds: TRUMP NATIONAL COMMITTEE JFC
  (5.4M of ours unmatched, 141,536 DIME rows), TRUMP SAVE AMERICA JFC, NRSC and RNC. Precision: DIME splits only 38,121 keys
  (41,772 wrong pairs); the rest is our connected-component chaining. Donor `1661978` holds 1,105 keys DIME labels as
  766 people (Soundex J525 surnames across states). Filed as NEU-2122.

### 2026-11-02 — Tuning the cluster cap, 2024 (NEU-2122)

From `22e56ce`: DIME v4.0, cycle 2024, build `20261102T031624Z`, model `20261102T194152Z` (retrained by this run).

- **Resolve** 9m58s (§8.2): 5,620,495 keys in 3,822,946 clusters. `recluster: 4,085 components (17 oversized, 4,085
  inconsistent) into 10,891 pieces; largest 1,400 → 180`. One override merge. Crosswalk: 6,806 new donors, 31,213 keys
  re-pointed, **0 redirects**. Working file 9.5 GB.
- **The loop** (§8.3–8.4), overall precision / recall, then the top 10,000:

  | N | Pieces | Largest | Overall | Top 10,000 |
  | --- | --- | --- | --- | --- |
  | before (model `20261101T205049Z`) | — | 1,105 | 0.3657 / 0.9149 | 0.9209 / 0.8120 |
  | 1,000,000 (veto only) | 10,891 | 180 | 0.6288 / 0.9121 | 0.9516 / 0.8023 |
  | 500 | 10,891 | 180 | 0.6288 / 0.9121 | 0.9516 / 0.8023 |
  | **200** | 10,891 | 180 | **0.6288 / 0.9121** | **0.9516 / 0.8023** |
  | 100 | 10,910 | 100 | 0.6313 / 0.9121 | 0.9517 / 0.8023 |
  | 50 | 11,130 | 50 | 0.6382 / 0.9032 | 0.9571 / 0.7593 |

  Each `recluster` took about 18 s and each `validate` about 3m35s.
- **Chosen: 200, by hand.** No candidate met NEU-2122's targets, nor §8.5's floor: the veto, which every candidate
  applies, takes top-scope recall from 0.8120 to 0.8023. Above 180 the cap cuts nothing, so 200 is the veto's result
  and still guards against a future chain; 100 gained 0.0025 precision for a redeploy and a second resolve; 50 cost
  top recall 0.043. Not yet known why the veto loses top-scope pairs; a person filed under two first names with
  different initials (WILLIAM and BILL) is the likely case, asserted, not measured.
- **Crosswalk** (§8.6): no donor over 200 keys; the largest holds 180. Donor `1661978`, the J525 chain, now holds 82 keys.
- **Load and publish** 2m50s and 1m44s: `quality: precision 0.6288 recall 0.9121 (top 0.9516/0.8023)` in `gold.meta`.
  Publish logged `kuma push (up) failed: HTTP Error 404` from its heartbeat; the publish itself succeeded.
- **What is left.** About 95% of the 1,204,209 remaining wrong pairs sit in clusters of 50 keys or fewer (capacity.md
  Findings), so the 0.8 precision target needs another fix than a cap.

### 2026-11-03 — Diagnosing the wrong pairs, 2024 (NEU-2182)

From `98acd28`: DIME v4.0, cycle 2024, build `20261103T163743Z`, model `20261103T170755Z`.

- **Plain recluster** (§9.2): `recluster: 4,085 components (17 oversized, 4,085 inconsistent) into 10,891 pieces;
  largest 1,400 → 180`, the same line as NEU-2122's.
- **Diagnose** (§9.3): 3,244,086 pairs predicted, 2,039,877 correct, 1,204,209 wrong (precision 0.6288).

  | Link | Wrong | Correct | Precision |
  | --- | --- | --- | --- |
  | same key | 45,045 | 0 | 0.0000 |
  | direct < 0.95 | 23,771 | 5,050 | 0.1752 |
  | direct 0.95–0.99 | 450,718 | 49,062 | 0.0982 |
  | direct 0.99–0.999 | 53,765 | 18,074 | 0.2516 |
  | direct ≥ 0.999 | 292,732 | 1,913,550 | 0.8673 |
  | chained | 338,178 | 54,141 | 0.1380 |

  | Cluster keys | Wrong | Correct | Precision |
  | --- | --- | --- | --- |
  | 1 | 17,661 | 0 | 0.0000 |
  | 2 | 95,978 | 361,253 | 0.7901 |
  | 3–5 | 271,351 | 686,344 | 0.7167 |
  | 6–10 | 248,144 | 430,072 | 0.6341 |
  | 11–25 | 300,821 | 365,193 | 0.5483 |
  | 26–50 | 156,562 | 131,225 | 0.4560 |
  | 51–200 | 113,692 | 65,790 | 0.3666 |

  | Cluster dollars | Wrong | Correct | Precision |
  | --- | --- | --- | --- |
  | < $1k | 134,950 | 390,611 | 0.7432 |
  | $1k–10k | 450,003 | 829,360 | 0.6483 |
  | $10k–50k | 332,447 | 428,757 | 0.5633 |
  | ≥ $50k | 286,809 | 391,149 | 0.5770 |

  | Keys sharing name | Wrong | Correct | Precision |
  | --- | --- | --- | --- |
  | 1 | 27,961 | 13,727 | 0.3293 |
  | 2–10 | 367,398 | 1,243,766 | 0.7720 |
  | 11–100 | 550,417 | 727,043 | 0.5691 |
  | > 100 | 258,433 | 55,341 | 0.1764 |

  Of the 20 commonest direct patterns, the eight whose first name is `initial only` hold 441,466 wrong pairs and
  23,339 correct: the largest of them, `initial only / exact / differ / null / null`, 176,755 wrong to 691 correct.
- **Hand classification** of the 100 sampled pairs (`classify.csv` on the VM; notes give each call, 12 marked
  `likely` or `unsure`):

  | Class | Pairs |
  | --- | --- |
  | DIME's error | 30 |
  | household or Jr/Sr (family) | 11 |
  | common name in one area | 6 |
  | junk data | 0 |
  | other | 53 (47 two different first names sharing an initial; 6 unsure between common name and DIME's error) |

  By link: of the 33 `direct ≥ 0.999` pairs, 18 are DIME's error; of the 29 `direct 0.95–0.99`, 21 are two first
  names sharing an initial; all 3 `same key` pairs are DIME's error. 54 of the 100 (43 in other, 10 households,
  1 chain) were joined through the model's `first_initial` level (`model.py:67`), which matches any two names
  starting with the same letter, so MARGO and MICHAEL score as an initial (sample 17, 0.9998), and the
  re-clustering veto, which asks for different initials, never cuts them.
- **Sweep** (§9.4), overall precision / recall, then the top 10,000. Each `recluster` took about 18 s and each
  `validate` about 3.5 minutes.

  | T | Pieces | Largest | Overall | Top 10,000 | Wrong pairs |
  | --- | --- | --- | --- | --- | --- |
  | 0.95 (the default) | 10,891 | 180 | 0.6288 / 0.9121 | 0.9516 / 0.8023 | 1,204,209 |
  | 0.97 | 10,294 | 123 | 0.6651 / 0.9002 | 0.9645 / 0.7753 | 1,013,541 |
  | 0.99 | 6,578 | 97 | 0.7881 / 0.8897 | 0.9653 / 0.7681 | 534,829 |
  | **0.999** | 1,662 | 97 | **0.8211 / 0.8864** | 0.9661 / 0.7647 | 431,884 |
  | 0.9999 | 537 | 96 | 0.8978 / 0.8262 | 0.9760 / 0.7073 | 210,438 |

  0.999 is the first configuration to meet NEU-2122's overall targets (≥ 0.8 / ≥ 0.88): it drops 772,325 wrong pairs
  for 57,437 correct ones. No T meets the top-scope recall target of 0.81, which the default already misses
  (0.8023); 0.999 costs it a further 0.0376.
- **Restored** (§9.5): `recluster: 4,085 components (17 oversized, 4,085 inconsistent) into 10,891 pieces; largest
  1,400 → 180`, as 9.2.
- **What it means.** About 30% of the 1,090,517 wrong pairs in clusters of 50 keys or fewer are DIME's own splits:
  about 330,000 pairs (95% interval 230,000–425,000), so the default's precision against the truth is about 0.73
  (0.70–0.76), not 0.6288. Most of the rest is the first-initial level, which a higher threshold also reaches
  because most of its pairs score below 0.999 (21 of the 29 sampled `direct 0.95–0.99` pairs; that band is
  0.0982 precise). The threshold cuts them with 57,437 correct pairs and top-scope recall; fixing the level
  targets them alone. Two tickets follow: fix the first-initial level, then re-run this sweep on the fixed model
  and set the threshold.

### 2026-11-03 — The first-name levels, 2024 (NEU-2188)

From `a2ca75f`: DIME v4.0, cycle 2024, build `20261103T175128Z`, model `20261104T012451Z`. The first-name
comparison's initial level now fires only for a single letter, a nickname level sits after exact match, and the
veto reads no initials (`docs/specs/NEU-2188-first-name-levels.md`).

- **Resolve** (§8.2): 5,620,495 contributor keys in 4,009,899 clusters. `recluster: 7,339 components (3 oversized,
  7,339 inconsistent) into 18,975 pieces; largest 263 → 103`. Crosswalk: 197,265 new donors, 284,508 keys
  re-pointed, 10,312 redirects; one override merge. Phases: load 10.01 s, train 174.71 s, cluster 112.62 s,
  recluster 10.98 s, overrides 0.19 s, save 0.15 s, crosswalk 32.82 s, silver 197.31 s. Working file 9.4 GB.
- **Validate** (§8.3), against 0.6288 / 0.9121 and 0.9516 / 0.8023 before:

  | Scope | Precision | Recall | Keys | Correct | Predicted | True |
  | --- | --- | --- | --- | --- | --- | --- |
  | overall | 0.8229 | 0.9105 | 4,283,076 | 2,036,148 | 2,474,404 | 2,236,402 |
  | top 10,000 | 0.9739 | 0.7988 | 65,053 | 343,871 | 353,072 | 430,470 |

  The ticket's floors: overall ≥ 0.70 / ≥ 0.90 met; top 10,000 not below 0.9516 / 0.8023 **missed on recall by
  0.0035** (1,495 correct pairs). Accepted 2026-11-03: the same change cut the top 10,000's wrong pairs from
  about 17,566 to 9,201. The top-scope recall target moves to NEU-2189, which re-tunes the threshold on this model.
- **Crosswalk** (§8.6): no donor over 200 keys, `(0 rows)`.
- **Plain recluster** (§9.2): the same `recluster:` line as the resolve.
- **Diagnose** (§9.3): 2,474,404 pairs predicted, 2,036,148 correct, 438,256 wrong (precision 0.8229).

  | Link | Wrong | Correct | Precision |
  | --- | --- | --- | --- |
  | same key | 45,045 | 0 | 0.0000 |
  | direct < 0.95 | 7,049 | 9,808 | 0.5818 |
  | direct 0.95–0.99 | 16,559 | 13,404 | 0.4474 |
  | direct 0.99–0.999 | 80,967 | 43,825 | 0.3512 |
  | direct ≥ 0.999 | 207,789 | 1,915,744 | 0.9021 |
  | chained | 80,847 | 53,367 | 0.3976 |

  | Cluster keys | Wrong | Correct | Precision |
  | --- | --- | --- | --- |
  | 1 | 20,630 | 0 | 0.0000 |
  | 2 | 74,733 | 393,957 | 0.8405 |
  | 3–5 | 157,300 | 706,016 | 0.8178 |
  | 6–10 | 93,009 | 418,291 | 0.8181 |
  | 11–25 | 67,057 | 347,228 | 0.8381 |
  | 26–50 | 19,432 | 114,197 | 0.8546 |
  | 51–200 | 6,095 | 56,459 | 0.9026 |

  | Cluster dollars | Wrong | Correct | Precision |
  | --- | --- | --- | --- |
  | < $1k | 91,390 | 409,187 | 0.8174 |
  | $1k–10k | 189,722 | 831,993 | 0.8143 |
  | $10k–50k | 87,999 | 417,687 | 0.8260 |
  | ≥ $50k | 69,145 | 377,281 | 0.8451 |

  | Keys sharing name | Wrong | Correct | Precision |
  | --- | --- | --- | --- |
  | 1 | 14,009 | 13,826 | 0.4967 |
  | 2–10 | 191,884 | 1,239,591 | 0.8660 |
  | 11–100 | 182,587 | 726,623 | 0.7992 |
  | > 100 | 49,776 | 56,108 | 0.5299 |

  The 20 commonest direct patterns (first name / last name / ZIP5 / employer / occupation):

  | Pattern | Wrong | Correct |
  | --- | --- | --- |
  | exact / exact / exact / null / null | 49,118 | 565,631 |
  | exact / exact / differ / exact / same | 41,176 | 42,184 |
  | exact / exact / differ / null / null | 30,357 | 36,543 |
  | exact / exact / differ / exact / differ | 19,715 | 33,139 |
  | exact / exact / differ / differ / differ | 19,202 | 27,440 |
  | jw ≥ 0.8 / exact / differ / null / null | 13,129 | 145 |
  | nickname / exact / exact / null / null | 12,383 | 49,468 |
  | initial only / exact / exact / null / null | 8,904 | 4,824 |
  | nickname / exact / differ / null / null | 7,751 | 1,920 |
  | jw ≥ 0.8 / exact / differ / differ / differ | 7,054 | 136 |
  | exact / exact / differ / differ / same | 6,571 | 16,369 |
  | exact / exact / exact / differ / differ | 6,081 | 284,300 |
  | jw ≥ 0.8 / exact / exact / null / null | 6,056 | 3,514 |
  | nickname / exact / differ / differ / differ | 5,121 | 2,009 |
  | exact / exact / differ / null / differ | 5,092 | 12,010 |
  | exact / exact / exact / exact / differ | 3,935 | 262,832 |
  | exact / differ / exact / null / null | 3,460 | 12,096 |
  | jw ≥ 0.92 / exact / exact / null / null | 3,122 | 5,761 |
  | exact / exact / exact / null / differ | 2,994 | 159,056 |
  | exact / differ / differ / null / null | 2,716 | 282 |

  `initial only`: one pattern in the top 20, 8,904 wrong to 4,824 correct (the ticket's floor is under 50,000;
  NEU-2182's top 20 held eight, 441,466 wrong). `nickname`: three, 25,255 wrong to 53,397 correct. `jw ≥ 0.8`:
  three, 26,239 wrong to 3,795 correct, now the first-name level behind the most wrong pairs.
- **Hand classification** of the 100 sampled pairs:

  | Class | Pairs |
  | --- | --- |
  | DIME's error | 79 |
  | household or Jr/Sr (family) | 4 |
  | common name in one area | 12 |
  | junk data | 0 |
  | other | 5 (Jaro-Winkler-close first names that are two people: BARRY/LARRY, CLAIRE/LAURIE, BENTON/BRENT; a nickname and a surname drift, MELINDA PETERS/LINDA PETERSON; a chain through a shared employer) |

  Of DIME's 79, 5 are `same key` and 11 are two `cid`s that differ by exactly 5×10¹⁵ (`3800298286` and
  `5000003800298286`, sample 4): whether DIME numbers one contributor both ways is not yet checked against its
  codebook. The households are JOAN/JON, PAMELA/PAUL, JOE/JON (Jaro-Winkler) and J MICHAEL/JEANNE (an initial
  pair). Of the 13 pairs joined through the nickname level, 8 are DIME's error.
- **Load and publish** (§5): `load` 3m9s, `publish` 1m38s; published build `20261103T175128Z` (previous
  `20261103T163743Z`); `gold.meta` holds 0.8229 / 0.9105, top 0.9739 / 0.7988, 30,175,706 matched rows, DIME v4.0.
- **What it means.** The fix removed what NEU-2182 traced to the first-initial level (54 of its 100 samples): no
  sampled pair here is two full names sharing only a first letter. The remaining wrong pairs are mostly DIME's:
  about 340,000 of the 432,161 in clusters of 50 keys or fewer if the sample holds (79 of 100; 95% interval about
  300,000–370,000), which puts precision against the truth at about 0.95–0.97, not 0.8229. What linkage still gets wrong is common names in one area and first names close by
  Jaro-Winkler; the `jw ≥ 0.8` patterns with a different ZIP are 20,183 wrong to 281 correct.
