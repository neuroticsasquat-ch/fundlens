-- The money of every candidate with a race is the money of every race.
SELECT candidates.total_individual, races.total_individual
FROM (SELECT coalesce(sum(total_individual), 0) AS total_individual FROM candidate_cycle WHERE race_id IS NOT NULL) AS candidates,
    (SELECT coalesce(sum(total_individual), 0) AS total_individual FROM race) AS races
WHERE candidates.total_individual <> races.total_individual;
