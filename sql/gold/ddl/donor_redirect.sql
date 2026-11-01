-- A merged-away donor_id and the id it now is (spec §6.6), copied from app.donor_redirect by the
-- loader: `GET /v1/donors/{id}` answers an old id with a 301. Every redirect resolves in one hop.
CREATE TABLE gold_build.donor_redirect (
    old_donor_id bigint PRIMARY KEY,
    donor_id bigint NOT NULL
);
