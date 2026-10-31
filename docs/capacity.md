# Capacity record

What the pipeline costs on `music-box-dancer` (spec §10.6): time per step and the disk it fills, per
cycle. At the end of v1 these figures are checked against the handover's triggers for moving to an
ephemeral runner: a weekly run over 6–8 h, or steady-state disk over ~300 GB. Each measured run gets a
row, filled in once from its runbook's figures and never changed after that. A run that measures again
gets a new row. The 2024 row is blank until [first-run.md](runbooks/first-run.md) has been run.

Step times are each step's `duration_s` from its R2 marker (`markers/cycle=<c>/build=<b>/<step>.json`).
`seats` writes no marker, so its time is `time`'s `real`. Sizes are decimal GB. Bronze is the cycle's
zips in R2, silver is the cycle's build under `/data/fundlens/silver`, and gold is the `gold` schema's
tables with their indexes and TOAST.

## Per cycle

Load is the DuckDB → CSV → `COPY` method of ADR-0007, written `<total> (<aggregates> + <copy>)`: the whole
step, then its two halves (DuckDB aggregates and CSV, then `COPY`, indexes and `ANALYZE`).

| Cycle | Date | Build | SHA | Extract s | Seats s | Transform s | Load s | Publish s | Bronze GB | Silver GB | Gold GB | Peak `pipeline` memory | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | | | | | | | ( + ) | | | | | | First run: committee-level gold, no resolution ([first-run.md](runbooks/first-run.md), NEU-2046) |

Resolution (M3), the backfill (NEU-2060) and the weekly run (M5) add their own figures here.
