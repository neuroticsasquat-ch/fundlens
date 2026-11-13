-- Every candidate standing this cycle has a race, or is a filing `fundlens seats --report`
-- recorded in app.unmatched_filing as matching no seat (spec §5.2). Standing this cycle is
-- 02_candidate.sql's rule: a filing for this cycle's year or the odd year before it, or a House
-- incumbent's filing for the next election when that election keeps this cycle's map (NEU-2283).
SELECT candidate_id, office, state, district
FROM candidate
WHERE race_id IS NULL
    AND (
        election_year IN ({cycle} - 1, {cycle})
        OR (
            office = 'H'
            AND election_year = {cycle} + 2
            AND incumbent_challenger_open = 'I'
            AND {cycle} % 10 <> 0
        )
    )
    AND NOT EXISTS (
        SELECT 1 FROM unmatched_filing WHERE unmatched_filing.candidate_id = candidate.candidate_id
    );
