-- Every giving committee in a race's top 100 is a committee of the cycle, so it has a page (and a
-- name, unless `cm` lists it only as a skeleton row: 06_committee.sql).
SELECT race_id, rank, committee_id
FROM race_top_committee
WHERE NOT EXISTS (SELECT 1 FROM committee WHERE committee.committee_id = race_top_committee.committee_id);
