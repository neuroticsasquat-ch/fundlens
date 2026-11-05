-- Every side is one of the two, and names the file its row came from: a receipt is an `oth`
-- row, or an `indiv` row a committee's by the name-match rule (NEU-2131); a disbursement a
-- `pas2` row. The files number their SUB_IDs apart, so a row of one is never found in another.
-- The receipts `oth` lacks are the few name-matched ones, looked up in `indiv` with the bulk
-- file on the left, so the join builds on them and never on the file.
WITH not_in_oth AS (
    SELECT source_record_id
    FROM committee_transfer
    WHERE side = 'receipt' AND source_record_id NOT IN (SELECT SUB_ID FROM oth)
),
in_indiv AS (
    SELECT not_in_oth.source_record_id
    FROM indiv
    JOIN not_in_oth ON not_in_oth.source_record_id = indiv.SUB_ID
)
SELECT source_record_id, side, transaction_type
FROM committee_transfer
WHERE side IS NULL
    OR side NOT IN ('receipt', 'disbursement')
    OR (
        side = 'receipt'
        AND source_record_id IN (SELECT source_record_id FROM not_in_oth)
        AND source_record_id NOT IN (SELECT source_record_id FROM in_indiv)
    )
    OR (side = 'disbursement' AND source_record_id NOT IN (SELECT SUB_ID FROM pas2));
