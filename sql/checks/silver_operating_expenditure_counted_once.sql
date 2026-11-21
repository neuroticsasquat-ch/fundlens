-- No sub-item is counted (every-FEC-dollar spec §5.2, NEU-2152): a sub-itemized payment counts
-- once, at its parent, so a counted row with parent_source_record_id set counts a card bill's
-- charges beside the bill. Nor does a row name a parent that is not a row of the table, or itself.
SELECT source_record_id, parent_source_record_id, 'counted' AS fault
FROM operating_expenditure
WHERE parent_source_record_id IS NOT NULL AND counted
UNION ALL
SELECT source_record_id, parent_source_record_id, 'no such parent'
FROM operating_expenditure
WHERE parent_source_record_id IS NOT NULL
    AND (
        parent_source_record_id = source_record_id
        OR parent_source_record_id NOT IN (SELECT source_record_id FROM operating_expenditure)
    );
