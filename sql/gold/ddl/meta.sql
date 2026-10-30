-- The one row describing the build (spec §7.1). published_at is NULL in gold_build and set by the
-- publish swap. resolver_version, model_version, precision and recall are NULL until M3. cycles is
-- {"<cycle>": {"build_id": "<build>", "source_dates": {"<file>": "YYYY-MM-DD", …}}}.
CREATE TABLE gold_build.meta (
    build_id text PRIMARY KEY,
    published_at timestamptz,
    resolver_version text,
    model_version text,
    precision numeric,
    recall numeric,
    cycles jsonb NOT NULL
);
