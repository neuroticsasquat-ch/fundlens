-- Every giving committee in a race's top 100 is a committee of the cycle, so it has a name and a page.
SELECT race_id, rank, committee_id
FROM race_top_committee
WHERE NOT EXISTS (SELECT 1 FROM committee WHERE committee.committee_id = race_top_committee.committee_id);
