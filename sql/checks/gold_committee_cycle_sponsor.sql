-- A committee with a sponsor is a leadership PAC that cycle, and every sponsor_candidate_id is a
-- candidate fundlens holds in some cycle, a page or an alias redirecting to one (every-FEC-dollar
-- spec §7.7). Silver cannot check a list id against another cycle's candidates (§7.3); gold sees
-- every cycle.
SELECT 'not a leadership PAC' AS failure, committee_id, cycle, sponsor_candidate_id, sponsor_name
FROM committee_cycle
WHERE (sponsor_candidate_id IS NOT NULL OR sponsor_name IS NOT NULL) AND NOT is_leadership_pac
UNION ALL
SELECT 'no such candidate', committee_id, cycle, sponsor_candidate_id, sponsor_name
FROM committee_cycle
WHERE sponsor_candidate_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM candidate WHERE candidate.candidate_id = committee_cycle.sponsor_candidate_id
    )
    AND NOT EXISTS (
        SELECT 1
        FROM candidate_redirect
        WHERE candidate_redirect.old_candidate_id = committee_cycle.sponsor_candidate_id
    );
