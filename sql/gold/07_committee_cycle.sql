-- committee_cycle (spec §7.1, NEU-2039 §3): one row per committee of the cycle.
--
-- total_individual and self_funding are the counted contributions it received, the candidate's own
-- money kept apart (a candidate committee's receipts would otherwise hide or include it).
-- total_from_committees is the receipt side of committee_transfer (what it recorded receiving);
-- total_to_candidates the disbursement side credited to a candidate (what it recorded giving; a 24K
-- whose recipient raises for no candidate of the cycle is to none, NEU-2075): one side each, never
-- both, so a gift on both sides is counted once in each figure, and a committee's top recipients
-- add up to its total_to_candidates. A giver->candidate pair whose 24Ks net negative for the cycle
-- is returned gifts, not gifts (NEU-2204): a void or refund is filed when it happens, and one of a
-- gift made last cycle has nothing here to net against. Such a pair is in
-- total_returned_by_candidates (a negative figure), not total_to_candidates, so neither goes below
-- 0 and the two add up to the giver's credited 24Ks; a pair netting 0 or more, a same-cycle void's,
-- nets inside total_to_candidates as before. total_from_organizations is the organization receipts
-- it recorded (ADR-0011), net of refunds, on the lines a total_individual counts: organization
-- money is the committee's only, in no candidate, race, cycle or donor figure.
-- total_non_contribution_account is a hybrid PAC's non-contribution account (NEU-2192),
-- individuals' and organizations' money alike: in neither
-- total_individual nor total_from_organizations, which hold its contribution account, the money
-- FEC's itemized figure (line 11(a)(i)) counts. 0 at every other committee. total_other_lines is
-- individuals' and organizations' money FEC files on a line no total_individual counts (silver's
-- is_other_line in contribution, NEU-2193, and in organization_receipt, NEU-2205): a national
-- party's convention, headquarters and recount accounts above all, a host committee's 18U gifts
-- from unregistered committees, transfers and loans. An organization's is in neither
-- total_from_organizations nor any other figure, so total_individual + total_from_organizations
-- compares with FEC's itemized figure like for like. The candidate's own money is self_funding
-- whatever its line (a loan's is line 13). total_refunds is the part of total_individual and
-- total_from_organizations FEC files on line 20 (NEU-2265): the counted refunds, by the same
-- filters, so 0 or less and never NULL. Both totals stay net of it (spec §7.1); FEC's gross basis
-- is total_individual + total_from_organizations - total_refunds. ie_total is the independent
-- expenditures it made, for and against candidates alike (silver's kind 'ie': 24E and 24A,
-- NEU-2057), net of corrections: those naming no candidate of the cycle too, which are in no
-- candidate's or race's figure. Its coordinated expenditures and communication costs are not.
CREATE TABLE committee_cycle AS
WITH received AS (
    SELECT
        recipient_committee_id AS committee_id,
        coalesce(
            sum(amount) FILTER (
                WHERE NOT is_self_funding
                    AND NOT is_non_contribution_account
                    AND NOT is_other_line
            ),
            0
        ) AS total_individual,
        coalesce(
            sum(amount) FILTER (
                WHERE NOT is_self_funding
                    AND NOT is_non_contribution_account
                    AND NOT is_other_line
                    AND fec_line = '20 refunds'
            ),
            0
        ) AS refunds,
        coalesce(sum(amount) FILTER (WHERE is_self_funding), 0) AS self_funding,
        coalesce(sum(amount) FILTER (WHERE is_non_contribution_account), 0)
            AS non_contribution_account,
        coalesce(sum(amount) FILTER (WHERE is_other_line AND NOT is_self_funding), 0)
            AS other_lines
    FROM silver.contribution
    GROUP BY recipient_committee_id
),
from_committees AS (
    SELECT to_committee_id AS committee_id, sum(amount) AS total_from_committees
    FROM silver.committee_transfer
    WHERE side = 'receipt'
    GROUP BY to_committee_id
),
from_organizations AS (
    SELECT
        recipient_committee_id AS committee_id,
        coalesce(
            sum(amount) FILTER (WHERE NOT is_non_contribution_account AND NOT is_other_line), 0
        ) AS total_from_organizations,
        coalesce(
            sum(amount) FILTER (
                WHERE NOT is_non_contribution_account
                    AND NOT is_other_line
                    AND fec_line = '20 refunds'
            ),
            0
        ) AS refunds,
        coalesce(sum(amount) FILTER (WHERE is_non_contribution_account), 0)
            AS non_contribution_account,
        coalesce(sum(amount) FILTER (WHERE is_other_line), 0) AS other_lines
    FROM silver.organization_receipt
    GROUP BY recipient_committee_id
),
given AS (
    SELECT from_committee_id AS committee_id, candidate_id, sum(amount) AS amount
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND candidate_id IS NOT NULL
    GROUP BY from_committee_id, candidate_id
),
to_candidates AS (
    SELECT
        committee_id,
        coalesce(sum(amount) FILTER (WHERE amount >= 0), 0) AS total_to_candidates,
        coalesce(sum(amount) FILTER (WHERE amount < 0), 0) AS total_returned_by_candidates
    FROM given
    GROUP BY committee_id
),
independent AS (
    SELECT committee_id, sum(amount) AS ie_total
    FROM silver.independent_expenditure
    WHERE kind = 'ie'
    GROUP BY committee_id
)
SELECT
    committee.committee_id,
    CAST({cycle} AS INTEGER) AS cycle,
    CAST(coalesce(received.total_individual, 0) AS DECIMAL(16, 2)) AS total_individual,
    CAST(coalesce(received.self_funding, 0) AS DECIMAL(16, 2)) AS self_funding,
    CAST(coalesce(from_committees.total_from_committees, 0) AS DECIMAL(16, 2)) AS total_from_committees,
    CAST(coalesce(from_organizations.total_from_organizations, 0) AS DECIMAL(16, 2))
        AS total_from_organizations,
    CAST(
        coalesce(received.non_contribution_account, 0)
            + coalesce(from_organizations.non_contribution_account, 0)
        AS DECIMAL(16, 2)
    ) AS total_non_contribution_account,
    CAST(
        coalesce(received.other_lines, 0) + coalesce(from_organizations.other_lines, 0)
        AS DECIMAL(16, 2)
    ) AS total_other_lines,
    CAST(
        coalesce(received.refunds, 0) + coalesce(from_organizations.refunds, 0) AS DECIMAL(16, 2)
    ) AS total_refunds,
    CAST(coalesce(to_candidates.total_to_candidates, 0) AS DECIMAL(16, 2)) AS total_to_candidates,
    CAST(coalesce(to_candidates.total_returned_by_candidates, 0) AS DECIMAL(16, 2))
        AS total_returned_by_candidates,
    CAST(coalesce(independent.ie_total, 0) AS DECIMAL(16, 2)) AS ie_total
FROM silver.committee AS committee
LEFT JOIN received USING (committee_id)
LEFT JOIN from_committees USING (committee_id)
LEFT JOIN from_organizations USING (committee_id)
LEFT JOIN to_candidates USING (committee_id)
LEFT JOIN independent USING (committee_id);
