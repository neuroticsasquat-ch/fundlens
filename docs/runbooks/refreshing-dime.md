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
