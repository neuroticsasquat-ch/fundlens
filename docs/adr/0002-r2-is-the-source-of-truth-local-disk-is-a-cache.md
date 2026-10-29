---
status: accepted
---

# R2 is the pipeline's source of truth; local NVMe is a cache

Every pipeline step reads its inputs from Cloudflare R2 and writes its outputs back to R2; the Robot box's disk only caches what the current run needs. This holds from the first ticket even though v1 runs entirely on the Robot box, so the weekly rebuild can later move to an hourly Hetzner Cloud instance (the preferred alternative to migrating the box) with no code change, and so old cycles can be dropped locally when disk gets tight. Historical raw zips are never kept locally. R2 was chosen over the Storage Box because the public dataset needs zero-egress hosting and DuckDB reads Parquet from R2 over httpfs; the Storage Box keeps its existing role as the pg_dump target.

## Consequences

- Idempotency is "does the silver partition exist in R2", never "is the zip on disk".
- Crosswalk and overrides are the only non-reproducible data and get real backup discipline (Postgres dump to the Storage Box).
