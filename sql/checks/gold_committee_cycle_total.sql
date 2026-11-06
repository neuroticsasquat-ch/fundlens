-- Every counted contribution went to a committee of the cycle (a silver check), so the
-- committees' receipts, own money included, add up to cycle.total_amount; every organization
-- receipt did too, so their total_from_organizations add up to silver's organization money, which
-- is in no cycle figure (ADR-0011). A hybrid PAC's non-contribution account (NEU-2192) is in
-- total_non_contribution_account and in neither of the other two, and money on a line no
-- total_individual counts (NEU-2193) is in total_other_lines alone, so the four add up together.
SELECT 'total_individual + self_funding + total_non_contribution_account + total_other_lines'
        AS figure,
    committees.total, cycle.total_amount + organizations.non_contribution_account AS expected
FROM (
        SELECT coalesce(
                sum(
                    total_individual + self_funding + total_non_contribution_account
                        + total_other_lines
                ),
                0
            ) AS total
        FROM committee_cycle
    ) AS committees,
    (
        SELECT coalesce(sum(amount) FILTER (WHERE is_non_contribution_account), 0)
            AS non_contribution_account
        FROM silver.organization_receipt
    ) AS organizations,
    cycle
WHERE committees.total <> cycle.total_amount + organizations.non_contribution_account
UNION ALL
SELECT 'total_from_organizations', committees.total, organizations.total
FROM (SELECT coalesce(sum(total_from_organizations), 0) AS total FROM committee_cycle) AS committees,
    (
        SELECT coalesce(sum(amount) FILTER (WHERE NOT is_non_contribution_account), 0) AS total
        FROM silver.organization_receipt
    ) AS organizations
WHERE committees.total <> organizations.total;
