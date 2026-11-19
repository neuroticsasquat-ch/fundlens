-- candidate_reported_total's key (cycle, candidate_id) is never null and never repeated
-- (every-FEC-dollar spec §4.2): one row per candidate per cycle.
SELECT cycle, candidate_id, count(*) AS copies
FROM candidate_reported_total
GROUP BY cycle, candidate_id
HAVING candidate_id IS NULL OR count(*) > 1;
