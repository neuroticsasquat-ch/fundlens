-- No operating expenditure is also a contribution, an organization receipt, a committee transfer
-- or an independent expenditure (every-FEC-dollar spec §5, NEU-2152): spending is never money
-- given to a committee, and a dollar spent on a candidate's behalf counts once, as one or the
-- other. The measurement found no `oppexp` SUB_ID in `indiv`, `oth` or `pas2` (Q7).
SELECT source_record_id, 'contribution' AS also_in
FROM operating_expenditure
WHERE source_record_id IN (SELECT source_record_id FROM contribution)
UNION ALL
SELECT source_record_id, 'organization_receipt'
FROM operating_expenditure
WHERE source_record_id IN (SELECT source_record_id FROM organization_receipt)
UNION ALL
SELECT source_record_id, 'committee_transfer'
FROM operating_expenditure
WHERE source_record_id IN (SELECT source_record_id FROM committee_transfer)
UNION ALL
SELECT source_record_id, 'independent_expenditure'
FROM operating_expenditure
WHERE source_record_id IN (
    -- Text, a `pas2` row's SUB_ID's digits (NEU-2165); a 24/48-hour row has no SUB_ID.
    SELECT CAST(source_record_id AS UBIGINT)
    FROM independent_expenditure
    WHERE source_file = 'pas2'
);
