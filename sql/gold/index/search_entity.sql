-- `GET /v1/search` is a trigram match on name (spec §7.1). pg_trgm is created by the loader in
-- the default schema, never in gold_build, which the next publish drops.
CREATE INDEX search_entity_name_trgm ON gold_build.search_entity USING gin (name gin_trgm_ops);
