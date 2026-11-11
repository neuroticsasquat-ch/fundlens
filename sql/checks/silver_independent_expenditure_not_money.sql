-- No independent expenditure, nor any other row of independent_expenditure, is a contribution,
-- a committee transfer or an organization receipt (NEU-2057): spending for or against a candidate
-- is never money given to one. `oth` repeats every `pas2` row under its SUB_ID (NEU-2070), so a
-- row read from either file twice would be found here.
SELECT source_record_id, 'contribution' AS also_in
FROM independent_expenditure
WHERE source_record_id IN (SELECT source_record_id FROM contribution)
UNION ALL
SELECT source_record_id, 'committee_transfer'
FROM independent_expenditure
WHERE source_record_id IN (SELECT source_record_id FROM committee_transfer)
UNION ALL
SELECT source_record_id, 'organization_receipt'
FROM independent_expenditure
WHERE source_record_id IN (SELECT source_record_id FROM organization_receipt)
UNION ALL
SELECT source_record_id, 'contribution typed ' || transaction_type
FROM contribution
WHERE transaction_type IN ('24A', '24E', '24C', '24F', '24N');
