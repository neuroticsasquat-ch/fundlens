-- A race's six outside-spending columns add up to its outside_spending_total, and so do a
-- committee's four totals to its own, a NULL electioneering figure as 0 (every-FEC-dollar spec
-- §6.5). Neither total is ever NULL.
SELECT
    'race' AS "table",
    race_id AS id,
    outside_spending_total,
    ie_support + ie_oppose + communication_cost_support + communication_cost_oppose
        + party_coordinated + coalesce(electioneering, 0) AS kinds
FROM race
WHERE outside_spending_total IS DISTINCT FROM ie_support + ie_oppose + communication_cost_support
    + communication_cost_oppose + party_coordinated + coalesce(electioneering, 0)
UNION ALL
SELECT
    'committee_cycle',
    committee_id || '/' || cycle,
    outside_spending_total,
    ie_total + communication_cost_total + party_coordinated_total
        + coalesce(electioneering_total, 0)
FROM committee_cycle
WHERE outside_spending_total IS DISTINCT FROM ie_total + communication_cost_total
    + party_coordinated_total + coalesce(electioneering_total, 0);
