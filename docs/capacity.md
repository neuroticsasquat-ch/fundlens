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

Resolution (M3), the backfill (NEU-2060) and the weekly run (M5) add their own figures here.

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
