-- leadership_pac's key (cycle, committee_id) is never null and never repeated (NEU-2175): FEC's
-- leadership file lists each leadership PAC once (no cycle 2010-2026 has a committee on two rows,
-- Q12a), and a second row would give one PAC two sponsors.
SELECT cycle, committee_id, count(*) AS copies
FROM leadership_pac
GROUP BY cycle, committee_id
HAVING committee_id IS NULL OR count(*) > 1;
