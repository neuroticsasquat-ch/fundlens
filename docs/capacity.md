# Capacity record

What the pipeline costs on `music-box-dancer` (spec §10.6): time per step and the disk it fills, per
cycle. At the end of v1 these figures are checked against the handover's triggers for moving to an
ephemeral runner: a weekly run over 6–8 h, or steady-state disk over ~300 GB. Each measured run gets a
row, filled in once from its runbook's figures and never changed after that. A run that measures again
gets a new row.

Step times are each step's `duration_s` from its R2 marker (`markers/cycle=<c>/build=<b>/<step>.json`).
`seats` writes no marker, so its time is `time`'s `real`. Sizes are decimal GB. Bronze is the cycle's
zips in R2, silver is the cycle's build under `/data/fundlens/silver`, and gold is the `gold` schema's
tables with their indexes and TOAST. A step a run did not measure is `—`.

## Per cycle

Load is the DuckDB → CSV → `COPY` method of ADR-0007, written `<total> (<aggregates> + <copy>)`: the whole
step, then its two halves (DuckDB aggregates and CSV, then `COPY`, indexes and `ANALYZE`).

| Cycle | Date | Build | SHA | Extract s | Seats s | Transform s | Load s | Publish s | Bronze GB | Silver GB | Gold GB | Peak `pipeline` memory | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | 2026-10-31 | `20261031T012553Z` | `d67cec2` | 454 | 5 | 407 | 4.1 (0.84 + 2.21) | 75 | 4.77 | 0.91 | 0.04 | 27.2 GiB | First run: committee-level gold, no resolution ([first-run.md](runbooks/first-run.md), NEU-2046). Publish includes its deliberate 75 s wait before the purge. |
| 2024 | 2026-10-31 | `20261031T164731Z` | `27e1bd0` | — | — | 1871 | — | — | — | — | — | 24.34 GiB | Transform only, with contributor keys (NEU-2047) and the join-side fix (NEU-2076), `DUCKDB_THREADS=6`. 1,602 s of it in `04_contribution.sql`. Six silver tables; `contributor` 5,185,485 rows. |
| 2024 | 2026-10-31 | `20261031T202003Z` | `47e3dd5` | — | — | 1343 | — | — | — | — | — | 23.46 GiB | Transform only, with JFC attributions (NEU-2078). 1,088 s of it in `04_contribution.sql`, 14 s in `06_jfc_attribution.sql`. Seven silver tables; `jfc_attribution` 17,037,819 rows, `contributor` 5,620,495 (435,010 more than NEU-2047's build). |
| 2024 | 2026-11-01 | `20261031T202003Z` | `a4c82b8` | — | 6 | — | 169 (73.08 + 93.51) | 91 | — | 2.03 | 2.61 | 24.54 GiB | First resolved build: donor tables live ([first-resolved-run.md](runbooks/first-resolved-run.md), NEU-2079). Resolved, loaded and published NEU-2078's build; `seats` ran only to add the `race` partition its transform-only run lacked. Silver is after resolution's bucketed rewrite. Peak memory is resolve's; load and publish stayed below it. |
| 2024 | 2026-11-02 | `20261102T031624Z` | `22e56ce` | — | — | — | 170 (71.34 + 91.29) | 104 | — | — | — | — | Load and publish after re-clustering (NEU-2122, [refreshing-dime.md](runbooks/refreshing-dime.md) §8); both times are `time`'s `real`. 3,822,946 donors, 6,968,328 `donor_top_recipient` rows, 1 `donor_redirect`. |

The backfill (NEU-2060) and the weekly run (M5) add their own figures here.

## Resolution

One `fundlens resolve --full` per row (spec §6.3–§6.6): every cycle's contributor keys linked, clustered and
given donor_ids. The phases are the run's own timings, in run order, from its output line `load <s> s, train <s> s, …`; wall time is
the `resolved` marker's `duration_s`. Peak memory is `pipeline`'s between the run's start and end. The working
file is `/data/fundlens/resolution/resolve.duckdb` after the run; from NEU-2122 it also keeps the run's `edge` and
`component` tables, and the Notes give the `recluster` summary line and the cluster cap.

| Date | Model | Cycles (build) | SHA | Contributor keys | Clusters | Load / train / cluster / recluster / overrides / save / crosswalk / silver s | Wall s | Peak `pipeline` memory | Working file GB | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-01 | `20261101T024736Z` | 2024 (`20261031T202003Z`) | `a4c82b8` | 5,620,495 | 3,816,141 | 10.08 / 190.33 / 111.11 / — / 0.00 / 0.12 / 101.13 / 346.49 | 762 | 24.54 GiB | 9.91 | First `resolve --full` on real keys ([first-resolved-run.md](runbooks/first-resolved-run.md), NEU-2079). Trained (EM converged after 8 iterations), no overrides, DuckDB memory limit 26.0 GiB. The peak came at 02:55:01, early in `silver`, not in Splink. |
| 2026-11-02 | `20261102T194152Z` | 2024 (`20261102T031624Z`) | `22e56ce` | 5,620,495 | 3,822,946 | 10.21 / 188.02 / 106.62 / 11.85 / 0.18 / 0.13 / 18.81 / 253.41 | 598 | — | 9.5 | First run with re-clustering ([refreshing-dime.md](runbooks/refreshing-dime.md) §8, NEU-2122), cap 200. `recluster: 4,085 components (17 oversized, 4,085 inconsistent) into 10,891 pieces; largest 1,400 → 180`. Crosswalk: 6,806 new donors, 31,213 keys re-pointed, 0 redirects; one override merge. Wall time is `time`'s `real`; peak memory not measured. |

## Validation

One `fundlens validate` per row ([refreshing-dime.md](runbooks/refreshing-dime.md), NEU-2054): a cycle's resolved
donors scored against DIME, pairwise, over the labelled contributor keys (ADR-0009). Matched is the counted
contributions DIME labels by exactly one `bonica.cid`, of all counted contributions. Precision and recall are the
`overall` scope, then the `top` one (the 10,000 DIME donors with the most matched dollars). Wall time is `time`'s `real`.
A row from `validate --clusters` (the cluster-cap loop, refreshing-dime.md §8) scores the working file's clusters and
writes nothing to `app.resolution_quality`; its Notes give the cap.

| Date | Model | Cycle (build) | DIME | Matched | Precision (top) | Recall (top) | Wall s | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-02 | `20261101T205049Z` | 2024 (`20261031T202003Z`) | v4.0 | 25,958,825 of 51,014,276 (50.9%) | 0.3825 (0.9197) | 0.9131 (0.8143) | 176 | First run, from `6f92e66`. Amounts compared to the cent, so DIME's cents (260.25 against the bulk file's 260) missed about 4.2M rows; superseded by the next row. |
| 2026-11-02 | `20261101T205049Z` | 2024 (`20261031T202003Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.3657 (0.9209) | 0.9149 (0.8120) | 209 | From `b77792d`: amounts in whole dollars (PR #60). The unmatched rest is DIME's coverage: gifts to ActBlue and WinRed themselves, and the Trump JFCs, RNC and NRSC. Precision is our over-merging: chained clusters, NEU-2122 (DIME's own key splits are 1.4% of the wrong pairs). |
| 2026-11-02 | `20261102T194152Z` | 2024 (`20261102T031624Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.6288 (0.9516) | 0.9121 (0.8023) | 216 | From `22e56ce`: re-clustered, N = 200, the chosen default and the live figures. 2,039,877 correct, 3,244,086 predicted, 2,236,402 true pairs overall. Identical at N = 1,000,000 (veto only) and N = 500: the veto leaves no cluster over 180 keys. |
| 2026-11-02 | `20261102T194152Z` | 2024 (`20261102T031624Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.6288 (0.9516) | 0.9121 (0.8023) | 206 | N = 1,000,000 (veto only), validate --clusters, nothing written. |
| 2026-11-02 | `20261102T194152Z` | 2024 (`20261102T031624Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.6288 (0.9516) | 0.9121 (0.8023) | 213 | N = 500, validate --clusters, nothing written. |
| 2026-11-02 | `20261102T194152Z` | 2024 (`20261102T031624Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.6313 (0.9517) | 0.9121 (0.8023) | 218 | N = 100, validate --clusters, nothing written. 59 oversized components, 10,910 pieces. |
| 2026-11-02 | `20261102T194152Z` | 2024 (`20261102T031624Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.6382 (0.9571) | 0.9032 (0.7593) | 218 | N = 50, validate --clusters, nothing written. 202 oversized components, 11,130 pieces. |
| 2026-11-03 | `20261103T145232Z` | 2024 (`20261103T142758Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.6288 (0.9516) | 0.9121 (0.8023) | 221 | From `abafafe`: the Biden→Harris handoff split (NEU-2126). Identical to `20261102T194152Z`: the change moves money between candidates and leaves contributor keys alone. |

## Findings

- **Memory, not time, is the limit (2024 first run).** The transform peaked at 27.2 GiB in `pipeline`, against a
  40 GiB container and DuckDB's 28 GB `memory_limit`, in `04_contribution.sql` (51,014,276 `contribution` rows
  in 2024). In the dev container the same SQL failed at 6 GB and 8 GB and completed at 10 GB. A transform killed
  for memory uploads nothing, so it fails safe.
- **A misplaced join was part of it, but the 2024 peak is still high (NEU-2076).** DuckDB estimates a `read_csv`
  view at a few dozen rows, so its build-side optimizer built each `indiv LEFT JOIN <small table>` hash table on
  the whole bulk file. With NEU-2047's four lookup joins the 2024 transform ran out of memory. The transform now
  disables that optimizer (`transform.runner.connect`). On a synthetic 10M-row `indiv`, the contribution build's
  minimum `memory_limit` fell from 4 GB to 800 MB (300 MB without the lookup joins). On real data the 2024
  transform now completes, but `pipeline` still peaked at 24.34 GiB, at 17:45:03 UTC: after
  `04_contribution.sql`, 51 s into `06_contributor.sql`. The runner logs no time for the silver checks and
  Parquet writes that follow, so the peak is in one of those three. The least memory the real build needs was
  not measured; the in-memory database holds every silver table until it is written,
  and DuckDB moves data to disk only under pressure. So before the backfill (NEU-2060) runs a cycle whose `indiv`
  is larger than 2024's, raise `DUCKDB_MEMORY_LIMIT` within the container, or measure that cycle first.
- **Gold is small.** The whole `fundlens` database was 49 MB after publish: contributions stay in silver Parquet
  (ADR-0006), and gold holds aggregates only. Load is seconds, not the spec's 10–30 GB estimate (§3.4); that
  estimate assumed donor tables, which arrive in M3.
- **Time:** extract, transform and publish dominate. Since NEU-2047 the 2024 transform takes 31 minutes, 27 of
  them in `04_contribution.sql`, which normalizes each distinct name, ZIP, employer and occupation in Python; it
  took 7 minutes before. A cycle end to end is about 40 minutes, still far inside the handover's 6–8 h trigger
  for an ephemeral runner.
- **JFC attributions cost little (NEU-2078).** The 2024 transform with `jfc_attribution` took 22 minutes, 18 of
  them in `04_contribution.sql`, and peaked at 23.46 GiB; `06_jfc_attribution.sql` took 14 s. That is faster than
  NEU-2047's 31 minutes although `04_contribution.sql` now also normalizes the 15J lines' values. The difference
  is not explained: neither run recorded the box's other load. The 435,010 new `contributor` rows match the
  spec's measured 434,469 new 15J keys (§6.11) to within 0.2%.
- **Resolution costs less than a transform (NEU-2079).** `resolve --full` linked 2024's 5,620,495 contributor keys into
  3,816,141 donors in 12.7 minutes, and `pipeline` peaked at 24.54 GiB, below the transform's 27.2 GiB. Splink itself,
  train and cluster, took 5 minutes. The longest phase was `silver` (346 s), which rewrote 51,014,276 contributions into
  256 buckets and uploaded them, and the peak came early in it. The working file is 9.91 GB. `--full` loads every
  cycle's keys into one table (spec §6.10), so the backfill (NEU-2060) resolves the union of every cycle's keys at once,
  and its memory follows that count, not one cycle's. Measure a few cycles together before resolving them all.
- **Donors are most of gold now (NEU-2079).** With 3.8M donors and 7.0M `donor_top_recipient` rows, gold grew from 0.04 GB
  to 2.61 GB and the database from 49 MB to 3.68 GB (with `app.crosswalk`'s 5.6M rows). Load took 169 s (aggregates
  73 s, `COPY` 94 s), against 4 s without donors. The spec's 10–30 GB gold estimate (§3.4) is for every cycle; one cycle
  is 2.6 GB.
- **The first-name veto does the work; the cap is a guard (NEU-2122).** Re-clustering took 12 s inside `resolve --full`
  (about 18 s as `fundlens recluster`). All 4,085 re-clustered components held a vetoed pair; 17 were over 200 keys. The
  veto alone cut the largest cluster from 1,400 keys to 180 and wrong pairs from 3,548,375 to 1,204,209, taking 2024's
  precision from 0.3657 to 0.6288 for 6,296 fewer correct pairs. A cap under 180 buys little: at N = 50 every cluster is
  50 keys or fewer, yet only 59,266 more wrong pairs go, and top-10,000 recall falls to 0.7593. So about 95% of the
  remaining wrong pairs sit inside clusters of 50 keys or fewer, out of reach of any cap.
