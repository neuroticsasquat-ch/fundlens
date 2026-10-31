-- candidate's key (cycle, candidate_id) is never null and never repeated.
SELECT cycle, candidate_id, count(*) AS copies
FROM candidate
GROUP BY cycle, candidate_id
HAVING candidate_id IS NULL OR count(*) > 1;
