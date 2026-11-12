-- committee (spec §7.1): every committee of any cycle. One row per committee across cycles
-- (NEU-2059): its name and other columns as its newest cycle's `cm` lists them, and cycles every
-- cycle it is in, in order.
CREATE TABLE committee AS
WITH filed AS (
    SELECT
        committee_id,
        pg_array(list(CAST(cycle AS INTEGER) ORDER BY cycle)) AS cycles
    FROM silver.committee
    GROUP BY committee_id
)
SELECT
    newest.committee_id,
    newest.name,
    newest.type,
    newest.designation,
    newest.party,
    newest.connected_org,
    newest.is_conduit,
    filed.cycles
FROM silver.committee AS newest
JOIN filed USING (committee_id)
QUALIFY row_number() OVER (PARTITION BY newest.committee_id ORDER BY newest.cycle DESC) = 1;
