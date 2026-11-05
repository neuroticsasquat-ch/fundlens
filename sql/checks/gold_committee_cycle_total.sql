-- Every counted contribution went to a committee of the cycle (a silver check), so the
-- committees' receipts, own money included, add up to cycle.total_amount; every organization
-- receipt did too, so their total_from_organizations add up to silver's organization money, which
-- is in no cycle figure (ADR-0011).
SELECT 'total_individual + self_funding' AS figure, committees.total, cycle.total_amount AS expected
FROM (SELECT coalesce(sum(total_individual + self_funding), 0) AS total FROM committee_cycle) AS committees,
    cycle
WHERE committees.total <> cycle.total_amount
UNION ALL
SELECT 'total_from_organizations', committees.total, organizations.total
FROM (SELECT coalesce(sum(total_from_organizations), 0) AS total FROM committee_cycle) AS committees,
    (SELECT coalesce(sum(amount), 0) AS total FROM silver.organization_receipt) AS organizations
WHERE committees.total <> organizations.total;
