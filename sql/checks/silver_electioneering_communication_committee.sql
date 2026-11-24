-- Every electioneering communication's spender is a committee of the cycle (NEU-2166): a row whose
-- spender `cm` lacks is dropped (every-FEC-dollar spec §6.1), so one here would be spending no
-- committee page can hold.
SELECT source_record_id, committee_id, amount
FROM electioneering_communication
WHERE NOT EXISTS (
    SELECT 1
    FROM committee
    WHERE committee.committee_id = electioneering_communication.committee_id
);
