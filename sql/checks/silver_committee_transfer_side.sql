-- Every side is one of the two, and names the file its row came from: a receipt is an `oth`
-- row, a disbursement a `pas2` row. The two files number their SUB_IDs apart, so a row of one
-- is never found in the other.
SELECT source_record_id, side, transaction_type
FROM committee_transfer
WHERE side IS NULL
    OR side NOT IN ('receipt', 'disbursement')
    OR (side = 'receipt' AND source_record_id NOT IN (SELECT SUB_ID FROM oth))
    OR (side = 'disbursement' AND source_record_id NOT IN (SELECT SUB_ID FROM pas2));
