-- A build is one cycle (NEU-2059 merges builds), so cycle has exactly one row.
SELECT count(*) AS rows
FROM cycle
HAVING count(*) <> 1;
