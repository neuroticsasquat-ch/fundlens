-- candidate_reported_total (every-FEC-dollar spec §4.2): each candidate's cycle-to-date figures
-- as FEC's `weball` reports them, 1980–2006, one row per candidate of the cycle in silver
-- `candidate`. `reported_total`'s columns with `candidate_id` in place of `committee_id`; a
-- measure `weball` lacks is NULL. FEC's figures as filed, never added to itemized money.
--
-- From 2008 the partition is empty: a candidate's figures are the sum of the committees fundlens
-- credits them with (gold, spec §4.3), so the dataset never holds a 2008+ candidate figure the
-- site contradicts.
--
-- `weball` lists a committee's money under each candidate id linked to it, so its rows do not add
-- up across candidates. That stands as filed: a candidate alias has no gold row, so its repeat is
-- in no race.
CREATE TABLE candidate_reported_total AS
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    'US' AS jurisdiction,
    'weball' AS source_file,
    CAND_ID AS candidate_id,
    CAST(NULL AS DATE) AS period_start,
    CAST(try_strptime(CVG_END_DT, '%m/%d/%Y') AS DATE) AS period_end,
    TTL_RECEIPTS AS receipts,
    TTL_DISB AS disbursements,
    COH_BOP AS cash_on_hand_start,
    COH_COP AS cash_on_hand_end,
    DEBTS_OWED_BY AS debts_owed_by,
    CAST(NULL AS DECIMAL(14, 2)) AS debts_owed_to,
    CAST(NULL AS DECIMAL(14, 2)) AS individual_itemized,
    CAST(NULL AS DECIMAL(14, 2)) AS individual_unitemized,
    TTL_INDIV_CONTRIB AS individual_total,
    INDIV_REFUNDS AS individual_refunds,
    POL_PTY_CONTRIB AS party_contributions,
    OTHER_POL_CMTE_CONTRIB AS other_committee_contributions,
    CAND_CONTRIB AS candidate_contributions,
    CAND_LOANS AS candidate_loans,
    OTHER_LOANS AS other_loans,
    CAND_LOAN_REPAY AS candidate_loan_repayments,
    OTHER_LOAN_REPAY AS other_loan_repayments,
    TRANS_FROM_AUTH AS transfers_in,
    TRANS_TO_AUTH AS transfers_out,
    CAST(NULL AS DECIMAL(14, 2)) AS independent_expenditures,
    CAST(NULL AS DECIMAL(14, 2)) AS party_coordinated,
    CAST(NULL AS DECIMAL(14, 2)) AS operating_expenditures,
    CAST(NULL AS DECIMAL(14, 2)) AS federal_funds
FROM weball
WHERE {cycle} < 2008
    AND CAND_ID IN (SELECT candidate_id FROM candidate);
