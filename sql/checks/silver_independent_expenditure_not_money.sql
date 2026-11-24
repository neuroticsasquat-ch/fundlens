-- No independent expenditure, nor any other row of independent_expenditure, is a contribution,
-- a committee transfer or an organization receipt (NEU-2057): spending for or against a candidate
-- is never money given to one. `oth` repeats every `pas2` row under its SUB_ID (NEU-2070), so a
-- row read from either file twice would be found here. A 24/48-hour row has no SUB_ID, and is in
-- none of those files.
WITH pas2_row AS (
    -- source_record_id is text (NEU-2165); a `pas2` row's is its SUB_ID's digits.
    SELECT CAST(source_record_id AS UBIGINT) AS sub_id
    FROM independent_expenditure
    WHERE source_file = 'pas2'
)
SELECT sub_id AS source_record_id, 'contribution' AS also_in
FROM pas2_row
WHERE sub_id IN (SELECT source_record_id FROM contribution)
UNION ALL
SELECT sub_id, 'committee_transfer'
FROM pas2_row
WHERE sub_id IN (SELECT source_record_id FROM committee_transfer)
UNION ALL
SELECT sub_id, 'organization_receipt'
FROM pas2_row
WHERE sub_id IN (SELECT source_record_id FROM organization_receipt)
UNION ALL
SELECT source_record_id, 'contribution typed ' || transaction_type
FROM contribution
WHERE transaction_type IN ('24A', '24E', '24C', '24F', '24N');
