-- committee (spec §7.1): every committee of any cycle. One row per committee across cycles
-- (NEU-2059): its name and other columns as the newest cycle's `cm` that names it lists them, and
-- cycles every cycle it is in, in order.
--
-- `cm` now and then lists a committee as a skeleton row: its id and a filing frequency of `T`
-- (terminated), every other column blank (NEU-2296: 1 in 2016's, 9 in 2018's, 2 in 2020's).
-- Taken as the newest row, it would blank the name, type and designation an earlier cycle gave
-- the committee, so a row with a name wins over a newer one without (a NULL name is the test); a skeleton still counts in
-- cycles. A committee that is a skeleton in every cycle it is in keeps a NULL name, and
-- 26_search_entity.sql leaves it out.
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
QUALIFY row_number() OVER (PARTITION BY newest.committee_id ORDER BY newest.name IS NULL, newest.cycle DESC) = 1;
