-- A committee's spending-category rows add up to its total_operating_expenditures (every-FEC-dollar
-- spec §5.5): each counted operating expenditure in one category, a category netting to $0 or less
-- kept. A committee with no counted row has a NULL total and no rows; one with rows has a total.
SELECT
    committee_id,
    cycle,
    committee_cycle.total_operating_expenditures,
    categories.amount
FROM committee_cycle
FULL JOIN (
    SELECT committee_id, cycle, sum(amount) AS amount
    FROM committee_spending_category
    GROUP BY committee_id, cycle
) AS categories USING (committee_id, cycle)
WHERE committee_cycle.total_operating_expenditures IS DISTINCT FROM categories.amount;
