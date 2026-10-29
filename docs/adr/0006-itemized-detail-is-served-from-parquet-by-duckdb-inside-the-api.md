---
status: accepted
---

# Itemized contribution detail is served from silver Parquet by in-process DuckDB; only aggregates live in Postgres

Loading the itemized contribution table into Postgres would cost roughly 90 GB on a 293 GB disk and make the weekly load and schema swap several times heavier, for pages that Cloudflare caches for a week anyway. The API container therefore runs two engines: Postgres for every gold lookup and search, and DuckDB (a library, not a service) reading a single silver partition over a read-only volume for "what did this donor / committee actually give or receive". Silver is bucketed by cycle and by `donor_id` hash so that scan touches one file. The rule "no on-request aggregation" still holds: these are row lists, not sums.

## Consequences

- The `api` and `pipeline` services share the silver volume (read-only for `api`); a publish must write new partitions atomically (write to a temp name, rename) so a request never reads a half-written file.
- If the two-engine API ever becomes the maintenance burden, the fallback is a partitioned Postgres table, not a third engine.
