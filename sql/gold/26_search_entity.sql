-- search_entity (spec §7.1): what `GET /v1/search` matches by trigram. One row per candidate,
-- committee, race, donor and payee, across every cycle (NEU-2059): a candidate or committee by its
-- newest name, weighed by its money in every cycle; not per candidate alias (NEU-2127), which
-- candidate_cycle leaves out. weight orders ties in the search results; aliases is a second string
-- to match on (the race's slug, the candidate's principal committee, the committee's connected
-- organisation, the donor's other spellings of their name, most money first). A donor's weight is
-- their total; one known only from JFC attributions weighs 0 and is still found. A payee
-- (every-FEC-dollar spec §5.5) is one with a page (payee, 22_payee.sql), by its display_name, its
-- aliases the key's other reported spellings, most payee dollars first, weighed by its payee
-- dollars over every cycle; a person's key and a name that names nobody have no page, so no row.
-- A committee `cm` names in no cycle, only ever a skeleton row (its id and a filing frequency of
-- `T`, every other column blank: 06_committee.sql, NEU-2296), and a candidate `cn` names in no
-- cycle (05_candidate.sql, NEU-2323), have no name to match on, so they are left out, as a donor
-- with no display_name is; their pages are still there under their ids. A candidate's principal
-- committee's name is not the candidate's, so it does not stand in for one.
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
WHERE candidate.name IS NOT NULL
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
WHERE committee.name IS NOT NULL
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
WHERE donor.display_name IS NOT NULL
UNION ALL
SELECT
    'payee' AS kind,
    payee.payee_id AS id,
    payee.display_name AS name,
    spellings.aliases,
    payee.total_all_cycles AS weight
FROM payee
LEFT JOIN (
    SELECT
        payee_key,
        string_agg(payee_name, '; ' ORDER BY amount DESC, rows DESC, payee_name) AS aliases
    FROM (
        SELECT payee_key, payee_name, sum(amount) AS amount, count(*) AS rows
        FROM payee_row
        GROUP BY payee_key, payee_name
    )
    JOIN payee USING (payee_key)
    WHERE payee_name <> payee.display_name
    GROUP BY payee_key
) AS spellings USING (payee_key);
