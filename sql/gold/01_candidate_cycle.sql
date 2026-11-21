-- candidate_cycle (spec §7.1, NEU-2039 §3): one row per silver candidate of each cycle (NEU-2059:
-- every figure below is the cycle's own, summed over that cycle's silver rows), with or
-- without a race (the fixture's H4MD09109 has money but no seat), but an alias (NEU-2127): a
-- person's second id for the same race, holding no money, is in candidate_redirect instead. So
-- race_candidate, race.candidate_count and search_entity, all built from this, list each person
-- once.
--
-- total_individual is every counted contribution to a committee raising for the candidate that is
-- not the candidate's own money, nor on a line FEC's itemized figure leaves out (silver's
-- is_other_line, NEU-2193: a transfer, an earmark's conduit side, a loan); self_funding is that
-- own money (silver's is_self_funding), and neither includes the other. total_committee is the
-- committees' gifts to the candidate: the disbursement side of committee_transfer only (the
-- recipient's 18K twin would count each gift twice), less a giver whose 24Ks to the candidate net
-- below 0 for the cycle: returned gifts, voids of an earlier cycle's, in the giver's
-- total_returned_by_candidates and never the candidate's (NEU-2204).
-- total_jfc_transfers is the receipts of the committees raising for the candidate from a
-- joint fundraising committee (designation J): its transfers of the candidate's share (NEU-2124),
-- whatever receipt type the filer gave them (18G mostly, some 18J and 15J; FEC's own transfers-in
-- totals take them all). It is in neither figure above, and counts nothing twice: the JFC's own
-- contributions raise for no candidate.
-- Refunds are negative amounts and net out. Nothing to sum is 0, never NULL.
-- contributor_count is the donors whose counted gifts reached the candidate, their own money aside;
-- NULL for every candidate of a cycle whose build was loaded before `resolve`, whose contributions
-- have no donor (the loader gives them a NULL donor_id).
-- ie_support and ie_oppose are the independent expenditures for and against the candidate
-- (silver's kind 'ie': 24E and 24A, NEU-2057), net of corrections, by anyone: spending, never money
-- the candidate received, in no figure above. A coordinated expenditure or communication cost is
-- in neither. total_operating_expenditures is the counted operating expenditures silver credits to
-- the candidate (its `candidate_id`, contribution's credit rule: a handed-off committee's by the
-- row's date, so C00703975's 2024 spending before 2024-07-21 is BIDEN's and the rest HARRIS's;
-- every-FEC-dollar spec §5.5), net as filed: spending, in no receipt figure. NULL, never 0, where
-- none is credited. reported_operating_expenditures (below) is the handed-off committee's whole for
-- the second candidate, so the two are not comparable at a handoff.
--
-- The reported_* fields are FEC's figures (every-FEC-dollar spec §4.3, §4.4). From 2008 they are
-- the sums of the candidate's credited committees' committee_cycle figures, each NULL when none of
-- them has it, the period their earliest start and latest end, reported_source_file
-- 'committee_summary'. The credited committees are those 04_contribution.sql's `linked` rule gives
-- the candidate (P or A in `ccl`, or the candidate's CAND_PCC; a committee linked to two candidates
-- is the principal link's, then the lower candidate_id's), but that a handed-off committee
-- (fec/handoffs.csv) is the second candidate's whole: a cycle-to-date row cannot be split at the
-- handoff date, so the first candidate has none. Each committee is one candidate's, so the figures
-- add up across candidates; transfers between a candidate's own committees are not netted out, as
-- FEC does not net them. reported_includes_converted_committee: a committee with a reported row is
-- credited through CAND_PCC alone, a campaign turned PAC that `ccl` no longer designates P or A,
-- whose whole row is the candidate's. Before 2008, the candidate's silver candidate_reported_total
-- row (`weball`) as filed, and the flag false.
-- itemized_total is the sum of the credited committees' (NULL with none: a handoff's first
-- candidate, beside their total_individual), and coverage, from 2008, that over their reported
-- itemized figures, both sides over the credited committees with one, conduits aside; NULL where
-- that is NULL or 0, and before 2008, when `weball` has no itemized figure.
CREATE TABLE candidate_cycle AS
WITH money AS (
    SELECT
        cycle,
        candidate_id,
        coalesce(sum(amount) FILTER (WHERE NOT is_self_funding AND NOT is_other_line), 0)
            AS total_individual,
        coalesce(sum(amount) FILTER (WHERE is_self_funding), 0) AS self_funding,
        count(DISTINCT donor_id) FILTER (WHERE NOT is_self_funding AND NOT is_other_line)
            AS contributor_count
    FROM silver.contribution
    WHERE candidate_id IS NOT NULL
    GROUP BY cycle, candidate_id
),
resolved AS (
    SELECT cycle, count(donor_id) = count(*) AS resolved
    FROM silver.contribution
    GROUP BY cycle
),
from_committees AS (
    SELECT cycle, candidate_id, sum(amount) AS total_committee
    FROM (
        SELECT cycle, from_committee_id, candidate_id, sum(amount) AS amount
        FROM silver.committee_transfer
        WHERE side = 'disbursement' AND candidate_id IS NOT NULL
        GROUP BY cycle, from_committee_id, candidate_id
        HAVING sum(amount) >= 0
    ) AS given
    GROUP BY cycle, candidate_id
),
jfc_transfers AS (
    SELECT transfer.cycle, transfer.candidate_id, sum(transfer.amount) AS total_jfc_transfers
    FROM silver.committee_transfer AS transfer
    JOIN silver.committee AS jfc
        ON jfc.cycle = transfer.cycle
        AND jfc.committee_id = transfer.from_committee_id
        AND jfc.designation = 'J'
    WHERE transfer.side = 'receipt' AND transfer.candidate_id IS NOT NULL
    GROUP BY transfer.cycle, transfer.candidate_id
),
independent AS (
    SELECT
        cycle,
        candidate_id,
        coalesce(sum(amount) FILTER (WHERE support_oppose = 'S'), 0) AS ie_support,
        coalesce(sum(amount) FILTER (WHERE support_oppose = 'O'), 0) AS ie_oppose
    FROM silver.independent_expenditure
    WHERE kind = 'ie' AND candidate_id IS NOT NULL
    GROUP BY cycle, candidate_id
),
spent AS (
    SELECT cycle, candidate_id, sum(amount) AS total_operating_expenditures
    FROM silver.operating_expenditure
    WHERE counted AND candidate_id IS NOT NULL
    GROUP BY cycle, candidate_id
),
credited AS (
    (
        SELECT
            link.cycle,
            link.committee_id,
            link.candidate_id,
            NOT coalesce(link.designation IN ('P', 'A'), false) AS is_converted
        FROM silver.candidate_committee_link AS link
        LEFT JOIN silver.candidate AS candidate USING (cycle, candidate_id)
        WHERE (
                link.designation IN ('P', 'A')
                OR link.committee_id = candidate.principal_committee_id
            )
            AND NOT EXISTS (
                SELECT 1
                FROM handoff
                WHERE handoff.cycle = link.cycle AND handoff.committee_id = link.committee_id
            )
        QUALIFY row_number() OVER (
            PARTITION BY link.cycle, link.committee_id
            ORDER BY
                (link.designation = 'P' OR link.committee_id = candidate.principal_committee_id) DESC,
                link.candidate_id
        ) = 1
    )
    UNION ALL
    SELECT cycle, committee_id, to_candidate_id AS candidate_id, false AS is_converted
    FROM handoff
),
credited_itemized AS (
    SELECT credited.cycle, credited.candidate_id, sum(committee_cycle.itemized_total) AS itemized_total
    FROM credited
    JOIN committee_cycle USING (cycle, committee_id)
    GROUP BY ALL
),
reported AS (
    SELECT
        credited.cycle,
        credited.candidate_id,
        'committee_summary' AS source_file,
        min(committee_cycle.reported_period_start) AS period_start,
        max(committee_cycle.reported_period_end) AS period_end,
        sum(committee_cycle.reported_receipts) AS receipts,
        sum(committee_cycle.reported_disbursements) AS disbursements,
        sum(committee_cycle.reported_cash_on_hand_start) AS cash_on_hand_start,
        sum(committee_cycle.reported_cash_on_hand_end) AS cash_on_hand_end,
        sum(committee_cycle.reported_debts_owed_by) AS debts_owed_by,
        sum(committee_cycle.reported_debts_owed_to) AS debts_owed_to,
        sum(committee_cycle.reported_individual_itemized) AS individual_itemized,
        sum(committee_cycle.reported_individual_unitemized) AS individual_unitemized,
        sum(committee_cycle.reported_individual_total) AS individual_total,
        sum(committee_cycle.reported_individual_refunds) AS individual_refunds,
        sum(committee_cycle.reported_party_contributions) AS party_contributions,
        sum(committee_cycle.reported_other_committee_contributions) AS other_committee_contributions,
        sum(committee_cycle.reported_candidate_contributions) AS candidate_contributions,
        sum(committee_cycle.reported_candidate_loans) AS candidate_loans,
        sum(committee_cycle.reported_other_loans) AS other_loans,
        sum(committee_cycle.reported_candidate_loan_repayments) AS candidate_loan_repayments,
        sum(committee_cycle.reported_other_loan_repayments) AS other_loan_repayments,
        sum(committee_cycle.reported_transfers_in) AS transfers_in,
        sum(committee_cycle.reported_transfers_out) AS transfers_out,
        sum(committee_cycle.reported_independent_expenditures) AS independent_expenditures,
        sum(committee_cycle.reported_party_coordinated) AS party_coordinated,
        sum(committee_cycle.reported_operating_expenditures) AS operating_expenditures,
        sum(committee_cycle.reported_federal_funds) AS federal_funds,
        CAST(
            sum(committee_cycle.itemized_total) FILTER (
                WHERE committee_cycle.reported_individual_itemized IS NOT NULL
                    AND NOT committee.is_conduit
            ) AS DOUBLE
        ) / CAST(
            nullif(
                sum(committee_cycle.reported_individual_itemized) FILTER (
                    WHERE NOT committee.is_conduit
                ),
                0
            ) AS DOUBLE
        ) AS coverage,
        bool_or(credited.is_converted) AS includes_converted_committee
    FROM credited
    JOIN committee_cycle USING (cycle, committee_id)
    JOIN silver.committee AS committee USING (cycle, committee_id)
    WHERE credited.cycle >= 2008 AND committee_cycle.reported_source_file IS NOT NULL
    GROUP BY ALL
    UNION ALL BY NAME
    SELECT
        cycle,
        candidate_id,
        source_file,
        period_start,
        period_end,
        receipts,
        disbursements,
        cash_on_hand_start,
        cash_on_hand_end,
        debts_owed_by,
        debts_owed_to,
        individual_itemized,
        individual_unitemized,
        individual_total,
        individual_refunds,
        party_contributions,
        other_committee_contributions,
        candidate_contributions,
        candidate_loans,
        other_loans,
        candidate_loan_repayments,
        other_loan_repayments,
        transfers_in,
        transfers_out,
        independent_expenditures,
        party_coordinated,
        operating_expenditures,
        federal_funds,
        CAST(NULL AS DOUBLE) AS coverage,
        false AS includes_converted_committee
    FROM silver.candidate_reported_total
    WHERE cycle < 2008
)
SELECT
    candidate.candidate_id,
    CAST(candidate.cycle AS INTEGER) AS cycle,
    candidate.race_id,
    CAST(coalesce(money.total_individual, 0) AS DECIMAL(16, 2)) AS total_individual,
    CAST(coalesce(from_committees.total_committee, 0) AS DECIMAL(16, 2)) AS total_committee,
    CAST(coalesce(jfc_transfers.total_jfc_transfers, 0) AS DECIMAL(16, 2)) AS total_jfc_transfers,
    CAST(coalesce(money.self_funding, 0) AS DECIMAL(16, 2)) AS self_funding,
    CAST(coalesce(independent.ie_support, 0) AS DECIMAL(16, 2)) AS ie_support,
    CAST(coalesce(independent.ie_oppose, 0) AS DECIMAL(16, 2)) AS ie_oppose,
    CAST(spent.total_operating_expenditures AS DECIMAL(16, 2)) AS total_operating_expenditures,
    CASE
        -- A cycle with no contributions at all has nothing to leave unresolved.
        WHEN coalesce(resolved.resolved, true) THEN CAST(coalesce(money.contributor_count, 0) AS INTEGER)
    END AS contributor_count,
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
    CAST(credited_itemized.itemized_total AS DECIMAL(16, 2)) AS itemized_total,
    reported.coverage,
    coalesce(reported.includes_converted_committee, false) AS reported_includes_converted_committee
FROM silver.candidate AS candidate
LEFT JOIN resolved USING (cycle)
LEFT JOIN money USING (cycle, candidate_id)
LEFT JOIN from_committees USING (cycle, candidate_id)
LEFT JOIN jfc_transfers USING (cycle, candidate_id)
LEFT JOIN independent USING (cycle, candidate_id)
LEFT JOIN spent USING (cycle, candidate_id)
LEFT JOIN credited_itemized USING (cycle, candidate_id)
LEFT JOIN reported USING (cycle, candidate_id)
WHERE candidate.alias_of IS NULL;
