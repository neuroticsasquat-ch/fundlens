-- Every counted contribution went to a committee of its cycle (a silver check), so each cycle's
-- committees' receipts, own money included, add up to its cycle.total_amount; every organization
-- receipt did too, so their total_from_organizations add up to the cycle's silver organization
-- money, which is in no cycle figure (ADR-0011). A hybrid PAC's non-contribution account
-- (NEU-2192) is in total_non_contribution_account and in neither of the other two, and money on a
-- line no total_individual counts (NEU-2193, NEU-2205) is in total_other_lines alone, so the four
-- add up together: to cycle.total_amount and the organization money in the last two.
WITH committees AS (
    SELECT
        cycle,
        sum(
            total_individual + self_funding + total_non_contribution_account + total_other_lines
        ) AS total,
        sum(total_from_organizations) AS from_organizations
    FROM committee_cycle
    GROUP BY cycle
),
organizations AS (
    SELECT
        cycle,
        sum(amount) FILTER (WHERE is_non_contribution_account OR is_other_line) AS elsewhere,
        sum(amount) FILTER (WHERE NOT is_non_contribution_account AND NOT is_other_line)
            AS counted
    FROM silver.organization_receipt
    GROUP BY cycle
)
SELECT
    cycle.cycle,
    'total_individual + self_funding + total_non_contribution_account + total_other_lines'
        AS figure,
    coalesce(committees.total, 0) AS total,
    cycle.total_amount + coalesce(organizations.elsewhere, 0) AS expected
FROM cycle
LEFT JOIN committees USING (cycle)
LEFT JOIN organizations USING (cycle)
WHERE coalesce(committees.total, 0) <> cycle.total_amount + coalesce(organizations.elsewhere, 0)
UNION ALL
SELECT
    cycle.cycle,
    'total_from_organizations',
    coalesce(committees.from_organizations, 0),
    coalesce(organizations.counted, 0)
FROM cycle
LEFT JOIN committees USING (cycle)
LEFT JOIN organizations USING (cycle)
WHERE coalesce(committees.from_organizations, 0) <> coalesce(organizations.counted, 0);
