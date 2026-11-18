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
| 1980–2026 | 2026-11-17 | `20261116T005426Z` | `dbe2ffd` | — | — | — | 1402 (684.82 + 696.97) | 157 | — | — | — | — | The backfill's last load and publish, of every cycle with its donors ([backfill.md](runbooks/backfill.md) step 6, NEU-2060): `fundlens run --cycle 2024 --from load` on 2024's rebuild. `gold donor` alone took 6 min. 12,564,451 donors, 26,835,891 `donor_cycle`, 34,127,960 `donor_top_recipient`, 70,635 `donor_redirect` rows. The whole database is 23.11 GB after it, against 7.6 GB before; gold alone was not measured. `real` 26m10s. |

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
| 1980 | 2026-11-13 | `20261113T232917Z` | `1aed283` | 0.01 | 7 | 5 | 75 | 197 (79.26 + 106.97) | 92 | 0.02 | 0.02 | 2.97 | 17.14 GiB, gold donor | 28GB | 259 |Fourth build. The first (`20261113T010657Z`) failed `silver_committee_transfer_recipient.sql` (NEU-2281); rebuilt after NEU-2283 and NEU-2287. |
| 1982 | 2026-11-13 | `20261113T233554Z` | `1aed283` | 0.00 | 7 | 5 | 38 | 192 (78.26 + 106.10) | 92 | 0.02 | 0.01 | 2.97 | 14.23 GiB, gold donor | 28GB | 259 |Rebuilt after NEU-2283 and NEU-2287 (Gramm, TX-06). |
| 1984 | 2026-11-13 | `20261113T154614Z` | `529ab9e` | 0.01 | 7 | 5 | 60 | 200 (79.43 + 108.63) | 93 | 0.02 | 0.02 | 2.94 | 15.08 GiB, gold check gold_top_donor_not_self_funding | 28GB | 261 |Rebuilt after NEU-2283. The peak is in load's gold phase, just after `gold donor`. |
| 1986 | 2026-11-13 | `20261113T155247Z` | `529ab9e` | 0.01 | 7 | 6 | 72 | 200 (78.23 + 107.36) | 95 | 0.02 | 0.02 | 2.94 | 12.95 GiB, gold donor | 28GB | 261 |Rebuilt after NEU-2283. KY-02 at $0: William Natcher took no contributions. |
| 1988 | 2026-11-13 | `20261113T155936Z` | `529ab9e` | 0.01 | 7 | 5 | 98 | 195 (76.49 + 105.87) | 95 | 0.02 | 0.03 | 2.94 | 12.55 GiB, gold donor | 28GB | 261 |Rebuilt after NEU-2283. |
| 1990 | 2026-11-13 | `20261113T234150Z` | `1aed283` | 0.01 | 7 | 6 | 106 | 197 (78.51 + 107.91) | 94 | 0.02 | 0.04 | 2.97 | 13.45 GiB, gold donor | 28GB | 259 |Rebuilt after NEU-2283 and NEU-2287. |
| 1992 | 2026-11-14 | `20261114T201011Z` | `8b503a5` | 0.02 | 6 | 5 | 168 | 225 (83.31 + 119.60) | 92 | 0.03 | 0.06 | 3.22 | 13.25 GiB, gold donor | 28GB | 248 |Rebuilt after NEU-2283, then after NEU-2294 (3 filings moved to their 1992 district). KY-02 at $0: Natcher. |
| 1994 | 2026-11-13 | `20261113T162226Z` | `529ab9e` | 0.02 | 7 | 6 | 153 | 198 (78.16 + 105.88) | 95 | 0.04 | 0.06 | 2.94 | 12.49 GiB, gold donor | 28GB | 261 |The first build (`20261113T023353Z`) stopped at `load` on a NUL byte (NEU-2282); rebuilt after NEU-2283. |
| 1996 | 2026-11-13 | `20261113T163032Z` | `529ab9e` | 0.03 | 8 | 5 | 211 | 206 (78.71 + 114.08) | 93 | 0.04 | 0.08 | 2.94 | 12.65 GiB, gold donor | 28GB | 261 |Rebuilt after NEU-2283. |
| 1998 | 2026-11-13 | `20261113T163943Z` | `529ab9e` | 0.03 | 8 | 5 | 183 | 206 (79.41 + 112.89) | 94 | 0.04 | 0.07 | 2.94 | 14.58 GiB, gold donor | 28GB | 261 |Rebuilt after NEU-2283, which restored 25 House incumbents ($14.30M). |
| 2000 | 2026-11-14 | `20261113T235513Z` | `1aed283` | 0.05 | 7 | 5 | 301 | 198 (79.45 + 109.11) | 91 | 0.06 | 0.11 | 2.96 | 15.56 GiB, gold donor | 28GB | 268 |Rebuilt after NEU-2287 (MA-03 and PA-14 had no candidates). |
| 2002 | 2026-11-14 | `20261114T174026Z` | `507d381` | 0.04 | 7 | 5 | 268 | 216 (82.43 + 115.81) | 94 | 0.06 | 0.10 | 3.15 | 12.43 GiB, gold check | 28GB | 257 |Rebuilt after NEU-2293 (10 filings moved to their 2002 district). The peak is in load's gold phase. |
| 2004 | 2026-11-15 | `20261115T234428Z` | `1250468` | 0.09 | 7 | 5 | 515 | 228 (90.78 + 120.35) | 94 | 0.11 | 0.19 | 3.37 | 14.98 GiB, gold check gold_top_donor_not_self_funding | 32GB | 262 |Second build, after NEU-2324 (DE and MT at-large filings). |
| 2006 | 2026-11-16 | `20261116T000249Z` | `1250468` | 0.06 | 7 | 5 | 351 | 222 (86.51 + 120.23) | 90 | 0.09 | 0.13 | 3.37 | 13.38 GiB, gold donor | 32GB | 263 |Second build, after NEU-2324 (DE at-large filing). |
| 2008 | 2026-11-14 | `20261114T014209Z` | `c8bec5f` | 0.12 | 34 | 5 | 534 | 203 (79.10 + 114.07) | 91 | 0.16 | 0.25 | 3.08 | 13.23 GiB, gold check gold_top_donor_not_self_funding.sql | 28GB | 266 |The peak is in load's gold phase. |
| 2010 | 2026-11-14 | `20261114T020123Z` | `c8bec5f` | 0.08 | 32 | 8 | 445 | 289 (101.29 + 176.69) | 97 | 0.10 | 0.15 | 3.12 | 14.41 GiB, gold check gold_top_donor_not_self_funding.sql | 28GB | 302 |Load's `COPY` rose to 177 s and free disk to 302 GB: outside fundlens, transient (both back by 2012). |
| 2012 | 2026-11-14 | `20261114T180514Z` | `507d381` | 0.27 | 8 | 5 | 519 | 222 (81.67 + 122.18) | 93 | 0.31 | 0.26 | 3.15 | 13.06 GiB, gold donor | 28GB | 253 |Rebuilt after NEU-2293 (11 filings: NY-11's Grimm and Murphy, CA-38's Sánchez). |
| 2014 | 2026-11-14 | `20261114T182542Z` | `507d381` | 0.17 | 44 | 5 | 334 | 221 (84.09 + 115.38) | 97 | 0.20 | 0.14 | 3.19 | 15.05 GiB, gold check | 28GB | 252 |The peak is in load's gold phase. |
| 2016 | 2026-11-14 | `20261114T184036Z` | `507d381` | 1.49 | 178 | 6 | 972 | 219 (83.72 + 118.12) | 93 | 1.59 | 0.79 | 3.23 | 14.90 GiB, gold donor | 28GB | 249 |Built from `507d381`. `record.py` read `a22a808`: PR #160 (dependencies) had redeployed `pipeline` before the row was recorded. |
| 2018 | 2026-11-16 | `20261116T001733Z` | `1250468` | 1.60 | 7 | 5 | 871 | 220 (85.83 + 120.07) | 90 | 1.65 | 0.65 | 3.37 | 15.24 GiB, gold check gold_top_donor_not_self_funding | 32GB | 263 |Third build: after NEU-2319 (the MN and MS specials) and NEU-2324 (MP at-large). |
| 2020 | 2026-11-15 | `20261115T033259Z` | `2592ae1` | 5.87 | 7 | 6 | 1882 | 216 (83.85 + 119.00) | 91 | 6.13 | 2.07 | 3.29 | 22.54 GiB, write contribution | 32GB | 248 |The first `LARGER` cycle (`indiv` 138% of 2024's); DuckDB raised to 32 GB before it. The first build failed `gold_committee_cycle_refunds` at `load` (NEU-2320). |
| 2022 | 2026-11-15 | `20261115T173437Z` | `529517d` | 3.60 | 8 | 6 | 1403 | 241 (95.85 + 122.45) | 97 | 3.77 | 1.40 | 3.34 | 20.38 GiB, write contribution | 32GB | 241 |The first build failed at transform on FEC's truncated `itcont.txt` (NEU-2321). The CA special is at $0 by design. |
| 2024 | 2026-11-16 | `20261116T005426Z` | `1250468` | 4.23 | 469 | 5 | 1728 | — | — | 4.76 | 2.29 | 3.37 | 26.48 GiB, write contribution | 32GB | 260 |Transform only, rebuilt after NEU-2324; loaded and published with every cycle (Per cycle, 2026-11-17). Its earlier transform-only build `20261115T182139Z` peaked at 28.97 GiB, the backfill's highest. |
| 2026 | 2026-11-16 | `20261116T013416Z` | `1250468` | 2.60 | 7 | 5 | 981 | 223 (87.88 + 121.79) | 91 | 2.83 | 1.36 | 3.37 | 20.36 GiB, write contribution | 32GB | 258 |Resumed at `load` after NEU-2323, then rebuilt after NEU-2324 (MP-00 had no candidates). |

## Resolution

One `fundlens resolve --full` per row (spec §6.3–§6.6): every cycle's contributor keys linked, clustered and
given donor_ids. The phases are the run's own timings, in run order, from its output line `load <s> s, train <s> s, …`; wall time is
the `resolved` marker's `duration_s`. Peak memory is `pipeline`'s between the run's start and end. The working
file is `/data/fundlens/resolution/resolve.duckdb` after the run; from NEU-2122 it also keeps the run's `edge` and
`component` tables, and the Notes give the `recluster` summary line and the cluster cap. From NEU-2325 a run
saves its model right after training, in a `model` phase between `train` and `cluster`; the Notes give its seconds,
and `save` only drops Splink's remaining tables. A run with `--model VERSION` has no `train` or `model` phase.

| Date | Model | Cycles (build) | SHA | Contributor keys | Clusters | Load / train / cluster / recluster / overrides / save / crosswalk / silver s | Wall s | Peak `pipeline` memory | Working file GB | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-01 | `20261101T024736Z` | 2024 (`20261031T202003Z`) | `a4c82b8` | 5,620,495 | 3,816,141 | 10.08 / 190.33 / 111.11 / — / 0.00 / 0.12 / 101.13 / 346.49 | 762 | 24.54 GiB | 9.91 | First `resolve --full` on real keys ([first-resolved-run.md](runbooks/first-resolved-run.md), NEU-2079). Trained (EM converged after 8 iterations), no overrides, DuckDB memory limit 26.0 GiB. The peak came at 02:55:01, early in `silver`, not in Splink. |
| 2026-11-02 | `20261102T194152Z` | 2024 (`20261102T031624Z`) | `22e56ce` | 5,620,495 | 3,822,946 | 10.21 / 188.02 / 106.62 / 11.85 / 0.18 / 0.13 / 18.81 / 253.41 | 598 | — | 9.5 | First run with re-clustering ([refreshing-dime.md](runbooks/refreshing-dime.md) §8, NEU-2122), cap 200. `recluster: 4,085 components (17 oversized, 4,085 inconsistent) into 10,891 pieces; largest 1,400 → 180`. Crosswalk: 6,806 new donors, 31,213 keys re-pointed, 0 redirects; one override merge. Wall time is `time`'s `real`; peak memory not measured. |
| 2026-11-03 | `20261104T012451Z` | 2024 (`20261103T175128Z`) | `a2ca75f` | 5,620,495 | 4,009,899 | 10.01 / 174.71 / 112.62 / 10.98 / 0.19 / 0.15 / 32.82 / 197.31 | — | — | 9.4 | First run with the first-name levels of NEU-2188 (initial pair, nickname pair, the veto blind to initials), cap 200. `recluster: 7,339 components (3 oversized, 7,339 inconsistent) into 18,975 pieces; largest 263 → 103`. Crosswalk: 197,265 new donors, 284,508 keys re-pointed, 10,312 redirects; one override merge. The phases sum to 539 s; wall time and peak memory not captured. |
| 2026-11-16 | `20261116T224205Z` | 1980–2026 (each cycle's live build; 2024 `20261116T005426Z`) | `dbe2ffd` | 29,213,828 | 12,564,451 | 56.18 / 829.52 / 2473.92 / 520.49 / 0.95 / 0.03 / 703.52 / 2459.66 | 7147 | 32.60 GiB | 110 | The first all-cycle run that finished ([backfill.md](runbooks/backfill.md) step 5, NEU-2060), from NEU-2333's sampled EM: each session trained on at most 2e8 pairs (the Log has the three). `model` 0.27 s, `adjudications` 95.96 s (130 verdicts, 4 splits); one override merge. `recluster: 107,324 components (1,190 oversized, 107,267 inconsistent) into 411,206 pieces; largest 89,299 → 200`, 7,073,685 vetoed pairs in the largest. `crosswalk: 8699796 new donors, 133498 keys re-pointed, 59884 redirects`. The peak came in `recluster`, with the process's own peak RSS at 32.31 GiB; DuckDB limit 29.8 GiB; least free disk 128 GB. The working file is 102 GiB by `du`. `real` 119m20s. |

**The first all-cycle run failed (2026-11-16, NEU-2060 step 9, NEU-2325).** It has no row: it resolved nothing.
Model `20261116T022944Z` from `62a47eb`, all 24 cycles (1980–2026), 29,213,828 contributor keys, DuckDB limit 32 GB.
Load took 54 s, train 8,420 s (EM converged after 8, 7 and 12 iterations) and cluster 2,499 s; the run failed in
`recluster` after 3h22m with `IOException: Could not write file "/data/fundlens/scratch/duckdb_temp_…tmp": No space
left on device`. The working file was 254,181,650,432 bytes, nearly all of it Splink scratch the run never read
again, which `resolve_full` then dropped only in `save`, after `recluster`, `overrides` and `adjudications`:

- the three EM sessions' `__splink__blocked_id_pairs_*` and `__splink__df_comparison_vectors_*` tables, of
  2,636,580,964 (soundex + ZIP3), 621,859,329 and 55,991,435 pairs;
- `__splink__df_predict_*`, 112,392,100 rows, a copy of `edge`;
- `__splink__df_clustered_with_input_data_*`, 29,213,828 rows of 18 columns, a copy of `component`.

Free disk on `/` went 266 → 202 → 78 → 128 → 58 → 14 → 3 → 1 GB, DuckDB's spill under `scratch/` taking the last
of it. `pipeline` read 40.00 GiB, its `mem_limit`, at 05:35:53Z, three minutes into `recluster`, by `docker stats`;
it was not killed. **What held that memory is not established**: `docker stats` counts active page cache, and a
process at the limit and not killed while writing a 254 GB file fits reclaimable cache as well as Python's
components or DuckDB's buffer pool. The failed run's working file was deleted at 14:45Z.

NEU-2325 drops each EM session's tables when the session ends and the predictions once `edge` and `component` hold
them, saves the model right after training (so `resolve --full --model 20261116T022944Z` would skip the 2h20m of
training), and makes `recluster` read the offending components a batch at a time, logging their size and its peak
memory. The working file still reaches about the largest EM session's size, since DuckDB never shrinks a file. Step
9's rerun gives the first all-cycle row.

**The rerun stopped in `train` (2026-11-16, NEU-2060 step 9, NEU-2333).** It has no row: it saved no model. From
`1e274e3` (NEU-2325), DuckDB limit 32 GB, started at about 16:09Z with 264 GB free, a guard set to restart `pipeline`
under 60 GB free. Blocking the soundex + ZIP3 session's pairs took free disk from 264 to 121 GB in 40 minutes. The
session's working file was 108 GB, and each EM iteration, about 15 minutes, spilled another 65–80 GB into
`scratch/`, released when the iteration ended. Free disk bottomed at 65–70 GB in iterations 1–7 and reached 59 GB
in iteration 8, when the guard restarted `pipeline` at 18:42:51Z, after 2h33m. The largest parameter change was
0.000332 at iteration 7, so the session was close to converging. One EM session over every cycle's 2.6 billion
pairs holds about 190 GB at its peak, working file and spill together, and with the run's other tables that took
free disk from 264 GB to 59 GB, under the 60 GB floor. Splink sampled nothing:
`[EM sampling] max_pairs is None — no sampling will be applied`. NEU-2333 caps each session at
`RESOLVE_EM_MAX_PAIRS` (2e8) pairs; scaled from 108 GB for 2.6 billion, about an 8 GB working file and a few GB of
spill per iteration (an estimate, not a measurement). Step 9's next rerun measures it.

**The second rerun finished (2026-11-16, NEU-2060 step 9).** From `dbe2ffd` (NEU-2333): the row above. Each sampled
session blocked its pairs in about a minute and ran an EM iteration in about 21 s, against 40 minutes and 15
minutes unsampled, so `train` took 829.52 s against 8,420 s. The working file still ended at 102 GiB, not the
estimate's 8 GB, which covered only training. Most likely `cluster`'s predictions grew it, since they score every
blocked pair unsampled and DuckDB never shrinks the file; the file was not measured by phase. Free disk's
low over the whole run was 128 GB, 68 GB above the floor.

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
| 2026-11-17 | `20261116T224205Z` | 2024 (`20261116T005426Z`) | v4.0 | 30,148,695 of 50,104,322 (60.2%) | 0.8122 (0.9834) | 0.8993 (0.7591) | 221 | From `dbe2ffd`: the first model over every cycle (NEU-2060 step 5.3); the live figures. 2,012,327 correct, 2,477,510 predicted, 2,237,707 true pairs overall; top 10,000: 327,213 correct, 332,728 predicted, 431,033 true. Against the 2024-only model `20261112T214620Z` live before it: precision −0.0121, recall −0.0083, top precision +0.0072, top recall −0.0283 (Findings). |

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
- **Pairs grow much faster than keys (NEU-2325).** 2024's 5.6M keys made a working file of 9.4–9.9 GB; every
  cycle's 29.2M keys, 5.2 times as many, made 254 GB, 26 times as large, before `recluster` had written anything.
  Blocking on a soundex and a ZIP3 pairs every key with every other in its block, so the pairs grow with the square
  of the busiest blocks, and an estimate of the working file, or of training time, scaled by key count is wrong by
  a wide margin.
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
- **Before resolution, a cycle's load was gold over every live cycle, and its peak was `gold donor` (backfill,
  NEU-2060).** Load ran 192–241 s (289 s at 2010), growing with the cycles before it, and the peak (12–17 GiB) was in load's
  gold phase, not the cycle's own transform, until 2020. From 2020 the cycle's own `write contribution` led: 22.54
  GiB for 2020's 5.87 GB `indiv`, 26.48 GiB for 2024's under `32GB`. 2024's earlier build under `32GB` peaked at
  28.97 GiB against 24.34 GiB under `28GB`: DuckDB holds more before it spills, so the peak follows the limit, not
  only the data. 28.97 GiB is the backfill's highest transform, about 11 GiB under the 40 GiB `mem_limit`.
- **Unmatched filings jumped to 37 in 1984 and 28 in 1992,** against 3–13 in other cycles.
- **The Backfill rows' gold column is all of gold after that cycle's publish,** so it grows with the cycles before
  it; the rows for 1984–1992 were recorded after 1992's load and overstate their own gold.
- **Seats needed five fixes before every cycle's races held their candidates.** Each was found by a race at $0 or
  by `app.unmatched_filing`, and each meant rebuilding the cycles it touched:
  - 1998's races were missing 25 House incumbents ($14.30M) whose `cn` row carried the next election's year
    (NEU-2283; 1980–1998 rebuilt). Senate later-year filings, about 60 incumbents a cycle, are senators whose seat
    isn't up, and correctly have no race.
  - Census-year cycles keep the old district in `cn` (15 of 15 checked), so 1980 (4 races at $0), 1990 (2), 2000
    (3) and 1982 (Gramm, TX-06) still missed incumbents (NEU-2287; those four rebuilt).
  - In the first cycle on a new map, `cn` keeps some House candidates under their old district. NEU-2293 corrected
    10 filings in 2002 ($476,509 of receipts), 11 in 2012 ($5,969,717) and 47 in 2022 ($24,917,356) from FEC's
    election results, and NEU-2294 3 in 1992 from its PDF results; 1982 needed none
    ([house-districts-redistricting.md](measurements/house-districts-redistricting.md)). 2012's misplacement was
    not a $0 race, so the $0 check alone would have missed it.
  - A Senate special beside a regular race had no candidates: 54 filings and $275,395,869 stood in the regular race
    (NEU-2319, [senate-specials-beside-regular-races.md](measurements/senate-specials-beside-regular-races.md)).
    NEU-2319 measured the seven specials in `specials.csv`, 2018–2024; specials before 2018 are not in it and were
    not measured.
  - A state with one House seat has its race at `00`, but `cn` files some candidates under `01`: 8 filings in 2004,
    2006, 2018, 2024 and 2026 (NEU-2324). The $0 check caught only 2026's MP-00.
- **Four failures came from FEC's data.** 1994's `cm` holds a NUL byte
  (NEU-2282). 2020's hybrid PAC C00603084 moved a refund between its accounts (`22Y` −12,500, `20Y` +12,500),
  which silver counted as a void (NEU-2320); every other cycle passed `gold_committee_cycle_refunds`, so a
  cross-type pair there nets to 0 or less, but no other cycle was searched. FEC's `indiv22.zip` (regenerated 08 Nov
  2026) held an `itcont.txt` cut at 4,471,783,424 bytes, 37% of its own `by_date/` members (NEU-2321). Every other
  cycle's matches byte for byte, or has no `by_date/`. 2026's `cn` held a skeleton candidate row with no name
  (NEU-2323).
- **Sampling EM changed training time, not the model (NEU-2333).** On 7.6% of the soundex + ZIP3 session's 2.63
  billion pairs, EM's largest change per iteration ran 0.414, 0.0747, 0.0969, 0.0365, 0.00816, 0.00167, 0.000337,
  against 0.414, 0.0753, 0.0971, 0.0364, 0.0081, 0.00166, 0.000332 unsampled. `train` took 14 minutes, against
  2h20m.
- **Resolving every cycle at once moved 2024's scores the wrong way for recall.** Against the 2024-only model,
  precision fell 0.8243 → 0.8122, within the runbook's 0.02 gate, but recall fell too (0.9076 → 0.8993), most in
  the top 10,000 (0.7874 → 0.7591). The runbook expected cross-cycle keys to raise recall. The run differs in
  several ways: the recluster at this scale (largest component 89,299 keys and 411,206 pieces, against 263 keys and 18,975 pieces in
  the 2026-11-03 2024-only run), the EM sample, 2024's rebuilt silver and 4 adjudication splits. Which one moved recall is not measured.
  One donor to check against DIME: `1901884`, LOEB, JOHN, gives in all 24 cycles, 1980–2026. That could be one
  person over 46 years, or a cross-cycle chain.
- **Donors for every cycle triple the database and make load the longest step after resolution.** The database
  went from 7.6 GB to 23.11 GB, and load from 192–241 s per cycle to 1,402 s, about 6 minutes of it `gold donor`.
- **The working file stays between runs.** `resolve.duckdb`, 102 GiB, is about 70% of the steady-state disk
  (Triggers). Every weekly `resolve --full` starts from it until NEU-2062.

## Dataset snapshot

One row per full `fundlens dataset --snapshot` (spec §9), timed by hand or on a Sunday (NEU-2067). The snapshot
pass hashes the live build's silver files and copies them from `fundlens-data` into `v1/<date>/`; the latest pass
copies that directory into `v1/latest/`. Each pass's seconds are from its log line (`hashed and copied <n>
objects …`, `copied <n> objects to v1/latest/ …`); wall time is `time`'s `real`, documentation, donor export and
retention included.

| Date | Build | SHA | Workers | Objects | Snapshot pass s | Latest pass s | Wall time | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-17 | `20261117T030329Z` | `ff1cff3` | 1 | 6,340 | ~6,300 (1h45m) | ~6,960 (1h56m) | 221m18s (3h41m) | The first production snapshot, all 24 cycles, copied one object at a time (NEU-2064). The passes are from its timestamps, not log lines, which it did not write. About 1.1 s a copy. 6,338 Parquet files (6,144 `contribution` parts), `overrides.yaml` and the manifest. The baseline [dataset-launch.md](runbooks/dataset-launch.md) §2 re-times against: 30 minutes or less. |
| 2026-11-18 | `20261117T030329Z` | `6bd0db0` | 16 | 6,336 + 6,340 | 363 | 495 | 16m26.675s | The re-time ([dataset-launch.md](runbooks/dataset-launch.md) §2, NEU-2067), by hand: 13.5 times faster than the baseline, inside the 30-minute target first try. Objects are the two passes' log counts. Same build and rows as the baseline. The 128 s outside the passes are the docs check, `gold.donor`'s export, the crosswalk copy and retention. |

## Triggers

The handover's triggers for moving the pipeline to an ephemeral runner (spec §10.6, §13): a weekly run over 6–8 h,
or steady-state disk over ~300 GB. Checked after the backfill (NEU-2060), from the rows above.

| Trigger | Measured | Against | Fired |
| --- | --- | --- | --- |
| Weekly run | 9,699 s, 2h42m: 2026's extract, seats and transform (7 + 5 + 981 s, its Backfill row), plus `resolve --full` over every cycle (7,147 s, Resolution), plus the load and publish of every cycle (1,402 + 157 s, Per cycle). With a first-download extract (2024's 469 s), 2h49m | 6–8 h | No |
| Steady-state disk | 152.6 GB: `/data/fundlens` 129.5 GB (126,422,360 KB, of it `resolve.duckdb` 102 GiB, silver 17 GiB, bronze 2.7 GiB) plus the database's 23.11 GB, on 2026-11-17. ClickHouse, beside it on the same disk, is 4.6 GiB | ~300 GB | No |
| Memory (not a handover trigger) | 32.60 GiB in `resolve --full`'s `recluster`; the largest transform 28.97 GiB (2024, `write contribution`) | 40 GiB `mem_limit` | — |

**Verdict: no trigger fired, so no ticket was filed.** Resolution is three quarters of the weekly run. Once
NEU-2062 makes it incremental, the 2026 steps, extract to publish, take about 43 minutes plus that incremental resolve. Memory has 7.4 GiB
of headroom at resolution's peak, with DuckDB at `32GB` (the compose fallback since PR #173). Resolution's
transient disk is the tighter margin: free disk's low during the run was 128 GB, from 256 GB at its start.
