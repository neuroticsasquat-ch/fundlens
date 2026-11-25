-- Every lobbyist/registrant PAC is a committee of the cycle (every-FEC-dollar spec §7.3,
-- NEU-2175): the model keeps only the cycle's committees of the file, which runs from 2009 and
-- names committees no cycle holds.
SELECT committee_id, filed_date, image_num
FROM lobbyist_pac
WHERE NOT EXISTS (
    SELECT 1
    FROM committee
    WHERE committee.committee_id = lobbyist_pac.committee_id
);
