-- `GET /v1/search` is a trigram match on name or aliases (spec §7.1): one GIN index each, so the
-- OR is a BitmapOr of two index scans. pg_trgm is created by the loader in the default schema,
-- never in gold_build, which the next publish drops.
CREATE INDEX search_entity_name_trgm ON gold_build.search_entity USING gin (name gin_trgm_ops);
CREATE INDEX search_entity_aliases_trgm ON gold_build.search_entity USING gin (aliases gin_trgm_ops);
