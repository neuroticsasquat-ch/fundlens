---
status: accepted
---

# Gold is computed by DuckDB over silver, written as CSV, and loaded into Postgres with `COPY`

The project spec (§5.5, §13) left open whether gold tables reach Postgres through DuckDB's `postgres` extension writing into an attached database, or through files that Postgres `COPY`s. Decided while planning NEU-2039 (2026-10-30), ahead of the real-cycle measurement the spec asked for: that measurement needs a published 2024, which needs this code first. The fixture timing lives in the NEU-2039 spec; the real-cycle timing is the `load seconds` column NEU-2046 records in `docs/capacity.md`.

`fundlens load` runs `sql/gold/*.sql` in DuckDB over the cycle's silver partitions, writes each gold table as a CSV file under `scratch/`, and streams it into `gold_build` with psycopg's `COPY … FROM STDIN (FORMAT csv, HEADER true)`; explicit Postgres DDL (`sql/gold/ddl/`) and index files (`sql/gold/index/`) pin the served types and indexes by hand.

## Why

- `COPY` is Postgres' fastest ingest path and needs nothing beyond psycopg, which the pipeline already has.
- The `postgres` extension would have to be baked into the image: the tests run with no network and DuckDB fetches extensions on first use. Its write path (`INSERT INTO pg.schema.table SELECT …`) is also less tunable than a `COPY` whose DDL, indexes and `ANALYZE` the loader controls.
- Building both behind a setting, to measure in prod, was rejected as twice the code for a one-time number.

## Consequences

- Gold SQL is DuckDB SQL; the DDL is Postgres SQL. A served column's type changes only when someone edits `ddl/`, never because a silver column's type drifted.
- Postgres literals that DuckDB does not write natively are produced in the SQL: arrays go through the `pg_array` macro the loader registers (`{…}` rather than DuckDB's `[…]`); `jsonb` (`meta.cycles`) is inserted from Python.
- Scratch holds one CSV per gold table for the duration of a load; the loader removes its work directory afterwards.
- If M3's donor tables make CSV `COPY` the bottleneck, the next step is `COPY … (FORMAT binary)` or indexes built after the copy, measured against the numbers in the NEU-2039 spec, not a third engine.
