-- committee_cycle (spec §7.1, NEU-2039 §3): one row per committee of the cycle.
--
-- total_individual and self_funding are the counted contributions it received, the candidate's own
-- money kept apart (a candidate committee's receipts would otherwise hide or include it).
-- total_from_committees is the receipt side of committee_transfer (what it recorded receiving);
-- total_to_candidates the disbursement side credited to a candidate (what it recorded giving; a 24K
-- whose recipient raises for no candidate of the cycle is to none, NEU-2075): one side each, never
-- both, so a gift on both sides is counted once in each figure, and a committee's top recipients
-- add up to its total_to_candidates. ie_total is 0 until NEU-2057.
CREATE TABLE committee_cycle AS
WITH received AS (
    SELECT
        recipient_committee_id AS committee_id,
        coalesce(sum(amount) FILTER (WHERE NOT is_self_funding), 0) AS total_individual,
        coalesce(sum(amount) FILTER (WHERE is_self_funding), 0) AS self_funding
    FROM silver.contribution
    GROUP BY recipient_committee_id
),
from_committees AS (
    SELECT to_committee_id AS committee_id, sum(amount) AS total_from_committees
    FROM silver.committee_transfer
    WHERE side = 'receipt'
    GROUP BY to_committee_id
),
to_candidates AS (
    SELECT from_committee_id AS committee_id, sum(amount) AS total_to_candidates
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND candidate_id IS NOT NULL
    GROUP BY from_committee_id
)
SELECT
    committee.committee_id,
    CAST({cycle} AS INTEGER) AS cycle,
    CAST(coalesce(received.total_individual, 0) AS DECIMAL(16, 2)) AS total_individual,
    CAST(coalesce(received.self_funding, 0) AS DECIMAL(16, 2)) AS self_funding,
    CAST(coalesce(from_committees.total_from_committees, 0) AS DECIMAL(16, 2)) AS total_from_committees,
    CAST(coalesce(to_candidates.total_to_candidates, 0) AS DECIMAL(16, 2)) AS total_to_candidates,
    CAST(0 AS DECIMAL(16, 2)) AS ie_total
FROM silver.committee AS committee
LEFT JOIN received USING (committee_id)
LEFT JOIN from_committees USING (committee_id)
LEFT JOIN to_candidates USING (committee_id);
