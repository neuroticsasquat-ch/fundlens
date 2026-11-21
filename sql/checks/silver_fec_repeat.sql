-- No counted row is one FEC's file repeats (NEU-2401): no silver table built from the itemized
-- files holds a row of `indiv_repeat`, `oth_repeat`, `pas2_repeat` or `oppexp_repeat` (the
-- transform runner's `_drop_fec_repeats`), a transaction's second, third or fourth row on its
-- filing. SUB_IDs are FEC's ids across its files, so one list serves every table. It catches a
-- model reading a file's rows as published (`<file>_published`) rather than its view; 2024 has
-- 18,783 receipt-side repeats and 2,943 in `oppexp`.
WITH repeat AS (
    SELECT SUB_ID, 'indiv' AS file FROM indiv_repeat
    UNION ALL
    SELECT SUB_ID, 'oth' FROM oth_repeat
    UNION ALL
    SELECT SUB_ID, 'pas2' FROM pas2_repeat
    UNION ALL
    SELECT SUB_ID, 'oppexp' FROM oppexp_repeat
)
SELECT 'contribution' AS silver_table, repeat.file, repeat.SUB_ID
FROM contribution
JOIN repeat ON repeat.SUB_ID = contribution.source_record_id
UNION ALL
SELECT 'committee_transfer', repeat.file, repeat.SUB_ID
FROM committee_transfer
JOIN repeat ON repeat.SUB_ID = committee_transfer.source_record_id
UNION ALL
SELECT 'organization_receipt', repeat.file, repeat.SUB_ID
FROM organization_receipt
JOIN repeat ON repeat.SUB_ID = organization_receipt.source_record_id
UNION ALL
SELECT 'jfc_attribution', repeat.file, repeat.SUB_ID
FROM jfc_attribution
JOIN repeat ON repeat.SUB_ID = jfc_attribution.source_record_id
UNION ALL
SELECT 'independent_expenditure', repeat.file, repeat.SUB_ID
FROM independent_expenditure
JOIN repeat ON repeat.SUB_ID = independent_expenditure.source_record_id
UNION ALL
SELECT 'operating_expenditure', repeat.file, repeat.SUB_ID
FROM operating_expenditure
JOIN repeat ON repeat.SUB_ID = operating_expenditure.source_record_id;
