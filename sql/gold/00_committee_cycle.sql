-- committee_cycle (spec §7.1, NEU-2039 §3): one row per committee of each cycle, every figure the
-- cycle's own, summed over that cycle's silver rows (NEU-2059).
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
-- total_operating_expenditures is its counted operating expenditures (silver's `counted`,
-- every-FEC-dollar spec §5.2, §5.5), net as filed, in-kind outlays included: spending, in no
-- receipt figure. NULL, never 0, where it has no counted row: a cycle before 2004, or one whose
-- live build predates the table (§2, older builds), reads as not available, not as nothing spent;
-- counted rows netting to $0 are 0.
--
-- The reported_* fields are FEC's figures for the committee as filed, its silver reported_total row
-- (every-FEC-dollar spec §4.1, §4.4): NULL where it has no row or the cycle's file lacks the
-- measure, never 0, and never added to any figure above. itemized_total is fundlens's figure to
-- compare with reported_individual_itemized (FEC's line 11(a)(i), CONTEXT.md): total_individual +
-- total_from_organizations - total_refunds, gross of refunds as FEC's is, never NULL; a comparison
-- figure, in no race total or top list. coverage is itemized_total / reported_individual_itemized,
-- a ratio stored as computed, above 1 where fundlens counts more than FEC: NULL where the reported
-- figure is NULL or 0 (every cycle before 2008, a Form 4 or Form 5 filer), and at a conduit, whose
-- itemized figure includes the earmarks fundlens counts at their recipients (ADR-0004).
-- 00_ so it runs first: candidate_cycle sums its credited committees' figures.
CREATE TABLE committee_cycle AS
WITH received AS (
    SELECT
        cycle,
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
    GROUP BY cycle, recipient_committee_id
),
from_committees AS (
    SELECT cycle, to_committee_id AS committee_id, sum(amount) AS total_from_committees
    FROM silver.committee_transfer
    WHERE side = 'receipt'
    GROUP BY cycle, to_committee_id
),
from_organizations AS (
    SELECT
        cycle,
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
    GROUP BY cycle, recipient_committee_id
),
given AS (
    SELECT cycle, from_committee_id AS committee_id, candidate_id, sum(amount) AS amount
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND candidate_id IS NOT NULL
    GROUP BY cycle, from_committee_id, candidate_id
),
to_candidates AS (
    SELECT
        cycle,
        committee_id,
        coalesce(sum(amount) FILTER (WHERE amount >= 0), 0) AS total_to_candidates,
        coalesce(sum(amount) FILTER (WHERE amount < 0), 0) AS total_returned_by_candidates
    FROM given
    GROUP BY cycle, committee_id
),
independent AS (
    SELECT cycle, committee_id, sum(amount) AS ie_total
    FROM silver.independent_expenditure
    WHERE kind = 'ie'
    GROUP BY cycle, committee_id
),
spent AS (
    SELECT cycle, committee_id, sum(amount) AS total_operating_expenditures
    FROM silver.operating_expenditure
    WHERE counted
    GROUP BY cycle, committee_id
),
totals AS (
    SELECT
        committee.committee_id,
        CAST(committee.cycle AS INTEGER) AS cycle,
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
        CAST(coalesce(independent.ie_total, 0) AS DECIMAL(16, 2)) AS ie_total,
        CAST(spent.total_operating_expenditures AS DECIMAL(16, 2)) AS total_operating_expenditures,
        committee.is_conduit
    FROM silver.committee AS committee
    LEFT JOIN received USING (cycle, committee_id)
    LEFT JOIN from_committees USING (cycle, committee_id)
    LEFT JOIN from_organizations USING (cycle, committee_id)
    LEFT JOIN to_candidates USING (cycle, committee_id)
    LEFT JOIN independent USING (cycle, committee_id)
    LEFT JOIN spent USING (cycle, committee_id)
),
itemized AS (
    SELECT
        *,
        CAST(total_individual + total_from_organizations - total_refunds AS DECIMAL(16, 2))
            AS itemized_total
    FROM totals
)
SELECT
    itemized.* EXCLUDE (is_conduit, itemized_total),
    reported.source_file AS reported_source_file,
    reported.period_start AS reported_period_start,
    reported.period_end AS reported_period_end,
    CAST(reported.receipts AS DECIMAL(16, 2)) AS reported_receipts,
    CAST(reported.disbursements AS DECIMAL(16, 2)) AS reported_disbursements,
    CAST(reported.cash_on_hand_start AS DECIMAL(16, 2)) AS reported_cash_on_hand_start,
    CAST(reported.cash_on_hand_end AS DECIMAL(16, 2)) AS reported_cash_on_hand_end,
    CAST(reported.debts_owed_by AS DECIMAL(16, 2)) AS reported_debts_owed_by,
    CAST(reported.debts_owed_to AS DECIMAL(16, 2)) AS reported_debts_owed_to,
    CAST(reported.individual_itemized AS DECIMAL(16, 2)) AS reported_individual_itemized,
    CAST(reported.individual_unitemized AS DECIMAL(16, 2)) AS reported_individual_unitemized,
    CAST(reported.individual_total AS DECIMAL(16, 2)) AS reported_individual_total,
    CAST(reported.individual_refunds AS DECIMAL(16, 2)) AS reported_individual_refunds,
    CAST(reported.party_contributions AS DECIMAL(16, 2)) AS reported_party_contributions,
    CAST(reported.other_committee_contributions AS DECIMAL(16, 2)) AS reported_other_committee_contributions,
    CAST(reported.candidate_contributions AS DECIMAL(16, 2)) AS reported_candidate_contributions,
    CAST(reported.candidate_loans AS DECIMAL(16, 2)) AS reported_candidate_loans,
    CAST(reported.other_loans AS DECIMAL(16, 2)) AS reported_other_loans,
    CAST(reported.candidate_loan_repayments AS DECIMAL(16, 2)) AS reported_candidate_loan_repayments,
    CAST(reported.other_loan_repayments AS DECIMAL(16, 2)) AS reported_other_loan_repayments,
    CAST(reported.transfers_in AS DECIMAL(16, 2)) AS reported_transfers_in,
    CAST(reported.transfers_out AS DECIMAL(16, 2)) AS reported_transfers_out,
    CAST(reported.independent_expenditures AS DECIMAL(16, 2)) AS reported_independent_expenditures,
    CAST(reported.party_coordinated AS DECIMAL(16, 2)) AS reported_party_coordinated,
    CAST(reported.operating_expenditures AS DECIMAL(16, 2)) AS reported_operating_expenditures,
    CAST(reported.federal_funds AS DECIMAL(16, 2)) AS reported_federal_funds,
    itemized.itemized_total,
    CASE
        WHEN NOT itemized.is_conduit AND reported.individual_itemized <> 0
            THEN CAST(itemized.itemized_total AS DOUBLE) / CAST(reported.individual_itemized AS DOUBLE)
    END AS coverage
FROM itemized
LEFT JOIN silver.reported_total AS reported USING (cycle, committee_id);
