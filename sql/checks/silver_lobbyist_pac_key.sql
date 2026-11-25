-- lobbyist_pac's key (cycle, committee_id) is never null and never repeated (NEU-2175): rule b
-- reads one Form 1 per committee, its latest by the cycle's last day.
SELECT cycle, committee_id, count(*) AS copies
FROM lobbyist_pac
GROUP BY cycle, committee_id
HAVING committee_id IS NULL OR count(*) > 1;
