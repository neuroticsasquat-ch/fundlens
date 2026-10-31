-- Every candidate standing this cycle has a race, or is a filing `fundlens seats --report`
-- recorded in app.unmatched_filing as matching no seat (spec §5.2).
SELECT candidate_id, office, state, district
FROM candidate
WHERE race_id IS NULL
    AND election_year IN ({cycle} - 1, {cycle})
    AND NOT EXISTS (
        SELECT 1 FROM unmatched_filing WHERE unmatched_filing.candidate_id = candidate.candidate_id
    );
