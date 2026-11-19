-- Every reported total is a committee of the cycle's (every-FEC-dollar spec §4.1): FEC's figures
-- for a committee `cm` lacks belong to no committee fundlens shows.
SELECT cycle, committee_id, source_file
FROM reported_total
WHERE NOT EXISTS (
    SELECT 1 FROM committee WHERE committee.committee_id = reported_total.committee_id
);
