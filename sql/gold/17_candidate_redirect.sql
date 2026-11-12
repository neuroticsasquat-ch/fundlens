-- candidate_redirect (spec §7.1, NEU-2127): each candidate alias, a person's second id for the
-- same race, and the id holding their money that it is an alias of. The API answers an alias's
-- candidate page with a 301 to that id, as `donor_redirect` does for a merged donor.
--
-- Across cycles (NEU-2059): an id that is a candidate of its own in any cycle has a page and no
-- redirect, and an id that is an alias in several cycles leads to its newest cycle's.
CREATE TABLE candidate_redirect AS
SELECT candidate_id AS old_candidate_id, alias_of AS candidate_id
FROM silver.candidate
WHERE alias_of IS NOT NULL
    AND candidate_id NOT IN (SELECT candidate_id FROM candidate)
QUALIFY row_number() OVER (PARTITION BY candidate_id ORDER BY cycle DESC) = 1;
