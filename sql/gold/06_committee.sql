-- committee (spec §7.1): every committee of the cycle.
CREATE TABLE committee AS
SELECT
    committee_id,
    name,
    type,
    designation,
    party,
    connected_org,
    is_conduit,
    pg_array([CAST({cycle} AS INTEGER)]) AS cycles
FROM silver.committee;
