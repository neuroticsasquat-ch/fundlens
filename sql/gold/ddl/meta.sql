-- The one row describing the build (spec §7.1). published_at is NULL in gold_build and set by the
-- publish swap. resolver_version and model_version are NULL until M3. precision and recall (the
-- overall scope), precision_top and recall_top (the top donors by matched dollars), matched_rows
-- and dime_version are NULL until the cycle is validated under the live model (NEU-2054). cycles
-- is {"<cycle>": {"build_id": "<build>", "source_dates": {"<file>": "YYYY-MM-DD", …}}}.
CREATE TABLE gold_build.meta (
    build_id text PRIMARY KEY,
    published_at timestamptz,
    resolver_version text,
    model_version text,
    precision numeric,
    recall numeric,
    precision_top numeric,
    recall_top numeric,
    matched_rows bigint,
    dime_version text,
    cycles jsonb NOT NULL
);
