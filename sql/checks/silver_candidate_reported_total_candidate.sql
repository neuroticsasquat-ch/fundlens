-- Every candidate reported total is a candidate of the cycle's (every-FEC-dollar spec §4.2):
-- FEC's figures for a candidate `cn` lacks belong to no candidate fundlens shows.
SELECT cycle, candidate_id
FROM candidate_reported_total
WHERE NOT EXISTS (
    SELECT 1 FROM candidate WHERE candidate.candidate_id = candidate_reported_total.candidate_id
);
