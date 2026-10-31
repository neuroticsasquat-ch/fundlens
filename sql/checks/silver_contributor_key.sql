-- contributor's key is never null and never repeated, and every contribution's contributor key has
-- its contributor row.
SELECT contributor_key, count(*) AS copies
FROM contributor
GROUP BY contributor_key
HAVING contributor_key IS NULL OR count(*) > 1
UNION ALL
SELECT DISTINCT contribution.contributor_key, 0
FROM contribution
ANTI JOIN contributor USING (contributor_key);
