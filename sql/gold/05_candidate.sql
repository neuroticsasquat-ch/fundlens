-- candidate (spec §7.1): every candidate of any cycle, a race or not, but an alias (NEU-2127,
-- candidate_redirect). One row per candidate across cycles (NEU-2059): its name, party, office,
-- state and district as its newest cycle's `cn` lists them, and cycles every cycle it stands in,
-- in order. A cycle it is an alias in is not one of them. pg_array writes the list as Postgres
-- reads an int[].
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
QUALIFY row_number() OVER (PARTITION BY newest.candidate_id ORDER BY newest.cycle DESC) = 1;
