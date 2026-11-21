-- Every operating expenditure's committee is a committee of the cycle (NEU-2152): a row whose
-- filer `cm` lacks is dropped (every-FEC-dollar spec §5.1), so one here would be spending no
-- committee page can hold.
SELECT source_record_id, committee_id, amount
FROM operating_expenditure
WHERE NOT EXISTS (
    SELECT 1 FROM committee WHERE committee.committee_id = operating_expenditure.committee_id
);
