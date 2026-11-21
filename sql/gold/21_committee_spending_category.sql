-- committee_spending_category (every-FEC-dollar spec §5.3, §5.5): a committee's counted operating
-- expenditures by spending category, net as filed, in-kind outlays included. A category with no
-- counted row has no row; one netting to $0 or less is kept, so a committee's rows add up to its
-- committee_cycle.total_operating_expenditures (gold_committee_spending_category_total.sql), and a
-- committee with no counted row has none. A narrow table, not a column per category: the list
-- can grow without a migration.
--
-- A row from a build transformed before the classifier (NEU-2153) has no spending_category
-- (§5.8): `other`, which holds anything no rule names, so the rows still add up.
CREATE TABLE committee_spending_category AS
SELECT
    committee_id,
    CAST(cycle AS INTEGER) AS cycle,
    coalesce(spending_category, 'other') AS category,
    CAST(sum(amount) AS DECIMAL(16, 2)) AS amount
FROM silver.operating_expenditure
WHERE counted
GROUP BY ALL;
