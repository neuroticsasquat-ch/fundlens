-- Every leadership PAC is a committee of the cycle (every-FEC-dollar spec §7.3, NEU-2175): every
-- committee of every cycle's leadership file is in `cm` (Q2, Q12c), so one that is not is a file
-- FEC changed, and a PAC no committee page could show.
SELECT committee_id, sponsor_name
FROM leadership_pac
WHERE NOT EXISTS (
    SELECT 1
    FROM committee
    WHERE committee.committee_id = leadership_pac.committee_id
);
