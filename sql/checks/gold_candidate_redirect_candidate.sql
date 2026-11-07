-- Every candidate redirect leads from an id gold does not list to one it does, in one hop.
SELECT old_candidate_id, candidate_id
FROM candidate_redirect
WHERE NOT EXISTS (SELECT 1 FROM candidate WHERE candidate.candidate_id = candidate_redirect.candidate_id)
    OR EXISTS (SELECT 1 FROM candidate WHERE candidate.candidate_id = candidate_redirect.old_candidate_id);
