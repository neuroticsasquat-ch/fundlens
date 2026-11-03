-- A candidate alias and the id it is an alias of (NEU-2127, silver candidate.alias_of):
-- `GET /v1/candidates/{id}` answers an alias with a 301. Every redirect resolves in one hop.
CREATE TABLE gold_build.candidate_redirect (
    old_candidate_id text PRIMARY KEY,
    candidate_id text NOT NULL
);
