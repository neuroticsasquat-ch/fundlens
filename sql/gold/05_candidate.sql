-- candidate (spec §7.1): every candidate of any cycle, a race or not, but an alias (NEU-2127,
-- candidate_redirect). One row per candidate across cycles (NEU-2059): its name, party, office,
-- state and district as the newest cycle's `cn` that names it lists them, and cycles every cycle
-- it stands in, in order. A cycle it is an alias in is not one of them. pg_array writes the list
-- as Postgres reads an int[].
--
-- `cn` now and then lists a candidate as a skeleton row: its id, year, state, office, status and
-- principal committee, every other column blank (NEU-2323: 2026's H6AZ08210, the one blank name
-- among cn26's 8,931 rows). As 06_committee.sql does for `cm`'s skeletons (NEU-2296), a row with
-- a name wins over a newer one without (a NULL name is the test); a skeleton still counts in
-- cycles. A candidate that is a skeleton in every cycle it stands in keeps a NULL name, and
-- 16_search_entity.sql leaves it out.
CREATE TABLE candidate AS
WITH stood AS (
    SELECT
        candidate_id,
        pg_array(list(CAST(cycle AS INTEGER) ORDER BY cycle)) AS cycles
    FROM silver.candidate
    WHERE alias_of IS NULL
    GROUP BY candidate_id
)
SELECT
    newest.candidate_id,
    newest.name,
    newest.party,
    newest.office,
    newest.state,
    newest.district,
    stood.cycles
FROM silver.candidate AS newest
JOIN stood USING (candidate_id)
WHERE newest.alias_of IS NULL
QUALIFY row_number() OVER (PARTITION BY newest.candidate_id ORDER BY newest.name IS NULL, newest.cycle DESC) = 1;
