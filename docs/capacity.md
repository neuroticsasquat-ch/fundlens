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

The weekly run (M5) adds its own figures here. The backfill's are under [Backfill](#backfill), apart from its last
load and publish of every cycle together, which gets a row here.

## Backfill

One row per cycle the backfill built ([backfill.md](runbooks/backfill.md) step 3.3, NEU-2060), oldest first, each
from one build's extract, seats, transform, load and publish, without resolution. `indiv` is the size FEC served
for the cycle's `indiv` zip, the input the transform's memory follows; 2024's was the reference for raising
DuckDB's limit. Gold is all of gold after the cycle's publish: every cycle published so far, without donors except
2024's. The peak is `pipeline`'s from the run's 10 s sampler, with the step whose log line came last before it.
Load is written as under Per cycle. DuckDB limit is `DUCKDB_MEMORY_LIMIT` during the cycle. Free disk is on `/` after the
publish, in decimal GB.

| Cycle | Date | Build | SHA | `indiv` GB | Extract s | Seats s | Transform s | Load s | Publish s | Bronze GB | Silver GB | Gold GB | Peak `pipeline` memory | DuckDB limit | Free disk GB | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

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
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | `a2ca75f` | 5,620,495 | 4,009,899 | 10.01 / 174.71 / 112.62 / 10.98 / 0.19 / 0.15 / 32.82 / 197.31 | — | — | 9.4 | First run with the first-name levels of NEU-2188 (initial pair, nickname pair, the veto blind to initials), cap 200. `recluster: 7,339 components (3 oversized, 7,339 inconsistent) into 18,975 pieces; largest 263 → 103`. Crosswalk: 197,265 new donors, 284,508 keys re-pointed, 10,312 redirects; one override merge. The phases sum to 539 s; wall time and peak memory not captured. |

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
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8229 (0.9739) | 0.9105 (0.7988) | — | From `a2ca75f`: NEU-2188's first-name levels, N = 200, threshold 0.95; the live figures. 2,036,148 correct, 2,474,404 predicted, 2,236,402 true pairs overall; top 10,000: 343,871 correct, 353,072 predicted, 430,470 true. Wall time not captured. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8023 (0.9736) | 0.9146 (0.8010) | 258 | T = 0.90, validate --clusters, nothing written (NEU-2189). 24,087 pieces, largest 617 → 103; 503,913 wrong pairs. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8031 (0.9737) | 0.9146 (0.8010) | 218 | T = 0.92, validate --clusters, nothing written (NEU-2189). 23,972 pieces, largest 568 → 103; 501,518 wrong pairs. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8052 (0.9737) | 0.9143 (0.8009) | 215 | T = 0.93, validate --clusters, nothing written (NEU-2189). 19,253 pieces, largest 265 → 103; 494,724 wrong pairs. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8090 (0.9737) | 0.9138 (0.8005) | 210 | T = 0.94, validate --clusters, nothing written (NEU-2189). 19,129 pieces, largest 265 → 103; 482,338 wrong pairs. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8229 (0.9739) | 0.9105 (0.7988) | 213 | T = 0.95, validate --clusters, nothing written (NEU-2189). The default, chosen (refreshing-dime §9.6, tier 4); 18,975 pieces, largest 263 → 103; 438,256 wrong pairs. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8254 (0.9741) | 0.9086 (0.7965) | 218 | T = 0.97, validate --clusters, nothing written (NEU-2189). 18,324 pieces, largest 258 → 102; 429,930 wrong pairs. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8279 (0.9741) | 0.9059 (0.7948) | 216 | T = 0.99, validate --clusters, nothing written (NEU-2189). 16,354 pieces, largest 238 → 102; 421,254 wrong pairs. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8714 (0.9865) | 0.8865 (0.7615) | 213 | T = 0.999, validate --clusters, nothing written (NEU-2189). 6,137 pieces, largest 148 → 97; 292,694 wrong pairs. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.9001 (0.9895) | 0.8468 (0.7118) | 211 | T = 0.9999, validate --clusters, nothing written (NEU-2189). 4,243 pieces, largest 122 → 96; 210,264 wrong pairs. |
| 2026-11-04 | `20261104T173004Z` | 2024 (`20261103T175128Z`) | v4.0 | 30,175,706 of 51,014,276 (59.2%) | 0.8244 (0.9762) | 0.9075 (0.7867) | 225 | From `c7e8fbb`: NEU-2055's first adjudication run applied (357 merges, 458 splits); the live figures. 2,029,462 correct, 2,461,785 predicted, 2,236,402 true pairs overall; top 10,000: 338,642 correct, 346,911 predicted, 430,470 true. |

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
- **A third of the wrong pairs are DIME's; half are one model level (NEU-2182).** A hand classification of 100 wrong
  pairs from clusters of 50 keys or fewer found 30 that DIME splits but are one person (HAL and HAROLD GEORGE at one
  ZIP; one professor at two ZIPs), 11 households, 6 common names in one area and 53 others, nearly all two first
  names sharing an initial. Scaled to the 1,090,517 wrong pairs in those clusters, DIME's own error is about 330,000
  pairs (95% interval 230,000–425,000), so 2024's precision against the truth is about 0.73, not 0.6288. 54 of the 100
  were joined through the model's `first_initial` level, which treats MARGO and MICHAEL as an initial and its
  full name; among direct wrong pairs the `initial only` patterns hold at least 441,466 wrong to 23,339 correct.
  A higher cluster threshold also reaches them, since most of them score below 0.999: at 0.999 overall precision
  and recall are 0.8211 / 0.8864, the first configuration to meet the overall targets, for 57,437 correct pairs and
  top-10,000 recall 0.8023 → 0.7647.
- **Telling an initial and a nickname from two first names sharing a letter removes nearly two thirds of
  the wrong pairs (NEU-2188).** With the initial level confined to a single letter, a nickname level (prefix of three letters or
  more, or the vendored nickname table) and a veto blind to initials, 2024's wrong pairs fell from 1,204,209 to
  438,256 for 3,729 correct ones: overall precision 0.6288 → 0.8229, recall 0.9121 → 0.9105, both past
  NEU-2122's overall targets at the default threshold. The top 10,000 gained precision (0.9516 → 0.9739) and lost a
  little recall (0.8023 → 0.7988, 1,495 correct pairs under the ticket's floor; accepted, and carried to NEU-2189),
  a fraction of what the 0.999 threshold cost it (0.7647). Among direct wrong pairs the `initial only` patterns in the top 20 now hold 8,904
  wrong pairs, against 441,466. Of the 100 sampled wrong pairs, 79 look like DIME's own splits (11 of them two
  `cid`s that differ by exactly 5×10¹⁵); the rest are common names in one area (12), other causes (5, chiefly
  Jaro-Winkler-close first names that are two people: BARRY/LARRY, CLAIRE/LAURIE) and households (4). If the sample holds, about 340,000 of the
  432,161 wrong pairs in clusters of 50 keys or fewer are DIME's, and precision against the truth is about
  0.95–0.97.
- **The threshold is not where top-scope recall went; 0.95 stays (NEU-2189).** Swept from the match threshold
  (0.90) to 0.9999 on NEU-2188's model, against 0.95: lowering it to 0.90 adds 9,283 correct pairs and 924 of the
  1,495 top-10,000 pairs below the 0.8023 floor, for 65,657 more wrong pairs (precision 0.8229 → 0.8023), and top
  recall stops at 0.8010. Raising it removes wrong pairs at a far worse rate than on NEU-2182's model: at 0.999,
  145,562 wrong for 53,507 correct (2.7 to 1; it was 772,325 for 57,437, 13.4 to 1, before the first-name fix),
  and top-10,000 recall falls 0.7988 → 0.7615; at 0.9999, 227,992 wrong for 142,282 correct, and 0.7118. The
  first-initial fix took most of what a higher threshold used to remove: it now buys about 2.7 wrong pairs per
  correct one lost, and if NEU-2188's sample holds, many of those "wrong" pairs are DIME's own errors, so the trade
  is worse than it looks. The cluster cap bound at no threshold (largest 103 keys at most), and 0.95 is kept by the
  rule's last tier, top-scope recall 0.7988 accepted.

## Triggers

The handover's triggers for moving the pipeline to an ephemeral runner (spec §10.6, §13): a weekly run over 6–8 h,
or steady-state disk over ~300 GB. Not yet checked. The backfill (NEU-2060) writes the check here from the rows
above ([backfill.md](runbooks/backfill.md) step 9): the weekly run's estimated time, the steady-state disk, the
memory peaks against the 40 GiB container, and which triggers fired, each with the ticket filed for it.
