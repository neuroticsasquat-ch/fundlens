-- search_entity (spec §7.1): what `GET /v1/search` matches by trigram. One row per candidate,
-- committee and race; donor rows arrive in M3. weight orders ties in the search results; aliases
-- is a second string to match on (the race's slug, the candidate's principal committee, the
-- committee's connected organisation).
CREATE TABLE search_entity AS
SELECT
    'candidate' AS kind,
    candidate_cycle.candidate_id AS id,
    candidate.name,
    principal.name AS aliases,
    CAST(candidate_cycle.total_individual + candidate_cycle.total_committee AS DECIMAL(16, 2)) AS weight
FROM candidate_cycle
JOIN silver.candidate AS candidate USING (candidate_id)
LEFT JOIN silver.committee AS principal ON principal.committee_id = candidate.principal_committee_id
UNION ALL
SELECT
    'committee' AS kind,
    committee_cycle.committee_id AS id,
    committee.name,
    committee.connected_org AS aliases,
    CAST(committee_cycle.total_individual + committee_cycle.total_from_committees AS DECIMAL(16, 2)) AS weight
FROM committee_cycle
JOIN silver.committee AS committee USING (committee_id)
UNION ALL
SELECT
    'race' AS kind,
    race_id AS id,
    -- A readable label: '2024 President', '2024 Senate MD', '2024 House MD-05', '… special'.
    CAST(cycle AS VARCHAR)
        || CASE office
            WHEN 'P' THEN ' President'
            WHEN 'S' THEN ' Senate ' || state
            ELSE ' House ' || state || '-' || district
        END
        || CASE WHEN is_special THEN ' special' ELSE '' END AS name,
    slug AS aliases,
    total_individual AS weight
FROM race;
