-- Every race_candidate stands in a race of the seat calendar.
SELECT race_id, candidate_id
FROM race_candidate
WHERE NOT EXISTS (SELECT 1 FROM race WHERE race.race_id = race_candidate.race_id);
