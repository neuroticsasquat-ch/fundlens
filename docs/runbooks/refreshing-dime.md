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

**Not in this runbook:** tuning the resolution thresholds against the figures (a follow-up ticket), the
methodology page and the `/v1/meta` fields (NEU-2056).

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

Copy the cycle's `contribDB_<cycle>.csv.gz` link from the download page (right-click → *Copy link*), then
set it, with its `dl=0` changed to `dl=1` so Dropbox sends the file rather than a preview page:

```bash
# VM
export DIME_URL='<the copied link, ending dl=1>'
```

```bash
# VM
docker exec "$(fl pipeline)" mkdir -p "/data/fundlens/reference/dime/v$V"
time docker exec -e DIME_URL="$DIME_URL" "$(fl pipeline)" python -c 'import os, sys, urllib.request; urllib.request.urlretrieve(os.environ["DIME_URL"], sys.argv[1])' "/data/fundlens/reference/dime/v$V/contribDB_$C.csv.gz"
docker exec "$(fl pipeline)" ls -l "/data/fundlens/reference/dime/v$V/contribDB_$C.csv.gz"
docker exec "$(fl pipeline)" python -c 'import sys; print(open(sys.argv[1], "rb").read(2).hex())' "/data/fundlens/reference/dime/v$V/contribDB_$C.csv.gz"
```

**Expected:** for 2024, a size of `19158623840` bytes; every cycle prints `1f8b` (a gzip file). A
size of a few kB, or anything else in place of `1f8b`, is an HTML page: check the link ends `dl=1` and download again.

## 3. Import

```bash
# VM, in tmux
time docker exec "$(fl pipeline)" fundlens dime --cycle "$C" --import "/data/fundlens/reference/dime/v$V/contribDB_$C.csv.gz" | tee import.txt
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
docker exec "$(fl pipeline)" rm "/data/fundlens/reference/dime/v$V/contribDB_$C.csv.gz"
df -h / | tee disk-after.txt
```

**Expected:** about 19 GB more free than before step 2, for 2024. The slim Parquet stays in the local cache;
`validate` downloads it again if the disk is ever dropped.

## 7. Other cycles

For the backfill (NEU-2060), repeat steps 2–4 and 6 with `export C=<cycle>`. Cycles before electronic filing
(roughly before 2001) carry few `efec.*` ids, so `matched` will be low; that is expected, and `matched_rows`
publishes it.

## Log

<!-- Append entries below; never rewrite one. -->
