-- A committee's bundled_total is its silver bundling_report rows' amount added (every-FEC-dollar
-- spec §7.6, §7.7): 0 where it has none in a cycle whose build holds the table (`silver_held`)
-- from 2010, and NULL in every other cycle, which then has no rows of the table. A recipient with
-- no committee_cycle row fails too.
WITH bundled AS (
    SELECT cycle, committee_id, sum(amount) AS amount
    FROM silver.bundling_report
    GROUP BY cycle, committee_id
),
held AS (
    SELECT DISTINCT cycle, true AS is_held
    FROM silver_held
    WHERE silver_table = 'bundling_report' AND cycle >= 2010
)
SELECT
    committee_id,
    cycle,
    committee_cycle.bundled_total,
    bundled.amount AS silver_amount
FROM committee_cycle
FULL JOIN bundled USING (cycle, committee_id)
LEFT JOIN held USING (cycle)
WHERE committee_cycle.bundled_total IS DISTINCT FROM CASE
        WHEN held.is_held THEN coalesce(bundled.amount, 0)
    END
    OR (held.is_held IS NULL AND bundled.amount IS NOT NULL);
