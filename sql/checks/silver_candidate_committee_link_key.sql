-- candidate_committee_link's key (cycle, candidate_id, committee_id) is never null and never
-- repeated.
SELECT cycle, candidate_id, committee_id, count(*) AS copies
FROM candidate_committee_link
GROUP BY cycle, candidate_id, committee_id
HAVING candidate_id IS NULL OR committee_id IS NULL OR count(*) > 1;
