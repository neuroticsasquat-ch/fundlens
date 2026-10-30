-- candidate (spec §7.1): every candidate of the cycle, a race or not. cycles is the one cycle
-- until NEU-2059 merges builds; pg_array writes it as Postgres reads an int[].
CREATE TABLE candidate AS
SELECT
    candidate_id,
    name,
    party,
    office,
    state,
    district,
    pg_array([CAST({cycle} AS INTEGER)]) AS cycles
FROM silver.candidate;
