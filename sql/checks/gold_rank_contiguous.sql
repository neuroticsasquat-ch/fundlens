-- Ranks run 1..n without a gap or a tie in every top-N group.
SELECT 'race_top_committee' AS "table", race_id AS group_id, count(*) AS rows, min(rank) AS first, max(rank) AS last
FROM race_top_committee
GROUP BY race_id
HAVING min(rank) <> 1 OR max(rank) <> count(*) OR count(DISTINCT rank) <> count(*)
UNION ALL
SELECT 'committee_top_recipient', committee_id || '/' || cycle, count(*), min(rank), max(rank)
FROM committee_top_recipient
GROUP BY committee_id, cycle
HAVING min(rank) <> 1 OR max(rank) <> count(*) OR count(DISTINCT rank) <> count(*);
