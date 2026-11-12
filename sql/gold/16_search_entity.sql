-- search_entity (spec §7.1): what `GET /v1/search` matches by trigram. One row per candidate,
-- committee, race and donor, across every cycle (NEU-2059): a candidate or committee by its newest
-- name, weighed by its money in every cycle; not per candidate alias (NEU-2127), which
-- candidate_cycle leaves out. weight orders ties in the search results; aliases is a second string
-- to match on (the race's slug, the candidate's principal committee, the committee's connected
-- organisation, the donor's other spellings of their name, most money first). A donor's weight is
-- their total; one known only from JFC attributions weighs 0 and is still found.
CREATE TABLE search_entity AS
SELECT
    'candidate' AS kind,
    candidate.candidate_id AS id,
    candidate.name,
    principal.name AS aliases,
    money.weight
FROM candidate
JOIN (
    SELECT
        candidate_id,
        CAST(sum(total_individual + total_committee) AS DECIMAL(16, 2)) AS weight
    FROM candidate_cycle
    GROUP BY candidate_id
) AS money USING (candidate_id)
LEFT JOIN (
    SELECT candidate_id, principal_committee_id
    FROM silver.candidate
    WHERE alias_of IS NULL
    QUALIFY row_number() OVER (PARTITION BY candidate_id ORDER BY cycle DESC) = 1
) AS newest USING (candidate_id)
LEFT JOIN committee AS principal ON principal.committee_id = newest.principal_committee_id
UNION ALL
SELECT
    'committee' AS kind,
    committee.committee_id AS id,
    committee.name,
    committee.connected_org AS aliases,
    money.weight
FROM committee
JOIN (
    SELECT
        committee_id,
        CAST(sum(total_individual + total_from_committees) AS DECIMAL(16, 2)) AS weight
    FROM committee_cycle
    GROUP BY committee_id
) AS money USING (committee_id)
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
