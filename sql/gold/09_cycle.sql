-- cycle (spec §7.1): one row per cycle gold holds (NEU-2059), each cycle of the seat calendar the
-- build read. total_amount is every counted contribution of the cycle, self-funding included
-- (expected.yaml's contributions.total_amount).
CREATE TABLE cycle AS
WITH races AS (
    SELECT cycle, count(*) AS race_count
    FROM race
    GROUP BY cycle
),
contributions AS (
    SELECT cycle, count(*) AS contribution_count, sum(amount) AS total_amount
    FROM silver.contribution
    GROUP BY cycle
)
SELECT
    CAST(cycles.cycle AS INTEGER) AS cycle,
    CAST(coalesce(races.race_count, 0) AS INTEGER) AS race_count,
    CAST(coalesce(contributions.contribution_count, 0) AS BIGINT) AS contribution_count,
    CAST(coalesce(contributions.total_amount, 0) AS DECIMAL(16, 2)) AS total_amount
FROM (SELECT DISTINCT cycle FROM silver.race) AS cycles
LEFT JOIN races USING (cycle)
LEFT JOIN contributions USING (cycle);
