-- candidate_redirect (spec §7.1, NEU-2127): each candidate alias, a person's second id for the
-- same race, and the id holding their money that it is an alias of. The API answers an alias's
-- candidate page with a 301 to that id, as `donor_redirect` does for a merged donor.
CREATE TABLE candidate_redirect AS
SELECT candidate_id AS old_candidate_id, alias_of AS candidate_id
FROM silver.candidate
WHERE alias_of IS NOT NULL;
