-- reported_total (every-FEC-dollar spec §4.1): each committee's cycle-to-date figures as FEC
-- reports them, one row per committee of the cycle. FEC's figures as filed: a blank is NULL, a
-- filed 0 is 0, nothing is netted, and nothing is ever added to itemized money.
--
-- Which file a row comes from depends on the cycle (spec §4, source precedence):
-- - 2008 on: `committee_summary`, one row per CMTE_ID. The file repeats a committee once per
--   linked candidate, every field but CAND_ID and Link_Image alike, and now and then lists a
--   committee twice over different periods (NEU-2454). The row kept is the one covering the
--   cycle to date: the earliest start, then the latest end. silver_reported_total_repeat.sql
--   fails the build when the rows over that period differ. A Form 5 filer
--   (type I) or Form 7 filer (type C) has a row carrying little or nothing: each measure it leaves
--   blank is `webk`'s, when `webk` holds the committee, and its `source_file` says so; its
--   reporting period stays `committee_summary`'s, both ends from one file. No other
--   committee's row is filled from `webk`: a Form 3X PAC's blank candidate lines are lines its
--   form lacks, not figures FEC left out. A committee only in `webk` gets no row.
-- - 1996–2006: `webk`, its rows as they are. It holds no House or Senate campaign committee.
-- - 1980–1994: no committee-grain file, and no row.
-- Only committees of the cycle in silver `committee` get a row. A row whose every measure is
-- blank is kept: FEC lists the committee and reports nothing.
CREATE TABLE reported_total AS
WITH summary AS (
    SELECT
        CMTE_ID AS committee_id,
        CMTE_TP AS committee_type,
        CAST(try_strptime(CVG_START_DT, '%Y%m%d') AS DATE) AS period_start,
        CAST(try_strptime(CVG_END_DT, '%Y%m%d') AS DATE) AS period_end,
        TTL_RECEIPTS AS receipts,
        TTL_DISB AS disbursements,
        COH_BOP AS cash_on_hand_start,
        COH_COP AS cash_on_hand_end,
        DEBTS_OWED_BY_CMTE AS debts_owed_by,
        DEBTS_OWED_TO_CMTE AS debts_owed_to,
        INDV_ITEM_CONTB AS individual_itemized,
        INDV_UNITEM_CONTB AS individual_unitemized,
        INDV_CONTB AS individual_total,
        INDV_REF AS individual_refunds,
        PTY_CMTE_CONTB AS party_contributions,
        OTH_CMTE_CONTB AS other_committee_contributions,
        CAND_CNTB AS candidate_contributions,
        CAND_LOAN AS candidate_loans,
        -- A Form 3X has one loans line, and leaves OTH_LOANS blank: its loans are TTL_LOANS.
        CAST(coalesce(OTH_LOANS, TTL_LOANS - coalesce(CAND_LOAN, 0)) AS DECIMAL(14, 2))
            AS other_loans,
        CAND_LOAN_REPYMNT AS candidate_loan_repayments,
        OTH_LOAN_REPYMTS AS other_loan_repayments,
        TRANF_FROM_OTHER_AUTH_CMTE AS transfers_in,
        TRANF_TO_OTHER_AUTH_CMTE AS transfers_out,
        INDT_EXP AS independent_expenditures,
        COORD_EXP_BY_PTY_CMTE AS party_coordinated,
        -- Form 3 and 3P fill OP_EXP, Form 3X TTL_OP_EXP; a campaign turned PAC fills both, each
        -- with a different form's reports.
        CAST(CASE
            WHEN OP_EXP IS NOT NULL OR TTL_OP_EXP IS NOT NULL
                THEN coalesce(OP_EXP, 0) + coalesce(TTL_OP_EXP, 0)
        END AS DECIMAL(14, 2)) AS operating_expenditures,
        FED_FUNDS AS federal_funds
    FROM committee_summary
    QUALIFY row_number() OVER (
        PARTITION BY CMTE_ID
        ORDER BY period_start ASC NULLS LAST, period_end DESC NULLS LAST, CAND_ID
    ) = 1
),
-- `webk`'s rows under the same names, NULL for a measure it does not have.
pac AS (
    SELECT
        CMTE_ID AS committee_id,
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
        INDV_CONTRIB AS individual_total,
        INDV_REFUNDS AS individual_refunds,
        CAST(NULL AS DECIMAL(14, 2)) AS party_contributions,
        OTHER_POL_CMTE_CONTRIB AS other_committee_contributions,
        CAND_CONTRIB AS candidate_contributions,
        CAND_LOANS AS candidate_loans,
        CAST(TTL_LOANS_RECEIVED - coalesce(CAND_LOANS, 0) AS DECIMAL(14, 2)) AS other_loans,
        CAND_LOAN_REPAY AS candidate_loan_repayments,
        LOAN_REPAY AS other_loan_repayments,
        TRANS_FROM_AFF AS transfers_in,
        TRANF_TO_AFF AS transfers_out,
        IND_EXP AS independent_expenditures,
        PTY_COORD_EXP AS party_coordinated,
        CAST(NULL AS DECIMAL(14, 2)) AS operating_expenditures,
        CAST(NULL AS DECIMAL(14, 2)) AS federal_funds
    FROM webk
),
-- 2008 on: each Form 5 or Form 7 filer's `committee_summary` row beside its `webk` row.
filled AS (
    SELECT
        summary.*,
        pac.committee_id IS NOT NULL AND (
            (summary.receipts IS NULL AND pac.receipts IS NOT NULL)
            OR (summary.disbursements IS NULL AND pac.disbursements IS NOT NULL)
            OR (summary.cash_on_hand_start IS NULL AND pac.cash_on_hand_start IS NOT NULL)
            OR (summary.cash_on_hand_end IS NULL AND pac.cash_on_hand_end IS NOT NULL)
            OR (summary.debts_owed_by IS NULL AND pac.debts_owed_by IS NOT NULL)
            OR (summary.individual_total IS NULL AND pac.individual_total IS NOT NULL)
            OR (summary.individual_refunds IS NULL AND pac.individual_refunds IS NOT NULL)
            OR (
                summary.other_committee_contributions IS NULL
                AND pac.other_committee_contributions IS NOT NULL
            )
            OR (
                summary.candidate_contributions IS NULL
                AND pac.candidate_contributions IS NOT NULL
            )
            OR (summary.candidate_loans IS NULL AND pac.candidate_loans IS NOT NULL)
            OR (summary.other_loans IS NULL AND pac.other_loans IS NOT NULL)
            OR (
                summary.candidate_loan_repayments IS NULL
                AND pac.candidate_loan_repayments IS NOT NULL
            )
            OR (summary.other_loan_repayments IS NULL AND pac.other_loan_repayments IS NOT NULL)
            OR (summary.transfers_in IS NULL AND pac.transfers_in IS NOT NULL)
            OR (summary.transfers_out IS NULL AND pac.transfers_out IS NOT NULL)
            OR (
                summary.independent_expenditures IS NULL
                AND pac.independent_expenditures IS NOT NULL
            )
            OR (summary.party_coordinated IS NULL AND pac.party_coordinated IS NOT NULL)
        ) AS from_webk,
        pac.receipts AS pac_receipts,
        pac.disbursements AS pac_disbursements,
        pac.cash_on_hand_start AS pac_cash_on_hand_start,
        pac.cash_on_hand_end AS pac_cash_on_hand_end,
        pac.debts_owed_by AS pac_debts_owed_by,
        pac.individual_total AS pac_individual_total,
        pac.individual_refunds AS pac_individual_refunds,
        pac.other_committee_contributions AS pac_other_committee_contributions,
        pac.candidate_contributions AS pac_candidate_contributions,
        pac.candidate_loans AS pac_candidate_loans,
        pac.other_loans AS pac_other_loans,
        pac.candidate_loan_repayments AS pac_candidate_loan_repayments,
        pac.other_loan_repayments AS pac_other_loan_repayments,
        pac.transfers_in AS pac_transfers_in,
        pac.transfers_out AS pac_transfers_out,
        pac.independent_expenditures AS pac_independent_expenditures,
        pac.party_coordinated AS pac_party_coordinated
    FROM summary
    LEFT JOIN pac
        ON pac.committee_id = summary.committee_id
        AND summary.committee_type IN ('I', 'C')
),
reported AS (
    SELECT
        committee_id,
        CASE WHEN from_webk THEN 'committee_summary+webk' ELSE 'committee_summary' END
            AS source_file,
        period_start,
        period_end,
        coalesce(receipts, pac_receipts) AS receipts,
        coalesce(disbursements, pac_disbursements) AS disbursements,
        coalesce(cash_on_hand_start, pac_cash_on_hand_start) AS cash_on_hand_start,
        coalesce(cash_on_hand_end, pac_cash_on_hand_end) AS cash_on_hand_end,
        coalesce(debts_owed_by, pac_debts_owed_by) AS debts_owed_by,
        debts_owed_to,
        individual_itemized,
        individual_unitemized,
        coalesce(individual_total, pac_individual_total) AS individual_total,
        coalesce(individual_refunds, pac_individual_refunds) AS individual_refunds,
        party_contributions,
        coalesce(other_committee_contributions, pac_other_committee_contributions)
            AS other_committee_contributions,
        coalesce(candidate_contributions, pac_candidate_contributions)
            AS candidate_contributions,
        coalesce(candidate_loans, pac_candidate_loans) AS candidate_loans,
        coalesce(other_loans, pac_other_loans) AS other_loans,
        coalesce(candidate_loan_repayments, pac_candidate_loan_repayments)
            AS candidate_loan_repayments,
        coalesce(other_loan_repayments, pac_other_loan_repayments) AS other_loan_repayments,
        coalesce(transfers_in, pac_transfers_in) AS transfers_in,
        coalesce(transfers_out, pac_transfers_out) AS transfers_out,
        coalesce(independent_expenditures, pac_independent_expenditures)
            AS independent_expenditures,
        coalesce(party_coordinated, pac_party_coordinated) AS party_coordinated,
        operating_expenditures,
        federal_funds
    FROM filled
    UNION ALL BY NAME
    -- 1996–2006: FEC publishes no `committee_summary`, and `webk` is the committees' only file.
    SELECT 'webk' AS source_file, *
    FROM pac
    WHERE {cycle} < 2008
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    'US' AS jurisdiction,
    source_file,
    committee_id,
    * EXCLUDE (committee_id, source_file)
FROM reported
WHERE committee_id IN (SELECT committee_id FROM committee);
