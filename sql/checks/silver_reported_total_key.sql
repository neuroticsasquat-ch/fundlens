-- reported_total's key (cycle, committee_id) is never null and never repeated (every-FEC-dollar
-- spec §4.1): one row per committee per cycle.
SELECT cycle, committee_id, count(*) AS copies
FROM reported_total
GROUP BY cycle, committee_id
HAVING committee_id IS NULL OR count(*) > 1;
