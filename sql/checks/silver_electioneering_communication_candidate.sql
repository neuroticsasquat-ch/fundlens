-- Every electioneering communication is attached as independent_expenditure's rows are
-- (every-FEC-dollar spec §6.1, NEU-2166): to a candidate of the cycle that is no alias (NEU-2127),
-- and no handoff's first candidate on or after the handoff or undated (NEU-2277), and to that
-- candidate's race; or, naming no candidate of the cycle, to neither. 24 rows of 2024 name none
-- (ads about an issue) and one an id `cn` lacks, so an unattached row is kept, in its spender's total alone;
-- what this fails on is a row attached to the wrong candidate or race.
SELECT spending.source_record_id, spending.candidate_id, spending.race_id, spending.date
FROM electioneering_communication AS spending
LEFT JOIN candidate USING (candidate_id)
WHERE (
        spending.candidate_id IS NOT NULL
        AND (candidate.candidate_id IS NULL OR candidate.alias_of IS NOT NULL)
    )
    OR spending.race_id IS DISTINCT FROM candidate.race_id
    OR EXISTS (
        SELECT 1
        FROM handoff
        WHERE handoff.from_candidate_id = spending.candidate_id
            AND (spending.date IS NULL OR spending.date >= handoff.handoff_date)
    );
