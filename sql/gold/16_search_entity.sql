-- search_entity (spec §7.1): what `GET /v1/search` matches by trigram. One row per candidate,
-- committee, race and donor. weight orders ties in the search results; aliases is a second string
-- to match on (the race's slug, the candidate's principal committee, the committee's connected
-- organisation, the donor's other spellings of their name, most money first). A donor's weight is
-- their total; one known only from JFC attributions weighs 0 and is still found.
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
FROM race
UNION ALL
SELECT
    'donor' AS kind,
    CAST(donor.donor_id AS VARCHAR) AS id,
    donor.display_name AS name,
    spellings.aliases,
    donor.total_all_cycles AS weight
FROM donor
LEFT JOIN (
    SELECT donor_id, string_agg(value, '; ' ORDER BY amount DESC, contributions DESC, value) AS aliases
    FROM donor_variant
    JOIN donor USING (donor_id)
    WHERE field = 'name' AND value <> donor.display_name
    GROUP BY donor_id
) AS spellings USING (donor_id)
WHERE donor.display_name IS NOT NULL;
