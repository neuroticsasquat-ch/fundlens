-- Every bundling report's recipient is a committee of its cycle (every-FEC-dollar spec §7.5,
-- NEU-2175): a report to a committee `cm` lacks is dropped, as an outside-spending spender `cm`
-- lacks is.
SELECT source_record_id, committee_id, amount
FROM bundling_report
WHERE NOT EXISTS (
    SELECT 1
    FROM committee
    WHERE committee.committee_id = bundling_report.committee_id
);
