-- A leadership PAC's sponsor id says where it came from (every-FEC-dollar spec §7.3, §7.4,
-- NEU-2175): sponsor_source is `rule` or `list`, set exactly when sponsor_candidate_id is. An id
-- the name rule gave is a candidate of the cycle and no alias, since the rule resolves each match
-- through alias_of; one the list gave may be a candidate of another cycle, which this cycle's
-- transform cannot see.
SELECT committee_id, sponsor_name, sponsor_candidate_id, sponsor_source
FROM leadership_pac
WHERE (sponsor_candidate_id IS NULL) <> (sponsor_source IS NULL)
    OR sponsor_source NOT IN ('rule', 'list')
    OR (
        sponsor_source = 'rule'
        AND NOT EXISTS (
            SELECT 1
            FROM candidate
            WHERE candidate.candidate_id = leadership_pac.sponsor_candidate_id
                AND candidate.alias_of IS NULL
        )
    );
