-- committee's key (cycle, committee_id) is never null and never repeated.
SELECT cycle, committee_id, count(*) AS copies
FROM committee
GROUP BY cycle, committee_id
HAVING committee_id IS NULL OR count(*) > 1;
