-- candidate_cycle (spec §7.1, NEU-2039 §3): one row per silver candidate of the cycle, with or
-- without a race (the fixture's H4MD09109 has money but no seat).
--
-- total_individual is every counted contribution to a committee raising for the candidate that is
-- not the candidate's own money; self_funding is that own money (silver's is_self_funding), and
-- neither includes the other. total_committee is the committees' gifts to the candidate: the
-- disbursement side of committee_transfer only (the recipient's 18K twin would count each gift
-- twice). Refunds are negative amounts and net out. Nothing to sum is 0, never NULL.
-- ie_support and ie_oppose are 0 until NEU-2057; contributor_count is NULL until M3 (NEU-2051).
CREATE TABLE candidate_cycle AS
WITH money AS (
    SELECT
        candidate_id,
        coalesce(sum(amount) FILTER (WHERE NOT is_self_funding), 0) AS total_individual,
        coalesce(sum(amount) FILTER (WHERE is_self_funding), 0) AS self_funding
    FROM silver.contribution
    WHERE candidate_id IS NOT NULL
    GROUP BY candidate_id
),
from_committees AS (
    SELECT candidate_id, sum(amount) AS total_committee
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND candidate_id IS NOT NULL
    GROUP BY candidate_id
)
SELECT
    candidate.candidate_id,
    CAST({cycle} AS INTEGER) AS cycle,
    candidate.race_id,
    CAST(coalesce(money.total_individual, 0) AS DECIMAL(16, 2)) AS total_individual,
    CAST(coalesce(from_committees.total_committee, 0) AS DECIMAL(16, 2)) AS total_committee,
    CAST(coalesce(money.self_funding, 0) AS DECIMAL(16, 2)) AS self_funding,
    CAST(0 AS DECIMAL(16, 2)) AS ie_support,
    CAST(0 AS DECIMAL(16, 2)) AS ie_oppose,
    CAST(NULL AS INTEGER) AS contributor_count
FROM silver.candidate AS candidate
LEFT JOIN money USING (candidate_id)
LEFT JOIN from_committees USING (candidate_id);
