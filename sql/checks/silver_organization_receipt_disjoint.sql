-- No organization receipt is also a contribution or a committee transfer: a source record is
-- counted once, in one table (ADR-0011, NEU-2131).
SELECT source_record_id, 'contribution' AS also_in
FROM organization_receipt
WHERE source_record_id IN (SELECT source_record_id FROM contribution)
UNION ALL
SELECT source_record_id, 'committee_transfer' AS also_in
FROM organization_receipt
WHERE source_record_id IN (SELECT source_record_id FROM committee_transfer);
