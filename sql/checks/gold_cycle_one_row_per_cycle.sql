-- Gold holds every cycle the build read (NEU-2059): cycle has exactly one row per cycle of the
-- seat calendar, and no other.
SELECT coalesce(silver.cycle, gold.cycle) AS cycle, count(gold.cycle) AS rows
FROM (SELECT DISTINCT cycle FROM silver.race) AS silver
FULL JOIN cycle AS gold USING (cycle)
GROUP BY ALL
HAVING count(gold.cycle) <> 1 OR bool_or(silver.cycle IS NULL);
