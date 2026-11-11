-- No counted row is on a superseded filing (NEU-2196): no contribution, organization receipt or
-- committee transfer is read from an `indiv` row of a filing a later amendment supersedes
-- (`superseded_filing`, 04_contribution.sql). Each table's `oth` rows are not judged: the rule
-- reads `indiv` alone. The superseded rows are the few `indiv` rows of the few such filings.
WITH superseded AS (
    SELECT SUB_ID, FILE_NUM
    FROM indiv
    WHERE FILE_NUM IN (SELECT FILE_NUM FROM superseded_filing)
)
SELECT 'contribution' AS silver_table, superseded.SUB_ID, superseded.FILE_NUM
FROM contribution
JOIN superseded ON superseded.SUB_ID = contribution.source_record_id
UNION ALL
SELECT 'organization_receipt', superseded.SUB_ID, superseded.FILE_NUM
FROM organization_receipt
JOIN superseded ON superseded.SUB_ID = organization_receipt.source_record_id
UNION ALL
SELECT 'committee_transfer', superseded.SUB_ID, superseded.FILE_NUM
FROM committee_transfer
JOIN superseded ON superseded.SUB_ID = committee_transfer.source_record_id;
